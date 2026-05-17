# Feature Specification: Hull Fidelity Refresh

**Feature Branch**: `007-hull-fidelity-refresh`

**Created**: 2026-05-17

**Status**: Draft

**Input**: User description: "Hull fidelity refresh — re-derive the Storebro Royal Cruiser 34 1972 hull shape to match the storebropassion.de reference. The v1.0.0 hull is faceted (Ruled=True linear loft), uses planing-hull deadrise (16°) when the reference is semi-displacement, raked transom too far, has a pointed-vertex stem instead of a finite blunt face, and uses pentagon cross-sections instead of the rounded forms typical of an Einar Runius design. Goal: when a user opens the generated `.FCStd` in the FreeCAD GUI and looks at the side view, the silhouette is recognizably an RC34 1972, not a paper origami. PATCH-level shape refresh; v1.0.1 once shipped; no public API change."

## Clarifications

### Session 2026-05-17

- Q: How does `stem_rake_angle` geometrically affect the hull construction? → A: **Tilt the stem datum plane around the Y-axis by the rake angle**. The PartDesign datum at the stem station gets `AttachmentOffset.Rotation = Rotation(Vector(0,1,0), stem_rake_angle)`. The sketch attached to it sits perpendicular to the tilted datum, so the stem face leans forward by the rake angle from vertical. FreeCAD-idiomatic (the datum's normal direction is the source of truth). Alternative considered: offsetting the X-position based on freeboard × tan(rake) — rejected as less idiomatic.
- Q: How does the Ruled=False → Ruled=True fall-back trigger when the smooth loft fails for an extreme parameter combination? → A: **Automatic at construction time**. Build the AdditiveLoft with `Ruled=False`; after `target_doc.recompute()`, inspect `loft.Shape`. If the shape is invalid (`Volume <= 0`, `not isClosed()`, or `BoundBox.XLength <= 0`), DELETE the loft, recreate it with `Ruled=True`, recompute again, and log a warning via the standard `logging` module. The user's `HullParameters` stays unchanged; the fall-back is transparent. No new public knob.
- Q: For the rounded-bilge cross-section (FR-005), what's the exact sketch geometry? → A: **Quarter-circle arc at the bottom corner**. Each non-stem station sketch replaces the line segment between the keel-centerline point and the bottom-outer point with a `Part.ArcOfCircle` that has `bilge_radius = profile.half_beam_at_bottom × 0.5`. The arc's center is at `(half_beam_at_bottom × 0.5, -keel_depth + bilge_radius)` in the sketch's local frame. The arc starts at the keel-centerline endpoint and ends at the bottom-outer endpoint. The remaining 4 line segments (bottom-outer → top-outer → sheer → centerline → back to start) are unchanged. Stem station keeps its rectangular shape (no arc; FR-003).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Side-view silhouette matches the RC34 1972 reference (Priority: P1, MVP)

A boat restorer opens the generated `.FCStd` in FreeCAD GUI, rotates to the **right side view**, and compares the silhouette against the storebropassion.de reference drawing (mirrored in `docs/references/Alternativ3.JPG`'s upper half). The hull shape — sheer line, stem rake, transom rake, freeboard variation — is recognizably the same boat: a low-profile Scandinavian semi-displacement motoryacht with near-vertical bow and stern.

**Why this priority**: This is the entire point of the spec. The v1.0.0 hull constructs valid geometry but doesn't *look like an RC34*. Constitution principle IV ("default parameter set MUST produce hull and interior geometry that matches the historical Storebro proportions") was satisfied only on principal dimensions (LOA, beam); the silhouette is alpha-grade and visually wrong. P1 closes that fidelity gap.

**Independent Test**: On a host with FreeCAD 1.1+, build the default hull and open in GUI. Switch to right-side view (number key `3`). Visually compare against `docs/references/Alternativ3.JPG` profile. Verify: (a) stem is near-vertical with slight forward rake, not a sharp 12° rake; (b) transom is near-vertical, not 12° aft rake; (c) sheer line is near-flat, not rising 450mm from aft to bow; (d) freeboard heights match the reference (~0.95m aft, ~1.16m fwd). Capture a screenshot for the PR description per constitution V.

**Acceptance Scenarios**:

1. **Given** a generated `.FCStd` on a FreeCAD 1.1+ host, **When** the user rotates to right-side view, **Then** the hull silhouette shows a near-vertical bow (stem rake ≤10° from vertical), a near-vertical transom (transom angle ≤8°), and a sheer line rising no more than 250mm from aft to bow.
2. **Given** the same setup, **When** the user measures the hull's bounding box, **Then** the X-extent is 10.35m ±1% (LOA), Y-extent is 3.20m ±1% (beam), and the freeboard heights at aft / fwd stations match the reference (0.95m / 1.16m) within ±5%.
3. **Given** the same setup, **When** the user inspects the bow tip in 3D, **Then** the bow has a finite face (not a knife-edge point) approximately 80-100mm wide that matches the reference's blunt stem.

---

### User Story 2 — Smooth hull surface (no faceted wedge) (Priority: P1)

The hull surface, viewed from any angle in FreeCAD GUI's 3D mode, appears smoothly curved between station profiles instead of piecewise-linear. There are no visible "fold lines" between stations at the level of detail visible to the naked eye in a standard isometric view.

**Why this priority**: The faceted appearance is the second-most-visible defect after the silhouette. A smooth hull surface signals "real boat" instead of "origami". The fix is internal — switch loft interpolation from `Ruled=True` (piecewise-linear) to `Ruled=False` (B-spline). This was attempted in spec 006 and caused twisting; spec 007 unblocks it by replacing the degenerate vertex stem (the trigger for B-spline twist) with a finite blunt stem face.

**Independent Test**: Open the generated `.FCStd` in FreeCAD GUI, rotate to axonometric, zoom to amidships. The transition between Aft station (X≈2.59m) and Amidships station (X≈5.18m) shows a smooth curve, not a piecewise-linear fold. No visible "creases" where stations connect.

**Acceptance Scenarios**:

1. **Given** the generated `.FCStd`, **When** the user views the hull from axonometric and zooms to the midbody region, **Then** the visible surface curvature between adjacent stations is continuous (G1 continuity), not discontinuous.
2. **Given** the same setup, **When** the user checks the AdditiveLoft feature's `Ruled` property in the Property panel, **Then** the value is `False` (B-spline mode), not `True` (piecewise-linear).

---

### User Story 3 — Backward compatibility preserved (Priority: P2)

All 96 existing geometry tests + 235 existing unit tests continue to pass. The public `Hull` dataclass surface, `HullParameters` field set (with one additive new field), `HullParameterError` / `HullConstructionError` shapes are unchanged. Downstream modules (`deck`, `interior`, `export`, `cli`) work without source-code changes.

**Why this priority**: This is a PATCH-level shape refresh. No consumer should need to update their code. If `build_hull()` returns a different SHAPE for the same parameter defaults, that's the WHOLE POINT of the spec; but the *signature* and *attribute set* on the return value must stay identical.

**Independent Test**: After implementation, run `uv run pytest` — all 331+ tests pass except those that explicitly hash-baseline-compare geometry (those need refresh in the polish phase, expected per constitution VII).

**Acceptance Scenarios**:

1. **Given** the rebuilt hull module, **When** the existing geometry tests run (`uv run pytest -m requires_freecad`), **Then** all topology / parametricity / determinism / GUI-editability tests pass without modification.
2. **Given** the same setup, **When** the CLI smoke test runs (`uv run storebro build --out /tmp/boat.FCStd`), **Then** the exit code is 0 and the file opens cleanly in FreeCAD GUI.
3. **Given** the rebuilt hull module, **When** `HullParameters` is constructed with default values, **Then** the existing eight named properties on `Hull.body` still exist, and a new `StemRakeAngle` property appears (additive).

---

### Edge Cases

- **Hash-baseline reset**: spec 002's byte-determinism baselines change because the hull shape changes. `tests/geometry/fixtures/expected_hashes.toml` re-seeds via `refresh_hashes.py` as part of the polish phase, like in spec 006.
- **B-spline interpolation failure**: if the new smoother station profiles still produce a self-intersecting `Ruled=False` loft for some parameter combination, fall back to `Ruled=True` for the offending station segment with a runtime warning, NOT a `HullConstructionError`. The spec MUST NOT regress to v1.0.0's "loft fails entirely" failure mode.
- **Reference fidelity tolerance**: the textual reference gives precise principal dimensions but the side-profile drawing is a stylized illustration, not a lines drawing. The implementation matches dimensions exactly where text says so (LOA, beam, draft, freeboards), and matches the silhouette visually within ±5% on derived heights.
- **Pentagonal-profile users**: any user code built against the v1.0.0 hull's exact pentagon cross-section at amidships will see a different shape. Acceptable per constitution VI (the *Shape* is implementation detail; `body.Shape` is public but its exact geometry is not contract).
- **Out-of-envelope stem rake**: `stem_rake_angle` outside `[0, 30]` degrees raises `HullParameterError`. Inside the range, extreme values may produce non-manifold lofts — caught by the rebuild logic and raised as `HullConstructionError` with the parameter combination.
- **Visual signoff regeneration**: the `storebro_v1_signoff.FCStd` is regenerated to `storebro_v1.0.1_signoff.FCStd`. Previous visual signoff (the faceted-origami one) is superseded; constitution V's signoff line in the PR description must reference the new artifact.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `HullParameters` MUST update its default values to match the storebropassion.de specification:
    - `draft = 1.10` (was 0.95)
    - `sheer_height_aft = 0.95` (was 0.85) — represents the deck height at the transom station
    - `sheer_height_fwd = 1.16` (was 1.30) — represents the deck height at the stem station
    - `deadrise_amidships = 8.0` (was 16.0) — semi-displacement hull, not planing
    - `transom_angle = 5.0` (was 12.0) — near-vertical transom per reference
    - `freeboard = 0.95` is preserved as the field but its semantic meaning aligns with `sheer_height_aft` (the visible freeboard at the transom). If the v1.0.0 code used `freeboard` for a different purpose, the implementation reconciles them so the resulting geometry matches the reference.
- **FR-002**: `HullParameters` MUST gain a new field `stem_rake_angle: float = 6.0` representing the forward lean of the bow's stem face from vertical (in degrees). Validation range: `[0, 30]` degrees. Backward-compatible (added field with default; existing callers passing 8 positional args still work). Per clarify Q1: applied as a Y-axis rotation in the stem datum's `AttachmentOffset.Rotation`, tilting the stem datum plane forward by `stem_rake_angle` degrees. The stem sketch attached to it sits perpendicular to the tilted plane.
- **FR-003**: The stem station profile MUST become a finite, blunt rectangular half-section instead of a degenerate vertex. The half-section dimensions: approximately 80mm half-beam-at-top × full sheer-height-fwd height, with the keel-depth-at-stem position at the waterline (zero keel depth). The blunt stem face represents the visible stem strip on a real RC34 (~80-100mm wide).
- **FR-004**: The hull's AdditiveLoft MUST use `Ruled=False` (B-spline interpolation) to produce a smooth curved surface between station profiles. Spec 006's twist failure mode is fixed because the stem is no longer degenerate (per FR-003). Per clarify Q2: if the smooth loft fails (zero volume, non-closed, or degenerate bounding box) at recompute time, the implementation MUST automatically delete the loft, recreate it with `Ruled=True`, recompute again, and log a warning via `logging.warning(...)`. The fall-back is transparent to the user — no new `HullParameters` field is exposed.
- **FR-005**: Station profile cross-sections MUST use rounded bilges (the transition from hull bottom to topsides is curved, not a hard corner). Per clarify Q3: each non-stem station sketch replaces the line segment between the keel-centerline point and the bottom-outer point with a `Part.ArcOfCircle` having radius `bilge_radius = profile.half_beam_at_bottom × 0.5`. The arc's center is at `(half_beam_at_bottom × 0.5, -keel_depth + bilge_radius)` in the sketch's local frame; arc start = keel-centerline endpoint; arc end = bottom-outer endpoint. The remaining 4 line segments (bottom-outer → top-outer → sheer-outer → centerline → close to keel) are unchanged. Stem station keeps its rectangular shape (no arc; FR-003).
- **FR-006**: The public `Hull` dataclass surface (fields: `body`, `parameters`, `document`, `label`, `build_duration_seconds`) MUST remain unchanged.
- **FR-007**: The eight named Body properties (`Loa`, `BeamMax`, `Draft`, `Freeboard`, `DeadriseAmidships`, `SheerHeightAft`, `SheerHeightFwd`, `TransomAngle`) MUST remain. A ninth property `StemRakeAngle` is added.
- **FR-008**: `HullParameterError` and `HullConstructionError` attribute shapes MUST remain unchanged.
- **FR-009**: All 96 currently-passing geometry tests MUST continue to pass on the new shape, with the following accommodations:
    - Hash-baseline tests (`expected_hashes.toml` rows for `step`, `stl`, `brep`, `fcstd`) re-seed via `refresh_hashes.py` in the polish phase; passing after re-seed.
    - `test_hull_default_dimensions.py` continues to pass: LOA and beam_max didn't change, the test still asserts ±1%.
    - `test_hull_construction_errors.py` continues to pass: rollback discipline preserved.
    - `test_hull_topology.py` continues to pass: hull remains a closed manifold solid.
    - `test_hull_partdesign_feature_types.py` continues to pass: PartDesign feature graph topology unchanged (5 datums + 5 sketches + AdditiveLoft + Mirrored).
- **FR-010**: New tests MUST verify the silhouette dimensions match the storebropassion.de reference within ±5%: height-above-waterline 3.15m (allowing hardtop+pillars variability), freeboard at transom 0.95m, freeboard at stem 1.16m, draft 1.10m.
- **FR-011**: The PartDesign feature graph topology MUST remain: 5 datum planes + 5 station sketches + 1 AdditiveLoft + 1 Mirrored. The stem station sketch shape changes (vertex → small rectangle); the other 4 sketches retain their general structure but with the rounded-bilge profile shape from FR-005.
- **FR-012**: Visual signoff workflow: regenerate `storebro_v1.0.1_signoff.FCStd` on a developer host, open in FreeCAD GUI, capture a screenshot of the right-side view. Compare against `docs/references/Alternativ3.JPG`'s upper-half profile. Documented in the PR description per constitution V: "Visually verified in FreeCAD: 1.1.x on \<OS\> — silhouette matches reference within tolerance."

### Key Entities

- **HullParameters (updated)**: 9 fields total — 8 v1.0.0 fields with default-value changes (draft, sheer_height_aft, sheer_height_fwd, deadrise_amidships, transom_angle changed; loa, beam_max, freeboard unchanged), plus 1 new `stem_rake_angle`. Validation rules updated for `deadrise_amidships` (still `[0, 30]`) and the new `stem_rake_angle` (`[0, 30]`).
- **Station Profile (changed)**: Stem station profile changes from degenerate vertex to finite blunt rectangle. Other station profiles' cross-section shape changes from pentagon to a rounded-bilge form. Internal `_StationProfile` dataclass may gain new fields (e.g., `bilge_radius`) or its layout may be refactored.
- **Loft Configuration (changed)**: `Ruled` switches from True to False; if a parameter combination produces a self-intersecting loft, a fall-back path (Ruled=True) MAY apply with a runtime warning.
- **Reference Image**: `docs/references/Alternativ3.JPG`'s upper half (the side profile from storebropassion.de) is the visual ground-truth. The lower half (interior layout) is unrelated to this spec.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A side-by-side visual comparison of the generated hull's right-side silhouette against `docs/references/Alternativ3.JPG`'s upper-half profile shows visual similarity ≥80% by maintaining: stem near-vertical (±10°), transom near-vertical (±8°), sheer near-flat (rise ≤250mm), freeboard heights matching ±50mm. Subjectively verified by the maintainer; documented in PR description.
- **SC-002**: 96 of 96 currently-passing geometry tests pass on FreeCAD 1.1+ (hash-baseline tests pass after re-seed via `refresh_hashes.py`).
- **SC-003**: Build time `build_hull()` < 30s on a developer laptop (same budget as v1.0.0).
- **SC-004**: Hull bounding box matches reference: X-extent 10.35m ±1%, Y-extent 3.20m ±1%, Z-extent including hardtop+pillars 3.15m ±5%.
- **SC-005**: The generated `.FCStd` opens in FreeCAD GUI in under 5 seconds and the hull shape recomputes successfully when a station sketch is edited (FR-004 GUI editability preserved from spec 006).
- **SC-006**: No regression in downstream modules: `uv run pytest -m requires_freecad tests/geometry/test_deck_*.py tests/geometry/test_interior_*.py tests/geometry/test_export_*.py tests/geometry/test_cli_build_*.py -v` reports 0 failures.
- **SC-007**: Hull surface visual quality: from axonometric view, no visible piecewise-linear creases between adjacent stations (constitution principle III — FreeCAD-idiomatic includes "looks like a real boat").
- **SC-008**: AdditiveLoft's `Ruled` property is `False` in the generated FCStd. Verified by a unit test that introspects the feature.

## Assumptions

- **Reference fidelity from images only**: The implementation derives the new hull silhouette from (a) the textual specifications scraped from storebropassion.de (LOA, beam, draft, freeboards, hull-type classification) and (b) the side-profile illustration in `docs/references/Alternativ3.JPG`'s upper half. No formal lines drawing (body plan + sheer plan + half-breadth plan) is available. Visual fidelity is targeted at ≥80% of the reference but not 100% lines-drawing-perfect.
- **Einar Runius design heuristics**: where the textual reference is silent, the implementation uses standard Scandinavian-motoryacht-of-the-1970s design heuristics: rounded bilges (no hard chine), moderate-deadrise V-bottom (8° at amidships flattening fore and aft), near-plumb stem with slight forward rake.
- **No hard chine in v1.0.1**: the RC34 reference is ambiguous on whether the hull has a true hard chine or a rounded bilge. v1.0.1 implements rounded bilges (smoother is safer for B-spline loft). Hard-chine variant deferred to v1.1+ if a primary source confirms it.
- **Semi-displacement classification = moderate deadrise**: 8° at amidships is mid-range for semi-displacement hulls (planing hulls run 18-22°, full-displacement ~3-5°). The exact value is a design judgment call; ±2° tolerance is acceptable.
- **The deck/interior/export/cli modules don't need to know**: spec 007 is internal to `hull.py`. The deck-module's `_sample_hull_sheer` already adapts to whatever sheer values come from `HullParameters`, so it auto-follows the new flatter sheer.
- **Hash baselines reset is part of this spec**: just like spec 006 did. `tests/geometry/fixtures/expected_hashes.toml` re-seeds in polish phase.
- **PATCH-level semver**: no breaking public API change (FR-006/007/008), only internal hull shape and one new optional parameter (`stem_rake_angle` with default). Bumps v1.0.0 → v1.0.1.
- **Visual signoff is mandatory**: per constitution principle V, the PR description must include "Visually verified in FreeCAD: 1.1.x on \<OS\> — silhouette matches Alternativ3.JPG reference within tolerance".
- **Failure path for self-intersecting loft**: if `Ruled=False` still produces a degenerate loft for the default parameters, the implementation MAY temporarily fall back to `Ruled=True`, with a runtime warning. This is an escape hatch, NOT the goal.
- **No primary lines drawing exists in the repo**: the reference is only the secondary-source side profile. A future spec (008+) may reconstruct the hull from a primary lines drawing if one is acquired (museum / model-builder archive).
