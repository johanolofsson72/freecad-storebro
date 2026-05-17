# Data Model: PartDesign Hull Upgrade (Phase 1)

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md) | **Date**: 2026-05-17

The hull module's *external* data model — `HullParameters`, `Hull`, `HullConstructionError` — is unchanged from spec 001 (per FR-005). This document describes the *internal* PartDesign feature graph entities the new implementation constructs.

---

## 1. The feature graph

```
PartDesign::Body  "HullBody"  (Tip → MirrorFeature)
├── Origin                              (auto-created by FreeCAD)
│   ├── XY_Plane / XZ_Plane / YZ_Plane  (reference planes)
│   └── X_Axis / Y_Axis / Z_Axis        (reference axes)
│
├── PartDesign::Plane  "HullDatumTransom"     attached to Origin.YZ_Plane @ X = 0.0
├── PartDesign::Plane  "HullDatumAft"         attached to Origin.YZ_Plane @ X = 0.25 · LOA
├── PartDesign::Plane  "HullDatumAmidships"   attached to Origin.YZ_Plane @ X = 0.50 · LOA
├── PartDesign::Plane  "HullDatumFwd"         attached to Origin.YZ_Plane @ X = 0.75 · LOA
├── PartDesign::Plane  "HullDatumStem"        attached to Origin.YZ_Plane @ X = LOA
│
├── Sketcher::SketchObject  "HullStation1"  on HullDatumTransom   (half-section polygon)
├── Sketcher::SketchObject  "HullStation2"  on HullDatumAft       (half-section polygon)
├── Sketcher::SketchObject  "HullStation3"  on HullDatumAmidships (half-section polygon)
├── Sketcher::SketchObject  "HullStation4"  on HullDatumFwd       (half-section polygon)
├── Sketcher::SketchObject  "HullStation5"  on HullDatumStem      (degenerate single-point/vertex)
│
├── PartDesign::AdditiveLoft  "HullLoft"   profiles = [HullStation1..5 in order], Solid = True
│                                          → produces port half-hull
│
└── PartDesign::Mirrored  "HullMirror"  base = HullLoft, plane = Origin.XZ_Plane
                                        → produces closed full-hull (Body.Tip)
```

12 PartDesign-derived feature objects in total (plus the auto-created Origin). All live as children of the `HullBody`. No legacy Part-workbench types anywhere in the graph.

---

## 2. Entity types and their FreeCAD type IDs

| Entity | FreeCAD TypeId | Count per Body | Naming pattern |
|---|---|---|---|
| Body container | `PartDesign::Body` | 1 | `HullBody` (auto-numbered for collisions) |
| Datum plane | `PartDesign::Plane` | 5 | `HullDatum<StationName>` (Transom, Aft, Amidships, Fwd, Stem) |
| Station sketch | `Sketcher::SketchObject` | 5 | `HullStation<N>` (1..5) |
| Additive loft | `PartDesign::AdditiveLoft` | 1 | `HullLoft` |
| Mirror | `PartDesign::Mirrored` | 1 | `HullMirror` |

The `HullBody.Tip` reference always points at `HullMirror`.

---

## 3. Body's named informational properties (FR-006, Q2 clarify)

These eight properties are added to the Body via `body.addProperty(...)`. They reflect the parameters used to build the hull but do NOT drive sketch dimensions (informational only for v1.0.0; `deferred HullBody.expression_engine_bindings` for v1.1+).

| Property name | FreeCAD type | Group | Source field |
|---|---|---|---|
| `LOA` | `App::PropertyLength` | `Hull` | `HullParameters.loa` |
| `BeamMax` | `App::PropertyLength` | `Hull` | `HullParameters.beam_max` |
| `Draft` | `App::PropertyLength` | `Hull` | `HullParameters.draft` |
| `Freeboard` | `App::PropertyLength` | `Hull` | `HullParameters.freeboard` |
| `SheerHeightAft` | `App::PropertyLength` | `Hull` | `HullParameters.sheer_height_aft` |
| `SheerHeightFwd` | `App::PropertyLength` | `Hull` | `HullParameters.sheer_height_fwd` |
| `DeadriseAmidships` | `App::PropertyAngle` | `Hull` | `HullParameters.deadrise_amidships` |
| `TransomAngle` | `App::PropertyAngle` | `Hull` | `HullParameters.transom_angle` |

Names, types, and group identical to v0.1.0-alpha. The `_bind_parameters_to_body_properties` helper from `hull.py:434-460` continues to do this work unchanged.

---

## 4. Datum-plane attachment configuration

Each `PartDesign::Plane` is configured as:

```python
datum.AttachmentSupport = (body.Origin.YZ_Plane, "")
datum.MapMode = "FlatFace"        # attaches the plane parallel to the support
datum.AttachmentOffset = FreeCAD.Placement(
    FreeCAD.Vector(profile.x_position, 0.0, 0.0),
    FreeCAD.Rotation(),           # no rotation; plane stays parallel to YZ
)
```

- `AttachmentSupport` references the Body's local YZ origin plane (Q1 clarify: Body-local frame).
- `MapMode = "FlatFace"` means the new plane is parallel to the supporting face.
- `AttachmentOffset` translates the plane to the station's X coordinate. No rotation — the plane stays parallel to YZ.

---

## 5. Station sketch construction (per non-terminal station)

```python
sketch = body.newObject("Sketcher::SketchObject", f"HullStation{n}")
sketch.AttachmentSupport = (datum, "")
sketch.MapMode = "FlatFace"

# Half-section closed polygon (port side; x' axis in the sketch frame = Y in
# the Body, y' axis in the sketch frame = Z in the Body).
sketch.addGeometry(Part.LineSegment(
    FreeCAD.Vector(0.0, -keel_depth, 0.0),                 # keel @ centerline
    FreeCAD.Vector(half_beam_at_bottom, -keel_depth * 0.6, 0.0),  # bottom outer
), False)
sketch.addGeometry(Part.LineSegment(
    FreeCAD.Vector(half_beam_at_bottom, -keel_depth * 0.6, 0.0),
    FreeCAD.Vector(half_beam_at_top, 0.0, 0.0),            # top outer
), False)
sketch.addGeometry(Part.LineSegment(
    FreeCAD.Vector(half_beam_at_top, 0.0, 0.0),
    FreeCAD.Vector(half_beam_at_top, freeboard, 0.0),      # outer sheer
), False)
sketch.addGeometry(Part.LineSegment(
    FreeCAD.Vector(half_beam_at_top, freeboard, 0.0),
    FreeCAD.Vector(0.0, freeboard, 0.0),                   # deck @ centerline
), False)
sketch.addGeometry(Part.LineSegment(
    FreeCAD.Vector(0.0, freeboard, 0.0),
    FreeCAD.Vector(0.0, -keel_depth, 0.0),                 # centerline back to keel
), False)
```

Five line segments forming a closed pentagon. The closed wire is what `PartDesign::AdditiveLoft` consumes as a profile section.

Coordinate convention: the sketch's local x-axis maps to the Body's Y-axis (transverse), the sketch's local y-axis maps to the Body's Z-axis (vertical). The X coordinate of the section is already handled by the datum plane's attachment offset.

---

## 6. Stem (terminal) station sketch construction

```python
sketch = body.newObject("Sketcher::SketchObject", "HullStation5")
sketch.AttachmentSupport = (datum, "")
sketch.MapMode = "FlatFace"

# Single zero-length line at the centerline — PartDesign::AdditiveLoft
# interprets this as a degenerate "point" profile, producing a pointed bow.
sketch.addGeometry(Part.LineSegment(
    FreeCAD.Vector(0.0, 0.0, 0.0),
    FreeCAD.Vector(0.0, 0.0, 0.0),
), False)
```

Per R6 in research.md, a degenerate profile is what FreeCAD's AdditiveLoft expects for a pointed end.

---

## 7. AdditiveLoft configuration

```python
loft = body.newObject("PartDesign::AdditiveLoft", "HullLoft")
loft.Profile = (sketches[0], [""])       # transom
loft.Sections = [(sketches[i], [""]) for i in range(1, 5)]  # aft, amidships, fwd, stem
loft.Ruled = False                       # smooth interpolation, not piecewise-linear
loft.Closed = False                      # not a closed loft (no end-to-end loop)
loft.Solid = True                        # produce a solid, not a surface
```

The first profile is the loft's `Profile` (the additive base); the remaining four are `Sections`. The order is transom → aft → amidships → fwd → stem, matching the geometric order along X.

`Ruled = False` produces smooth B-spline interpolation between profiles — the classic hull surface.

---

## 8. Mirror configuration

```python
mirror = body.newObject("PartDesign::Mirrored", "HullMirror")
mirror.Originals = [loft]
mirror.MirrorPlane = (body.Origin.XZ_Plane, [""])

body.Tip = mirror
```

`MirrorPlane = Body.Origin.XZ_Plane` reflects the half-hull (which lives in +Y space) into the -Y space, producing a closed full-hull. Setting `Body.Tip = mirror` exposes the full hull as `body.Shape`.

---

## 9. State transitions (build_hull execution flow)

```
START
  │
  ├── _validate_hull_parameters(parameters)         (unchanged from v0.1.0-alpha)
  │       └── raises HullParameterError on invalid
  │
  ├── _resolve_document(document_arg)               (unchanged)
  ├── _resolve_body_label(name_arg)                 (unchanged)
  ├── ensure_supported_freecad()                    (unchanged; raises HullConstructionError on bad version)
  │
  ├── added: list[Any] = []                         (rollback tracker)
  │
  ├── try:
  │     body = target_doc.addObject("PartDesign::Body", "HullBody")     ; added.append(body)
  │     body.Label = body_label
  │     _bind_parameters_to_body_properties(body, parameters)
  │     stations = _compute_stations(parameters)
  │     datums = []
  │     for profile in stations:
  │         datum = body.newObject("PartDesign::Plane", f"HullDatum{profile.name}")  ; added.append(datum)
  │         _configure_datum_plane(datum, profile, body)
  │         datums.append(datum)
  │     sketches = []
  │     for profile, datum in zip(stations, datums):
  │         sketch = body.newObject("Sketcher::SketchObject", f"HullStation{...}") ; added.append(sketch)
  │         _populate_station_sketch(sketch, datum, profile)
  │         sketches.append(sketch)
  │     loft = body.newObject("PartDesign::AdditiveLoft", "HullLoft")    ; added.append(loft)
  │     loft.Profile = (sketches[0], [""])
  │     loft.Sections = [(s, [""]) for s in sketches[1:]]
  │     loft.Ruled = False ; loft.Closed = False ; loft.Solid = True
  │     mirror = body.newObject("PartDesign::Mirrored", "HullMirror")    ; added.append(mirror)
  │     mirror.Originals = [loft]
  │     mirror.MirrorPlane = (body.Origin.XZ_Plane, [""])
  │     body.Tip = mirror
  │     target_doc.recompute()
  │
  ├── except HullConstructionError:
  │     for obj in reversed(added):
  │         target_doc.removeObject(obj.Name)
  │     raise
  │
  └── except BaseException as exc:
        for obj in reversed(added):
            target_doc.removeObject(obj.Name)
        raise HullConstructionError(...) from exc
  │
  ├── duration = perf_counter() - started
  └── return Hull(body=body, parameters=parameters, document=target_doc,
                  label=body.Label, build_duration_seconds=duration)
```

State machine depth: linear, no branches (except the exception path). Trivial. `/tla` will hit the triviality gate post-implementation.

---

## 10. What changes vs. v0.1.0-alpha (diff scope)

**Unchanged code** (~95% of `hull.py`):
- Module docstring, imports
- `HullParameterError`, `HullConstructionError` exception classes
- `HullParameters` dataclass + `__post_init__` validation
- `_validate_hull_parameters` helper
- `_StationProfile` dataclass + `_compute_stations` function
- `_resolve_document`, `_resolve_body_label` helpers
- `_bind_parameters_to_body_properties` helper
- `Hull` dataclass
- `build_hull` outer scaffolding (parameter resolution, document resolution, return value)

**Replaced code** (~80 lines, two private functions):
- `_create_station_sketch(profile, body, parent_doc)` → new signature: `_create_station_sketch(profile, body, datum)` returning the sketch (using `body.newObject("Sketcher::SketchObject", ...)`).
- `_apply_loft_and_mirror(body, sketches, parent_doc)` → new internal: calls `body.newObject("PartDesign::AdditiveLoft", ...)` and `body.newObject("PartDesign::Mirrored", ...)`, sets `body.Tip = mirror`.

**Added code** (~30 lines):
- `_create_datum_plane(profile, body)` returning the Body-local datum.
- The rollback `added: list` tracking inside `build_hull`'s try/except.

**Hash baselines** (`tests/geometry/fixtures/expected_hashes.toml`): regenerated from scratch in polish phase.

**New tests** (~3 small files): `test_hull_partdesign_feature_types.py` asserts the feature graph uses PartDesign types only.

---

## Cross-references

- Public API contract (unchanged) → [contracts/python-api-preserved.md](./contracts/python-api-preserved.md)
- Usage walkthrough → [quickstart.md](./quickstart.md)
- Formal invariants → [spec.allium](./spec.allium)
- Acceptance criteria → [spec.md](./spec.md) §Success Criteria
- v0.1.0-alpha (current) code → `src/storebro/hull.py` lines 217-318 (preserved) + 345-460 (replaced)
