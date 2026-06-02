# Feature Specification: Hull Surface Curvature v2 (dense Ruled=True smooth hull)

**Feature Branch**: `018-hull-surface-curvature-v2`

**Created**: 2026-06-02

**Status**: Draft

**Input**: Re-scoped roadmap item. Original premise (B-spline `Ruled=False` loft) was empirically falsified by a FreeCAD spike (≥12% beam overshoot vs the ±1% bar across four station-spacing strategies; raw `Part.BSplineSurface` would violate constitution III). New scope: make the hull read as smooth by densifying the `Ruled=True` loft, and re-land the quarter-circle bilge arc gated on a manifold check.

## Context

The hull is lofted with `PartDesign::AdditiveLoft Ruled=True` (piecewise-linear between station cross-sections). At the current default of 9 stations the surface is visibly faceted lengthwise, and the cross-section is a sharp-chined pentagon. Two long-standing deferrals (specs 007/009) aimed to fix this with a `Ruled=False` B-spline loft plus a quarter-circle bilge arc; both were deferred because the B-spline overshoots wildly and the bilge fillet broke STL at high density.

A pre-spec spike (`/tmp/spike_018.py`, recorded in the register history) confirmed the B-spline is permanently infeasible in FreeCAD 1.1.1 for this profile: `Ruled=False` overshoots the beam by 12–141% regardless of node placement, while `Ruled=True` is exact (0% overshoot). So smoothness here comes from **station density**, not interpolation: a `Ruled=True` loft with enough stations has facets below visual resolution and reads smooth, while staying exact, manifold, and GUI-editable. The quarter-circle bilge arc is re-attempted at the new density and kept only if it survives the manifold/STL gate.

## Clarifications

### Session 2026-06-02

- Q: B-spline (`Ruled=False`) vs dense `Ruled=True` for the smooth hull? → A: Dense `Ruled=True` (spike-confirmed exact + manifold; B-spline overshoots ≥12%). True B-spline is recorded as permanently infeasible in FreeCAD 1.1.1 for this profile and stays deferred.
- Q: How dense should the default and the cap be? → A: Raise `STATION_COUNT_MAX` from 21 to 81; bump `DEFAULT_STATION_COUNT` from 9 to 31 (smooth at viewing distance, sub-second build). `STATION_COUNT_MIN` stays 3.
- Q: What about the quarter-circle bilge arc (deferred since 007/009)? → A: Re-attempt it at the new default density; keep it only if the lofted hull stays a single manifold solid AND STL export succeeds. If it produces a non-manifold/broken mesh, fall back to the sharp-chine pentagon (the v1.0.3 behavior) and re-defer, surfacing the result as a finding. The default `bilge_radius` stays 0.10 m.
- Q: Does the denser default change the public output for existing callers? → A: Yes — the default hull gains stations (9 → 31), so its geometry (and exports) change. This is an intended fidelity improvement, a MINOR bump; the parametric envelope (LOA, beam, draft within ±1%) is preserved, and callers can pin `station_count=9` for the old shape.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A smooth-reading hull by default (Priority: P1)

A restorer or modeler builds the default hull and sees a smooth-sided Storebro, not a 9-facet wedge — without touching any parameter.

**Why this priority**: This is the feature. The faceted hull is the most-noted remaining geometry crudeness.

**Independent Test**: Build the default hull; confirm it has the denser station set (31), is a single manifold solid (`Solids == 1`, `isValid()`), and its LOA/beam/draft stay within ±1% of the parameters.

**Acceptance Scenarios**:

1. **Given** default parameters, **When** the hull is built, **Then** it uses 31 stations, `Ruled=True`, is a single valid manifold solid, and exports to STL without error.
2. **Given** the default hull, **When** its bounding box is measured, **Then** beam and draft match the parameters within ±1% (no overshoot — the `Ruled=True` exactness the spike confirmed).
3. **Given** a caller that pins `station_count=9`, **When** the hull is built, **Then** it reproduces the pre-feature 9-station shape (back-compat escape hatch).

---

### User Story 2 - Tunable station density up to a higher cap (Priority: P2)

An advanced user dials `station_count` higher (up to 81) for an even smoother surface, or lower for speed, within the validated range.

**Why this priority**: Parametric control (constitution I); the higher cap is what makes "smooth" reachable. Lower than P1 because the default already delivers the headline win.

**Independent Test**: Build at `station_count` = 3, 31, 81; each builds as a single manifold solid; 81 is smoother (more faces) than 31 than 9.

**Acceptance Scenarios**:

1. **Given** `station_count=81`, **When** the hull is built, **Then** it is a single manifold solid and its lengthwise face count exceeds the 31-station hull's.
2. **Given** `station_count=82` (over cap) or `2` (under floor), **When** constructed, **Then** `HullParameterError` names `station_count` and the `[3, 81]` range.
3. **Given** any valid `station_count`, **When** the hull is built twice with identical inputs, **Then** the geometry is identical (reproducibility).

---

### User Story 3 - Rounded bilge if it stays manifold (Priority: P3)

The chine corner is rounded by a quarter-circle bilge arc when `bilge_radius > 0`, provided the result remains a watertight, STL-exportable solid; otherwise the hull keeps its sharp chine.

**Why this priority**: The bilge arc softens the cross-section, but it has twice broken STL. Gating it behind a manifold check delivers it safely or not at all — never a broken mesh. Lowest priority because the longitudinal smoothness (US1) is the dominant visual win.

**Independent Test**: Build with `bilge_radius=0.10` at the default density; if the result is manifold and STL-exportable, the chine is rounded; if not, it falls back to the sharp pentagon and the build still succeeds.

**Acceptance Scenarios**:

1. **Given** `bilge_radius=0.10` and the bilge arc holds manifold, **When** the hull is built, **Then** the chine cross-section shows a rounded arc and STL export succeeds.
2. **Given** the bilge arc would break the manifold/STL, **When** the hull is built, **Then** it falls back to the sharp chine, still builds as a single solid, and exports STL (no broken mesh ever ships).
3. **Given** `bilge_radius=0`, **When** the hull is built, **Then** the chine is the sharp pentagon (unchanged).

---

### Edge Cases

- `station_count` at the floor (3) and cap (81): both build manifold; the floor reproduces a coarse 3-station wedge, the cap a fine surface.
- `bilge_radius` at its geometric max (`max_bilge_radius`): the arc is capped per-station to fit; never crosses the centerline or self-intersects.
- Reproducibility under the denser default: identical inputs → byte-identical exports (no station-ordering nondeterminism).
- Build time at `station_count=81`: must stay human-scale (seconds), not minutes.
- The stem station stays the thin 5 mm pentagon at all densities (the degenerate-vertex overshoot mode the spike re-confirmed for any blend toward a point).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The hull MUST loft with `PartDesign::AdditiveLoft Ruled=True` at every station count; the `Ruled=False` B-spline path MUST NOT be used (spike-confirmed overshoot ≥12% vs the ±1% bar).
- **FR-002**: `STATION_COUNT_MAX` MUST rise from 21 to 81; `STATION_COUNT_MIN` stays 3. `station_count` outside `[3, 81]` MUST raise `HullParameterError` naming the field and range.
- **FR-003**: `DEFAULT_STATION_COUNT` MUST rise from 9 to 31 so the default hull reads smooth.
- **FR-004**: For any valid `station_count`, the lofted-and-mirrored hull MUST be a single manifold solid (`Solids == 1`, `Shape.isValid()`) and MUST export to STL without error.
- **FR-005**: The hull bounding box MUST match the parametric envelope (LOA, beam, draft) within ±1% at every station count — i.e., no overshoot (the `Ruled=True` exactness property).
- **FR-006**: When `bilge_radius > 0`, the build MUST attempt the quarter-circle bilge arc cross-section and MUST verify the resulting hull is a single manifold solid that exports to STL; if that verification fails, it MUST fall back to the sharp-chine pentagon and still produce a valid manifold hull (never a broken mesh).
- **FR-007**: When `bilge_radius == 0`, the cross-section MUST be the sharp-chine pentagon (unchanged behavior).
- **FR-008**: A caller MUST be able to reproduce the pre-feature 9-station hull by passing `station_count=9` (back-compat escape hatch).
- **FR-009**: Builds MUST be reproducible — identical inputs produce identical geometry and byte-identical STL/STEP/BREP, with no timestamps or station-ordering nondeterminism.
- **FR-010**: The build MUST stay human-scale (target: under a few seconds) at `station_count=81`.
- **FR-011**: The stem station MUST remain the thin 5 mm pentagon (`THIN_STEM_HALF_WIDTH_M`) at all densities; a true degenerate vertex MUST NOT be introduced (the overshoot-to-point mode).
- **FR-012**: Any FreeCAD-side failure during the build MUST roll back all added features and surface as the hull module's construction error, exactly as today.

### Key Entities *(include if feature involves data)*

- **Station set**: The ordered list of cross-section profiles along the LOA, now defaulting to 31 and tunable up to 81. Evenly spaced (uniform), each a pentagon (or pentagon-with-arc) half-section.
- **Bilge arc (conditional)**: A quarter-circle replacing the chine corner of a non-stem station when `bilge_radius > 0` and the manifold gate passes; otherwise absent (sharp chine).
- **Smoothness**: An emergent property of station density under `Ruled=True` — not a new parameter; more stations → finer facets → smoother read, with bounded (zero) overshoot.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The default hull builds with 31 stations as a single manifold solid and exports to STL without error.
- **SC-002**: At `station_count` ∈ {3, 9, 31, 81} the hull is a single manifold solid with beam/draft within ±1% of parameters (0% overshoot confirmed).
- **SC-003**: The 81-station hull has a strictly greater lengthwise face count than the 31-station hull, which exceeds the 9-station hull (measurable smoothness).
- **SC-004**: With `bilge_radius > 0`, the hull either shows a rounded chine and exports STL, or falls back to a sharp chine and exports STL — never a non-manifold/broken mesh.
- **SC-005**: Build time at `station_count=81` stays under 10 seconds on the reference host.
- **SC-006**: `station_count=9` reproduces the pre-feature geometry (back-compat), and all builds are byte-identical across repeated identical-input runs.

## Assumptions

- Smoothness is delivered by station density under `Ruled=True`, not by spline interpolation; true B-spline is permanently infeasible in FreeCAD 1.1.1 for this profile (spike evidence) and stays deferred.
- The denser default is an intended, faithful fidelity improvement (MINOR bump); callers needing the exact old shape pin `station_count=9`.
- The cross-section topology stays the 5-vertex pentagon (or pentagon-with-arc) the loft already maps 1:1 across stations; no new cross-section vertices that would break AdditiveLoft vertex correspondence.
- The bilge arc remains a best-effort, manifold-gated feature; if it cannot hold manifold at the new density it re-defers with the sharp-chine fallback, consistent with v1.0.3.
- No CLI flag changes are in scope (consistent with the spec 009 decision that `station_count`/`bilge_radius` are advanced `HullParameters` knobs, not CLI flags).
