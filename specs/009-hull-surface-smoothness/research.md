# Research: Hull surface smoothness (spec 009)

Phase 0 output for `/plan`. Resolves implementation-direction questions raised by the spec / Allium baseline. No `NEEDS CLARIFICATION` markers were introduced during planning, so this file primarily documents the decisions behind the values chosen in `plan.md` and the parameter defaults declared in `spec.md`.

## R1: Default station count

**Decision**: `DEFAULT_STATION_COUNT = 9`

**Rationale**: The user-facing requirement is "≥ 8 to make the B-spline loft converge". Picking 9 (odd) places one station exactly at amidships (X = LOA/2), which the cross-section assertions in `tests/geometry/test_hull_silhouette_fidelity.py` use as a fixed reference. An even count would force the amidships assertion to interpolate between two stations, adding test complexity without geometry benefit. 9 is also comfortably above the 8-station empirical convergence floor that spec 007's closure note identified — leaves headroom for tighter cross-sections without immediately producing overshoot.

**Alternatives considered**:
- 8 (the minimum) — rejected: too close to the convergence floor; one bad parameter combination could push into overshoot.
- 11 (next odd above 9) — rejected: adds 2 extra sketches per build with no visible smoothness improvement at this LOA (10.34 m); reproducibility-hash-bytes also grow.
- Variable default tied to LOA — rejected: violates "named parameter with a default" principle; defaults are simpler to validate.

## R2: Default bilge radius

**Decision**: `DEFAULT_BILGE_RADIUS_M = 0.20` (200 mm, ~6.4 % of default beam 3.13 m)

**Rationale**: Visually faithful to `docs/references/Alternativ3.JPG` — the RC34 1972 reference shows a moderate bilge transition, neither hard-chine nor barrel-bottomed. 6.4 % of beam falls within the typical range for cruising motor yachts of this era (5–10 %). Falsifiable at visual signoff: if the rendered hull reads as either too sharp or too rounded against the reference photo, the default is bumped and tests re-baselined.

**Alternatives considered**:
- 0.0 (no bilge arc, sharp chine) — rejected as default: legacy behavior preserved as escape hatch but not the visual target.
- Derived from beam (e.g., `beam / 16`) — rejected for v1.0.3: adds implicit coupling that's harder to reason about; defer until a future spec proves the coupling is desired.
- 0.10 / 0.30 — rejected: 0.10 is too tight for the reference profile (reads as chine); 0.30 is too rounded (reads as barrel bottom).

## R3: B-spline convergence threshold

**Decision**: `B_SPLINE_STATION_COUNT_THRESHOLD = 8`

**Rationale**: spec 007's closure note explicitly states `Ruled=False` produces a self-intersecting loft with only 5 stations because the pentagon → vertex transition at the stem is too steep to interpolate without overshoot. Empirical floor for non-overshoot convergence is somewhere in the 6–8 range; setting the threshold at 8 gives a 1-station safety margin from the worst observed case (overshot at 7) and matches the user's stated requirement ("≥ 8").

**Alternatives considered**:
- 5 (always use B-spline) — rejected: known-broken at 5 stations.
- 12 (very conservative) — rejected: would force the default of 9 to fall back to `Ruled=True`, defeating the spec.
- Dynamic threshold based on LOA / beam ratio — rejected: over-engineering for v1.0.3.

## R4: Overshoot tolerance

**Decision**: `OVERSHOOT_TOLERANCE_MM = 1.0`

**Rationale**: Matches the constitution principle IV tolerance bar (±1 % of principal dimensions, which at LOA = 10.34 m is ±10.34 cm — far above 1 mm). 1 mm is below the resolution of any visual rendering and below the precision of the input parameters (floats with ~6 mm precision at most). Setting the tolerance tighter would flag noise; setting it looser would let actual overshoot slip through.

**Alternatives considered**:
- 0.0 (exact) — rejected: floating-point rounding noise produces false positives.
- 5 mm — rejected: lets visible overshoot through at the bilge transition.
- Tolerance relative to bbox size — rejected: over-engineering.

## R5: Bilge arc tangent constraints

**Decision**: Use Sketcher `Tangent` constraints between the arc and the two adjacent line segments (bottom edge, topside edge).

**Rationale**: FreeCAD's Sketcher supports `Sketcher.Constraint("Tangent", arc_idx, line_idx)` natively. This gives the parametric solver a hard constraint that the implementation does not have to enforce manually with vertex math. The constraint also propagates correctly if a downstream user edits the Sketch (constitution III requires GUI editability).

**Alternatives considered**:
- Compute arc endpoints + center analytically and place vertices without constraints — rejected: breaks GUI editability; if the user nudges a vertex, the arc no longer reads as tangent.
- Use `Coincident` constraints only — rejected: doesn't enforce tangency; arc could rotate freely around its endpoints.

## R6: Overshoot detection — where and how

**Decision**: Sample the post-loft Shape bounding box at each station's X position via `Shape.slice(Vector(1, 0, 0), station_x_mm)` and compare the resulting wire's bounding box Z extent against `parameters.draft + sheer_at_X(station_x_mm)`. Detection happens in `_detect_b_spline_overshoot()` invoked from `build_hull()` after `_apply_loft_and_mirror()` but before the document is finalized. Fail-fast via `HullConstructionError` (the existing exception class for hull build failures).

**Rationale**: Slicing the post-loft Shape gives the actual rendered cross-section, not the pre-loft station sketch profile. The bbox-Z comparison is O(N) per build (one slice per station) which is acceptable within the 10-s budget.

**Alternatives considered**:
- Sample mid-segment (between adjacent stations) — rejected: 2N slices per build, doubles cost.
- Use the AdditiveLoft Shape's overall bbox only — rejected: detects bow/stern overshoot but misses amidships-only overshoot.
- Skip detection (trust empirics) — rejected: violates fail-fast principle.

## R7: Backward compatibility strategy

**Decision**: Both new fields (`station_count`, `bilge_radius`) get defaults so existing `HullParameters(loa=..., beam=..., ...)` call sites compile and run unchanged. Existing tests that assert specific vertex counts, station counts, or `loft.Ruled` values are updated to the v1.0.3 behavior (new defaults). Tests that pin to the old behavior explicitly construct `HullParameters(..., station_count=5)` to opt into legacy mode.

**Rationale**: This is the same pattern spec 007 used when adding `stem_rake_angle` (additive field, new default). Worked then; works now. PATCH-bump-safe.

**Alternatives considered**:
- Keep old defaults (station_count=5, bilge_radius=0); require explicit opt-in for new behavior — rejected: nobody would use the new smoother default; spec's headline deliverable would not ship.
- Bump MAJOR version (v2.0.0) — rejected: no API surface removed; PATCH is the correct semver signal.

## R8: Pillar seating contract — how to verify no regression

**Decision**: Add `tests/geometry/test_hull_pillar_seating_regression.py` that exercises the full hull + deck + superstructure build pipeline (default `Alternativ3` layout) and asserts every `PillarBody.lower_endpoint_z_mm` is within ±1 mm of `deck_plate.top_z_at(pillar.x)` — using the spec 008 resolver helper unchanged. Re-baseline spec 008's existing pillar-seating tests against the new hull defaults so they assert against the smoother hull's sheer line, not the spec 008-era analytical formula.

**Rationale**: Spec 008's pillar bug came from drift between an analytical sheer formula and the actual hull geometry. Spec 009's smoother hull changes the actual sheer line at any X-station, so any test that pins to the old analytical value will break. The fix is to re-baseline against the resolver helper's output, which is exactly what spec 008's helper does. Result: the pillar seating contract holds verbatim, and the test signals when the resolver helper itself is regressed.

**Alternatives considered**:
- Pin pillar-seating tests to absolute Z values — rejected: would require re-baselining for every hull-profile change, including future v1.1+ refinements.
- Skip the regression test, trust the helper — rejected: the headline correctness bug from spec 008 is exactly the kind of silent drift that needs an executable assertion.

## R9: Reproducibility under denser stations

**Decision**: No new code path for determinism. Reuse the spec 002 STEP/STL/BREP writers verbatim. Test that two consecutive `build_hull(params)` calls produce STEP files with identical SHA-256 hashes. Test that the SHA-256 is also identical across the CI matrix cells (Ubuntu + macOS × Python 3.11 + 3.12).

**Rationale**: The writers are deterministic by construction (spec 002 R1 — no timestamps, no env-dependent paths, deterministic ordering). More stations means more topology elements but the order is index-driven and deterministic. New helpers (`_detect_b_spline_overshoot`) are read-only and don't mutate the Shape.

**Alternatives considered**:
- Add new determinism scrubs for the bilge arc — rejected: the Sketcher arc lives inside the existing station sketch, which is already covered by spec 002's scrubs.

## R10: Visual signoff workflow

**Decision**: Generate `tests/fixtures/signoff/storebro_v1_0_3_signoff.FCStd` from `Alternativ3` default parameters, open in FreeCAD 1.1.1 GUI on macOS Darwin arm64, eyeball the hull silhouette against `docs/references/Alternativ3.JPG`, record the SHA-256 in the PR description (or this project's case, the spec-009 closure note in `specs/INDEX.md`), and the visual-verified-by line.

**Rationale**: Matches the spec 007 and spec 008 signoff pattern. Visual signoff is the only check that catches "smooth-curved" qualitative failures the test suite cannot encode.

## Resolved NEEDS CLARIFICATION markers

None — Phase 0 introduced no `NEEDS CLARIFICATION` markers because all three potential ambiguities were caught in `/clarify` and resolved with auto-picked recommendations. See `spec.md → ## Clarifications → Session 2026-05-28`.

## Open follow-ups for v1.1+

These are explicit `deferred` markers in `spec.allium` and are tracked in `specs/INDEX.md` for future work:

- `HullBody.non_uniform_station_spacing` — denser stations near bow/stern, sparser amidships. Defer until visual signoff proves uniform spacing is insufficient at LOA = 10.34 m.
- `HullModuleApi.cli_flags_for_station_count_and_bilge_radius` — exposed via `HullParameters` only in v1.0.3 per clarification 3. Revisit if user demand emerges.
- `HullBody.cross_invocation_fcstd_byte_determinism` — inherited from v1.0.0 tag closure note. STEP/STL/BREP cross-invocation determinism preserved; FCStd cross-invocation defers.

All three are intentional scope exclusions, surfaced and decided per `.claude/rules/validation-followup.md` during the `/allium:elicit` step.
