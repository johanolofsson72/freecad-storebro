# Data Model: Hull Fidelity Refresh (Phase 1)

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md) | **Date**: 2026-05-17

---

## 1. Updated `HullParameters` dataclass

```python
@dataclass(frozen=True)
class HullParameters:
    loa: float = 10.35
    beam_max: float = 3.20
    draft: float = 1.10                     # CHANGED 0.95 → 1.10
    freeboard: float = 0.95
    deadrise_amidships: float = 8.0         # CHANGED 16.0 → 8.0
    sheer_height_aft: float = 0.95          # CHANGED 0.85 → 0.95
    sheer_height_fwd: float = 1.16          # CHANGED 1.30 → 1.16
    transom_angle: float = 5.0              # CHANGED 12.0 → 5.0
    stem_rake_angle: float = 6.0            # NEW

    REFERENCE_STOREBRO_ROYAL_CRUISER_34_1972: ClassVar[dict[str, float]] = {
        "loa": 10.35,
        "beam_max": 3.20,
        "draft": 1.10,
        "freeboard": 0.95,
        "deadrise_amidships": 8.0,
        "sheer_height_aft": 0.95,
        "sheer_height_fwd": 1.16,
        "transom_angle": 5.0,
        "stem_rake_angle": 6.0,
    }
```

**Field count: 9** (was 8). Additive change per constitution VI = PATCH-level.

---

## 2. `_StationProfile` dataclass (unchanged shape, new value at Stem)

```python
@dataclass(frozen=True)
class _StationProfile:
    name: str
    x_position: float
    half_beam_at_top: float
    half_beam_at_bottom: float
    keel_depth: float
    freeboard: float
    is_terminal: bool
    # NEW field (additive; existing callers can ignore)
    stem_rake_angle_deg: float = 0.0
```

The `stem_rake_angle_deg` field is non-zero ONLY for the Stem profile. Other stations carry 0.0.

---

## 3. Updated station profile values (`_compute_stations`)

| Station | x_position | half_beam_at_top | half_beam_at_bottom | keel_depth | freeboard | is_terminal | stem_rake_angle_deg |
|---|---|---|---|---|---|---|---|
| Transom | 0.0 | 1.12 (= 1.6 × 0.70) | 0.672 (= 1.12 × 0.60) | 0.825 (= 1.10 × 0.75) | 0.95 | False | 0.0 |
| Aft | 2.5875 | 1.472 (= 1.6 × 0.92) | 0.736 (= 1.472 × 0.50) | 1.045 (= 1.10 × 0.95) | 1.0025 | False | 0.0 |
| Amidships | 5.175 | 1.600 (= beam_max/2) | 0.640 (= 1.6 × 0.40) | 1.100 (= draft) | 0.95 | False | 0.0 |
| Fwd | 7.7625 | 0.880 (= 1.6 × 0.55) | 0.264 (= 0.88 × 0.30) | 0.605 (= 1.10 × 0.55) | 1.1075 | False | 0.0 |
| Stem | 10.35 | **0.040** (NEW: 40mm) | **0.040** (NEW: constant) | **0.0** (NEW) | 1.16 | **False** (CHANGED) | **6.0** (NEW) |

Stem changes from degenerate vertex (half_beam = 0, is_terminal = True) to a finite 80mm-wide × 1.16m-tall rectangular face.

---

## 4. PartDesign feature graph (unchanged topology)

```
PartDesign::Body  "HullBody"  (Tip → MirrorFeature)
├── Origin (auto-created)
├── PartDesign::Plane  "HullDatumTransom"     @ X = 0
├── PartDesign::Plane  "HullDatumAft"         @ X = 2.5875 m
├── PartDesign::Plane  "HullDatumAmidships"   @ X = 5.175 m
├── PartDesign::Plane  "HullDatumFwd"         @ X = 7.7625 m
├── PartDesign::Plane  "HullDatumStem"        @ X = 10.35 m, ROTATED 6° around Y-axis ← CHANGED
├── Sketcher::SketchObject  "HullStationTransom"   (5-line + 1-arc rounded-bilge profile) ← CHANGED
├── Sketcher::SketchObject  "HullStationAft"       (5-line + 1-arc rounded-bilge profile) ← CHANGED
├── Sketcher::SketchObject  "HullStationAmidships" (5-line + 1-arc rounded-bilge profile) ← CHANGED
├── Sketcher::SketchObject  "HullStationFwd"       (5-line + 1-arc rounded-bilge profile) ← CHANGED
├── Sketcher::SketchObject  "HullStationStem"      (5-line CLOSED RECTANGLE — 80mm × 1.16m) ← CHANGED
├── PartDesign::AdditiveLoft  "HullLoft"     Ruled=False (with auto-fall-back to True) ← CHANGED
└── PartDesign::Mirrored      "HullMirror"   (Body.Tip — unchanged from v1.0.0)
```

Topology counts unchanged: 5 datums + 5 sketches + 1 AdditiveLoft + 1 Mirrored.

---

## 5. Stem sketch geometry detail (FR-003)

Stem station sketch — 5 line segments forming a closed rectangle:

```python
# Local frame: x = transverse (Y in body), y = vertical (Z in body)
pts = [
    Vector(0.0, 0.0, 0.0),                    # bottom-center at waterline
    Vector(40.0, 0.0, 0.0),                   # bottom-outer (40mm half-width)
    Vector(40.0, 1160.0, 0.0),                # top-outer (1160mm = 1.16m sheer height)
    Vector(0.0, 1160.0, 0.0),                 # top-center (deck centerline)
    Vector(0.0, 0.0, 0.0),                    # close to bottom-center
]
# 5 line segments + 5 Coincident constraints + 1 closed wire
```

No bilge arc (the stem face is rectangular, not boat-bottom).

The datum this attaches to has `AttachmentOffset.Rotation = Rotation(Vector(0,1,0), 6.0°)` so the sketch's local Z-axis (vertical in sketch) maps to a tilted-forward Z in world space — the stem face leans forward by 6° from vertical.

---

## 6. Non-stem sketch geometry detail (FR-005, R5)

Non-stem station sketch — 1 arc + 4 line segments forming a closed wire:

```python
# Computed once per station from _StationProfile fields
keel_depth_mm = profile.keel_depth * 1000.0
half_beam_top_mm = profile.half_beam_at_top * 1000.0
half_beam_bottom_mm = profile.half_beam_at_bottom * 1000.0
freeboard_mm = profile.freeboard * 1000.0
bilge_radius_mm = half_beam_bottom_mm * 0.5

# 1. Quarter-circle bilge arc from keel-centerline to bottom-outer.
#    Arc center: (bilge_radius, -keel_depth + bilge_radius)
#    Arc spans 90° (π to 3π/2 in OpenCASCADE convention)
arc_center = Vector(bilge_radius_mm, -keel_depth_mm + bilge_radius_mm, 0)
arc_circle = Part.Circle(arc_center, Vector(0, 0, 1), bilge_radius_mm)
arc = Part.ArcOfCircle(arc_circle, math.pi, 1.5 * math.pi)
arc_id = sketch.addGeometry(arc, False)

# 2. Line segments (4):
seg_ids = []
seg_ids.append(sketch.addGeometry(Part.LineSegment(
    Vector(half_beam_bottom_mm, -keel_depth_mm + bilge_radius_mm, 0),   # bottom-outer (above bilge tangent)
    Vector(half_beam_bottom_mm, -keel_depth_mm * 0.6, 0),                # mid-side
), False))
# ... (3 more segments for: top-outer, sheer, centerline-to-keel)

# 3. Coincident constraints: chain arc → segments → close back to arc start
```

Resulting wire: smooth at the bilge corner (G1 continuity from arc to vertical side), kink-free at the other 4 corners (these are pentagonal corners between line segments — acceptable since they're at the topsides where the hull has discrete corners anyway).

---

## 7. Stem datum tilt (R4)

```python
def _create_datum_plane(profile: _StationProfile, body: Any) -> Any:
    import FreeCAD

    datum_name = f"HullDatum{profile.name}"
    datum = body.newObject("PartDesign::Plane", datum_name)
    yz_plane = _get_origin_plane(body, "YZ_Plane")
    datum.AttachmentSupport = [(yz_plane, "")]
    datum.MapMode = "FlatFace"

    if profile.name == "Stem" and profile.stem_rake_angle_deg > 0.0:
        rotation = FreeCAD.Rotation(
            FreeCAD.Vector(0, 1, 0),
            profile.stem_rake_angle_deg,
        )
    else:
        rotation = FreeCAD.Rotation()  # identity

    datum.AttachmentOffset = FreeCAD.Placement(
        FreeCAD.Vector(0.0, 0.0, profile.x_position * _MM_PER_M),
        rotation,
    )
    return datum
```

Only the Stem datum tilts. All others keep identity rotation.

---

## 8. AdditiveLoft auto-fall-back (R6)

```python
def _apply_loft_and_mirror(body: Any, sketches: list[Any]) -> tuple[Any, Any]:
    import logging

    loft = _build_loft(body, sketches, ruled=False)
    body.Document.recompute()

    if not _loft_is_valid(loft):
        logging.warning(
            "PartDesign::AdditiveLoft Ruled=False produced invalid shape "
            "(volume=%.3e, closed=%s) — falling back to Ruled=True",
            loft.Shape.Volume if loft.Shape else 0.0,
            loft.Shape.isClosed() if loft.Shape else False,
        )
        body.removeObject(loft.Name)
        body.Document.recompute()
        loft = _build_loft(body, sketches, ruled=True)
        body.Document.recompute()

    mirror = body.newObject("PartDesign::Mirrored", "HullMirror")
    mirror.Originals = [loft]
    mirror.MirrorPlane = (_get_origin_plane(body, "XZ_Plane"), [""])
    body.Tip = mirror
    return (loft, mirror)


def _build_loft(body: Any, sketches: list[Any], *, ruled: bool) -> Any:
    loft = body.newObject("PartDesign::AdditiveLoft", "HullLoft")
    loft.Profile = (sketches[0], [""])
    loft.Sections = [(s, [""]) for s in sketches[1:]]
    loft.Ruled = ruled
    loft.Closed = False
    return loft


def _loft_is_valid(loft: Any) -> bool:
    if loft.Shape is None:
        return False
    return (
        loft.Shape.Volume > 0.0
        and loft.Shape.isClosed()
        and loft.Shape.BoundBox.XLength > 0
    )
```

---

## 9. Updated Body properties (FR-007)

| Property name | FreeCAD type | Group | Source field | Status |
|---|---|---|---|---|
| `LOA` | `App::PropertyLength` | `Hull` | `parameters.loa` | unchanged |
| `BeamMax` | `App::PropertyLength` | `Hull` | `parameters.beam_max` | unchanged |
| `Draft` | `App::PropertyLength` | `Hull` | `parameters.draft` | unchanged |
| `Freeboard` | `App::PropertyLength` | `Hull` | `parameters.freeboard` | unchanged |
| `SheerHeightAft` | `App::PropertyLength` | `Hull` | `parameters.sheer_height_aft` | unchanged |
| `SheerHeightFwd` | `App::PropertyLength` | `Hull` | `parameters.sheer_height_fwd` | unchanged |
| `DeadriseAmidships` | `App::PropertyAngle` | `Hull` | `parameters.deadrise_amidships` | unchanged |
| `TransomAngle` | `App::PropertyAngle` | `Hull` | `parameters.transom_angle` | unchanged |
| `StemRakeAngle` | `App::PropertyAngle` | `Hull` | `parameters.stem_rake_angle` | **NEW** |

9 properties total. Names, types, group all consistent with v1.0.0 conventions.

---

## 10. What changes in `hull.py` (diff scope)

**Unchanged** (preserved from spec 001 + 006):
- Module docstring, imports (one new: `import logging` at module top)
- `HullParameterError`, `HullConstructionError` exception classes
- `HullParameters.__post_init__`, `_validate_hull_parameters` (just adds one new range check for `stem_rake_angle`)
- `_resolve_document`, `_resolve_body_label` helpers
- `Hull` dataclass
- `build_hull` outer scaffolding (parameter resolution, document resolution, return value)
- `_get_origin_plane` helper
- Most of `_apply_loft_and_mirror` (just adds the auto-fall-back wrapper)
- `_create_datum_plane` (just adds the stem-rake rotation branch)

**Modified** (~80 LOC net new):
- `HullParameters` defaults (5 changes + 1 new field)
- `REFERENCE_STOREBRO_ROYAL_CRUISER_34_1972` reference dict
- `_validate_hull_parameters` (1 new range check)
- `_compute_stations` (5 station profiles with updated values, stem becomes finite-rectangle)
- `_create_station_sketch` (adds bilge-arc branch for non-stem; stem branch creates rectangle instead of `Part.Point`)
- `_apply_loft_and_mirror` (wraps loft build in auto-fall-back; uses `Ruled=False` by default)
- `_bind_parameters_to_body_properties` (adds `StemRakeAngle` property)

**Added** (~30 LOC):
- `_build_loft(body, sketches, *, ruled)` helper
- `_loft_is_valid(loft)` predicate

**Hash baselines** (`tests/geometry/fixtures/expected_hashes.toml`): regenerated.

**New tests** (~3 files):
- `tests/geometry/test_hull_bspline_loft.py` — asserts `Ruled=False` for canonical defaults
- `tests/geometry/test_hull_silhouette.py` — asserts bounding-box dimensions match reference within ±5%
- (Optional) `tests/unit/test_hull_parameters_stem_rake.py` — asserts `HullParameterError` on out-of-range `stem_rake_angle`

---

## 11. State transitions (build_hull execution flow, updated)

```
START
  │
  ├── _validate_hull_parameters(parameters)   (NOW includes stem_rake_angle range check)
  ├── _resolve_document, _resolve_body_label  (unchanged)
  ├── ensure_supported_freecad()              (unchanged)
  ├── added: list[Any] = []
  ├── try:
  │     body = target_doc.addObject("PartDesign::Body", "HullBody")
  │     added.append(body)
  │     target_doc.recompute()                (populates Origin features)
  │     _bind_parameters_to_body_properties(body, parameters)  ← NOW binds 9 props
  │     stations = _compute_stations(parameters)               ← NOW includes finite-stem
  │     for profile in stations:
  │         datum = _create_datum_plane(profile, body)         ← Stem gets rotation
  │         sketch = _create_station_sketch(profile, body, datum)  ← Bilge arc or stem rect
  │     loft, mirror = _apply_loft_and_mirror(body, sketches)  ← Auto-fall-back wrapper
  │     target_doc.recompute()
  │
  ├── except ...
  │     for obj in reversed(added):
  │         target_doc.removeObject(obj.Name)
  │     raise HullConstructionError(...)
  │
  └── return Hull(body=body, parameters=parameters, ...)
```

Linear flow, no new branches at the orchestration level. Triviality gate for `/tla` will hit again.

---

## Cross-references

- Public API contract (preserved) → [contracts/python-api-preserved.md](./contracts/python-api-preserved.md)
- Usage walkthrough → [quickstart.md](./quickstart.md)
- Formal invariants → [spec.allium](./spec.allium)
- Acceptance criteria → [spec.md](./spec.md) §Success Criteria
- v1.0.0 code → `src/storebro/hull.py` (gets modified in implementation phase)
- Reference image → `docs/references/Alternativ3.JPG` (upper half = side profile)
