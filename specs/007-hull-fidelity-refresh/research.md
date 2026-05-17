# Research: Hull Fidelity Refresh (Phase 0)

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-05-17

---

## R1. Reference source — storebropassion.de

### Decision

The new HullParameters defaults come from the textual specification scraped from `https://www.storebropassion.de/index.php?mod=bootdata&boat=storo34&lng=se` (WebFetched during spec authoring on 2026-05-17). The side-profile illustration in `docs/references/Alternativ3.JPG`'s upper half corroborates the silhouette.

### Extracted facts

| Spec | Value |
|---|---|
| LOA | 10.35 m |
| Beam | 3.20 m |
| Draft | **1.10 m** |
| Freeboard fwd | **1.16 m** |
| Freeboard aft | **0.95 m** |
| Height above WL | 3.15 m (total air-draft including hardtop) |
| Displacement | 5.0–7.0 tonnes |
| Hull type | semi-displacement (cruising) |
| Production | 1966–1988; "Storö IV" design phase through 1974 (covers 1972 model year) |
| Designer | Einar Runius (hull); Winfried H. Wilke (deck / interior) |

### Rationale

- The website is a community/registry resource, not a primary naval-architecture source, but it has more dimensional detail than I could derive from photographs alone.
- The "semi-displacement" classification is the single most important clue: it tells me the bottom is flatter than a planing hull (deadrise 6-10° vs 18-22°) and the hull is symmetric front-to-back proportions, not "fast bow + flat aft".
- Einar Runius's design language (Storebro Runö 31 / 34 / 36 line) is consistent: rounded bilges, near-plumb stem with slight rake, vertical transom, flat sheer.

### Alternatives considered

- **Wikipedia**: insufficient dimensional detail.
- **Sjöhistoriska museet**: would require physical archive access.
- **Modeling-forum reconstructions**: secondary sources, less authoritative than storebropassion.de's curated registry.

---

## R2. Decision: 5 parameter-default changes + 1 new field

### Decision

Apply these changes to `HullParameters` in `src/storebro/hull.py`:

```python
@dataclass(frozen=True)
class HullParameters:
    loa: float = 10.35                        # unchanged
    beam_max: float = 3.20                    # unchanged
    draft: float = 1.10                       # was 0.95
    freeboard: float = 0.95                   # semantic preserved (used by _compute_stations as freeboard reference)
    deadrise_amidships: float = 8.0           # was 16.0
    sheer_height_aft: float = 0.95            # was 0.85
    sheer_height_fwd: float = 1.16            # was 1.30
    transom_angle: float = 5.0                # was 12.0
    stem_rake_angle: float = 6.0              # NEW — range [0, 30]
```

The reference dict `REFERENCE_STOREBRO_ROYAL_CRUISER_34_1972` is also updated to mirror.

### Validation update

`_validate_hull_parameters` adds a range check for `stem_rake_angle`:
```python
if not (0.0 <= p.stem_rake_angle <= 30.0):
    raise HullParameterError("stem_rake_angle", p.stem_rake_angle, "[0, 30] degrees")
```

### Rationale

- 6.0° stem rake is a moderate Einar-Runius-typical value: visually almost vertical but with the slight forward lean characteristic of the 1970s Storebro line.
- `freeboard = 0.95` semantically aligns with sheer_height_aft now (both represent the transom-side deck height); v1.0.0 had them inconsistent.

### Alternatives considered

- Repurpose `freeboard` to be a 9th-name like `stem_rake_angle` semantically: rejected — risks breaking downstream user code that reads `params.freeboard`. Additive is safer.

---

## R3. Decision: blunt rectangular stem face

### Decision

The stem station's `_StationProfile` changes from `is_terminal=True` (which the construction interprets as a `Part.Point` vertex profile) to a finite half-section with:
- `half_beam_at_top = 0.040` (40mm → 80mm full width)
- `half_beam_at_bottom = 0.040` (constant; the stem face is a tall narrow rectangle, not a triangle)
- `keel_depth = 0.0` (zero — the stem terminates at the waterline)
- `freeboard = sheer_height_fwd`
- `is_terminal = False` (the construction code falls through to the normal rounded-bilge sketch)

`_create_station_sketch` no longer special-cases the stem; the stem becomes a normal (small, narrow) station. The bilge-arc construction (R5) collapses gracefully at this scale because the arc's radius is `half_beam_at_bottom × 0.5 = 20mm` — still valid for Sketcher.

### Rationale

- A real RC34's stem is ~80-100mm wide (the visible bow strip / stem-piece on classic Scandinavian boats), not a knife edge.
- Replacing the degenerate-vertex profile with a normal-shape-but-small-dimensions profile means the loft has a CONTINUOUS profile-shape topology all the way through. This is what unblocks `Ruled=False` (R4).

### Alternatives considered

- **Tall-thin-triangle stem**: rejected — would still degenerate at the top corner.
- **Keep the vertex but use spline-tangency hints**: rejected — FreeCAD's PartDesign AdditiveLoft doesn't expose tangency controls via Python in a stable cross-version way.

---

## R4. Decision: stem datum tilted via Y-axis rotation

### Decision

In `_create_datum_plane`, the stem datum's `AttachmentOffset` is constructed with both translation AND rotation:

```python
import math

if profile.name == "Stem":
    rotation = FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), profile.stem_rake_angle_deg)
else:
    rotation = FreeCAD.Rotation()  # identity

datum.AttachmentOffset = FreeCAD.Placement(
    FreeCAD.Vector(0.0, 0.0, profile.x_position * _MM_PER_M),
    rotation,
)
```

The Y-axis is the support plane's (YZ_Plane's) horizontal local axis, so rotating around it tilts the new datum forward (positive rake) or backward (negative rake) in global X.

The stem sketch attached to this tilted datum produces a stem face that leans forward by `stem_rake_angle` degrees from vertical.

### Rationale

- FreeCAD-idiomatic: the datum's Placement.Rotation is the canonical knob for "tilt this plane".
- Geometry: a plane attached to YZ with a Y-rotation is no longer parallel to YZ but rotates around the global Y axis (which is the YZ-plane's local horizontal axis). Result: the plane's normal vector tilts in the XZ plane, exactly what "stem rake" describes.

### Alternatives considered

- **Offset X-position by `freeboard × tan(rake)`**: rejected per clarify Q1. Less idiomatic.
- **Build the stem sketch with skewed geometry**: rejected — harder to maintain, and the sketch's local coordinates would no longer correspond to "real" XYZ.

---

## R5. Decision: quarter-circle bilge arc on non-stem stations

### Decision

For each non-stem station (Transom, Aft, Amidships, Fwd), the `_create_station_sketch` function replaces the v1.0.0 line segment from `(0, -keel_depth)` to `(half_beam_at_bottom, -keel_depth × 0.6)` with a `Part.ArcOfCircle`:

```python
import Part, FreeCAD

bilge_radius = profile.half_beam_at_bottom * 0.5  # meters

# Quarter-circle from keel-centerline (90°) to bottom-outer (0°),
# centered at (bilge_radius, -keel_depth + bilge_radius).
center_x = bilge_radius
center_y = -profile.keel_depth + bilge_radius
arc_circle = Part.Circle(
    FreeCAD.Vector(center_x * _MM_PER_M, center_y * _MM_PER_M, 0),
    FreeCAD.Vector(0, 0, 1),  # normal — pointing out of the sketch plane
    bilge_radius * _MM_PER_M,
)
# 90° arc (π/2 radians) from keel-centerline endpoint to bottom-outer endpoint
arc = Part.ArcOfCircle(arc_circle, math.pi, 1.5 * math.pi)
sketch.addGeometry(arc, False)
```

The remaining 4 line segments (bottom-outer → top-outer → outer-sheer → centerline-deck → close-to-keel) stay as `Part.LineSegment` calls just like v1.0.0.

The Coincident constraints loop now connects: arc-end (1) → line1-start (2), line1-end → line2-start, ... line4-end → arc-start (closing the loop).

### Rationale

- Quarter-circle is the simplest representation of a rounded bilge and matches Einar Runius's design language for the Storebro line.
- Predictable: the arc's curvature is fully determined by `half_beam_at_bottom`, no new parameter needed.
- B-spline-loft-safe: smooth curves don't trigger the AdditiveLoft twist failure mode.

### Alternatives considered

- **B-spline bilge with custom control points**: rejected per clarify Q3. More flexible but harder to constrain and adds complexity.
- **Skip the arc, keep pentagons**: rejected — the entire point of FR-005 is the rounded-bilge appearance.

---

## R6. Decision: AdditiveLoft Ruled=False with auto-fall-back

### Decision

`_apply_loft_and_mirror` builds the loft with `Ruled=False`. After `target_doc.recompute()`, inspect the loft's shape:

```python
import logging

loft = body.newObject("PartDesign::AdditiveLoft", "HullLoft")
loft.Profile = (sketches[0], [""])
loft.Sections = [(s, [""]) for s in sketches[1:]]
loft.Ruled = False
loft.Closed = False
target_doc.recompute()

if (
    loft.Shape is None
    or loft.Shape.Volume <= 0
    or not loft.Shape.isClosed()
    or loft.Shape.BoundBox.XLength <= 0
):
    logging.warning(
        "PartDesign::AdditiveLoft with Ruled=False produced invalid shape "
        "(volume=%.3e, closed=%s, bbox.X=%.1f) — falling back to Ruled=True",
        loft.Shape.Volume if loft.Shape else 0.0,
        loft.Shape.isClosed() if loft.Shape else False,
        loft.Shape.BoundBox.XLength if loft.Shape else 0.0,
    )
    body.removeObject(loft.Name)
    target_doc.recompute()
    loft = body.newObject("PartDesign::AdditiveLoft", "HullLoft")
    loft.Profile = (sketches[0], [""])
    loft.Sections = [(s, [""]) for s in sketches[1:]]
    loft.Ruled = True
    loft.Closed = False
    target_doc.recompute()
```

The mirror feature is then built on the (possibly-fallback) loft, same as v1.0.0.

### Rationale

- For default RC34 parameters, B-spline interpolation across the new smooth, finite-stem profiles is expected to produce a valid loft. The blunt stem face (R3) was the missing piece for spec 006's failed `Ruled=False` attempt.
- The fall-back is a safety net for users who push HullParameters out of envelope (extreme deadrise, draft, beam). The legacy Ruled=True is known to work for "any reasonable input".
- `logging.warning` (not `raise`) keeps the build succeeding; users see a clear message in stderr but get a hull anyway.

### Alternatives considered

- **Always Ruled=False, raise on failure**: rejected — would regress the spec 006 "loft always works" property for extreme parameters.
- **User-facing `loft_mode` parameter**: rejected — adds API surface without enough payoff. The auto-fall-back is the right default.

---

## R7. Decision: 9th Body property `StemRakeAngle`

### Decision

`_bind_parameters_to_body_properties` adds:

```python
body.addProperty(
    "App::PropertyAngle",
    "StemRakeAngle",
    "Hull",
    "Stem rake from vertical (forward lean of bow)",
)
body.StemRakeAngle = parameters.stem_rake_angle
```

### Rationale

- Consistent with v1.0.0's 8 informational Body properties — adding the 9th alongside the new `HullParameters.stem_rake_angle` field.
- Visible in the FreeCAD GUI's Property panel — confirms the parameter is wired through.

### Alternatives considered

- **Skip the property**: rejected — would leave the new field invisible in the GUI.

---

## R8. Decision: hash baselines re-seed in polish phase

### Decision

Same approach as spec 006: run `uv run python tests/geometry/fixtures/refresh_hashes.py` after implementation lands, paste the new TOML stanzas into `tests/geometry/fixtures/expected_hashes.toml`, commit the file.

### Rationale

- The hull shape changes structurally. Old hashes will mismatch.
- Constitution principle II's byte-determinism guarantee applies at the new baselines: two consecutive builds with identical parameters produce identical bytes.

### Alternatives considered

- **Reset baselines automatically in CI**: rejected — would mask future drift.

---

## Summary of decisions

| ID | Decision | Resolves |
|---|---|---|
| R1 | Reference = storebropassion.de textual specs + Alternativ3.JPG profile | Reference fidelity |
| R2 | 5 HullParameters default changes + new `stem_rake_angle` field | FR-001, FR-002 |
| R3 | Stem becomes finite blunt rectangle (40mm half-width × full sheer-height) | FR-003 |
| R4 | Stem datum tilts via `AttachmentOffset.Rotation(Vector(0,1,0), rake)` | Clarify Q1 |
| R5 | Non-stem sketches use `Part.ArcOfCircle` for rounded bilge | Clarify Q3 / FR-005 |
| R6 | AdditiveLoft Ruled=False with auto-fall-back to Ruled=True | Clarify Q2 / FR-004 |
| R7 | Add 9th Body property `StemRakeAngle` | FR-007 |
| R8 | Hash baselines re-seed in polish phase | FR-009 / constitution II |

All NEEDS CLARIFICATION resolved.
