# Feature Specification: Hull surface smoothness

**Feature Branch**: `master` (solo direct-push; see `.claude/rules/spec-register.md`)

**Created**: 2026-05-28

**Status**: Draft

**Input**: User description: "009 — hull-surface-smoothness — Bump hull station count from 5 to ≥8 so PartDesign::AdditiveLoft Ruled=False (B-spline) converges without overshoot. Unblock three deferred Allium markers from spec 007: Hull.b_spline_loft (smooth B-spline loft instead of Ruled=True piecewise-linear), Hull.bilge_arc (quarter-circle bilge transition between bottom and topside), and Hull.stem_with_zero_forefoot (drop the 80mm virtual forefoot half-beam now that mixed topology is no longer required by 1:1 vertex mapping across a denser station set). Goal: faceted between-stations look disappears; hull silhouette reads as a smooth-curved RC34 1972 reference profile both in side view and at amidships cross-section. Constraint: must remain PartDesign-idiomatic (constitution principle III), reproducible (principle II), and parametric (principle I — station count is a named parameter with a default). Must preserve spec 008's deck/pillar seating contract (pillars seat on actual deck plate top Z; do not regress the Z-resolution helper). FreeCAD 1.1+ on Ubuntu + macOS × Python 3.11 + 3.12 CI matrix. v1.0.3 PATCH release (additive parameter, no public API break)."

## Implementation drift (post-implementation amendment, 2026-05-28)

During implementation in FreeCAD 1.1.1, three premises of the original spec
were found to be empirically incorrect. The spec is amended below to reflect
the shipped v1.0.3 behavior; the original aspirations are tracked as `v1.1+`
deferred items in `spec.allium`.

1. **B-spline loft is deferred to v1.1+.** FR-006/FR-007 originally required
   `Ruled=False` at `station_count >= 8`. Empirical testing revealed
   FreeCAD's AdditiveLoft B-spline interpolation is fundamentally unstable
   for the Storebro hull profile — overshoots ranged from 22 mm to 1900 mm
   depending on station count, with intermittent degenerate (zero-volume)
   shapes at counts 13 and 21. The v1.0.3 implementation uses `Ruled=True`
   (piecewise-linear) at every station count. Visual smoothness still
   improves over v1.0.2 because the default station count rose from 5 to 9.
   `uses_b_spline_loft` always reports `False` in v1.0.3.
2. **Quarter-circle bilge arc is deferred to v1.1+.** FR-008 required a
   tangent-continuous quarter-circle bilge arc on every non-stem station
   sketch. FreeCAD's Sketcher.fillet() does produce the arc correctly, but
   the denser-station + arc combination produces tessellated meshes with
   non-manifold edges and self-intersections that break the STL export
   pipeline. The v1.0.3 implementation skips the fillet entirely; non-stem
   stations retain the spec 007 sharp-chine pentagon. `uses_bilge_arc`
   always reports `False`.
3. **Zero-forefoot stem is a thin pentagon, not a degenerate vertex.**
   FR-009 required a true `DEGENERATE_VERTEX` (single point) stem at
   `station_count >= 8`. The AdditiveLoft surface morphing from a 5-vertex
   pentagon to a 1-vertex section produces wildly-curving "blend to point"
   geometry — the dominant overshoot mode in finding 1. The v1.0.3
   implementation uses `PENTAGON_THIN_STEM` — a 5-vertex pentagon with
   `THIN_STEM_HALF_WIDTH_M = 0.005` (5 mm half-width = 10 mm stem face).
   Below visual resolution at boat scale; preserves topology consistency.

What v1.0.3 DOES ship:
- Default `station_count = 9` (vs 5 in spec 007).
- Default `bilge_radius = 0.10 m` (parameter accepted, currently ignored
  by the build but reserved for v1.1+).
- `PENTAGON_THIN_STEM` topology for the stem when `station_count >= 8`.
- Smoother keel-depth anchor profile (less abrupt forefoot drop than spec
  007, giving the silhouette a more faithful RC34 1972 look).
- Module-level constants for all magic numbers (Constitution I).
- Backward-compat construction (existing v1.0.2 call sites work unchanged).
- New `station_count` and `bilge_radius` parameter fields with validated
  ranges.
- `StationTopology` enum exposed in `__all__`.
- 553 tests green (was 485 at spec 008 closure; 67 spec 009 additions
  plus 1 xfail for cumulative FCStd determinism flakiness).

## Clarifications

### Session 2026-05-28

- Q: When the B-spline loft (`Ruled=False`) overshoots the explicit hull height — Shape bounding box Z exceeds `parameters.draft + sheer_at_X(X)` at some X-station — should the build silently fall back to `Ruled=True` (graceful degradation) or raise a descriptive `ValueError` (fail-fast)? → A: Raise a descriptive `ValueError` quoting the offending overshoot magnitude, the X-station where it was detected, and a remediation hint (increase `station_count`, reduce `bilge_radius`, or set `station_count < 8` for legacy piecewise-linear behavior). Rationale: CLAUDE.md fail-fast principle; silent fallback would mask geometry pathologies and produce output that does not match the requested loft type.
- Q: Does `station_count` refer to the number of stations on the half-hull (before mirroring) or the whole hull (after mirroring)? → A: Half-hull, evenly spaced along LOA from stem (X=0) to transom (X=LOA), inclusive of both endpoints. The `PartDesign::Mirrored` feature produces the port side from the starboard half. Rationale: matches the convention established by specs 006 and 007 (five datum planes for the half-hull); counting on the half is the natural unit for `PartDesign::AdditiveLoft`.
- Q: Should the new fields (`station_count`, `bilge_radius`) be exposed as optional CLI flags in v1.0.3, or only via direct `HullParameters` instantiation? → A: Only via `HullParameters` for v1.0.3 — no new CLI flags. Defaults are tuned for visual fidelity to the RC34 reference; the parameters are "advanced" knobs not expected to be tweaked per-build. Rationale: YAGNI principle from CLAUDE.md; adding CLI flags now means additional argparse plumbing, validation duplication, and CLI test coverage with no current consumer. Revisit in v1.1 if user demand emerges.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Smooth-curved hull surface across stations (Priority: P1)

A FreeCAD scripter who renders the generated `.FCStd` in the GUI (or opens a STEP export in another CAD package) sees a smooth-curved hull surface that reads as a real boat hull, not a piecewise-linear approximation that visibly facets between the five stations of the v1.0.2 hull. The bow-to-stern silhouette tracks the RC34 1972 reference (`docs/references/Alternativ3.JPG`) without visible polygon edges between stations, and the amidships cross-section presents as a continuous curve rather than a pentagon.

**Why this priority**: This is the headline visual deliverable. The faceted between-stations look is the single most-noticed remaining defect after spec 007 refreshed the silhouette and spec 008 refreshed the superstructure. Without it, no other refinement (windows, hardware, paint) will make the hull look real. It is also the precondition for spec 011's window cutouts (boolean cuts against a faceted surface produce visible polygon artifacts).

**Independent Test**: Build the hull with default parameters, open the `.FCStd` in FreeCAD 1.1.1 GUI, and inspect the hull surface in side view and amidships cross-section. The surface MUST present as a smooth B-spline curve with no visible polygon edges between stations and no Z-axis overshoot above the sheer line or below the keel between stations. The same scripter, using only the public CLI (`storebro build`) and visual inspection, can confirm the deliverable end-to-end.

**Acceptance Scenarios**:

1. **Given** the default `HullParameters` (which now uses the new station_count default of 9), **When** the user runs `storebro build --layout 3 --out boat.FCStd` and opens `boat.FCStd` in FreeCAD 1.1.1, **Then** the HullBody.Shape presents as a smooth-curved B-spline loft with no visible polygon facets in side view between any pair of adjacent stations.
2. **Given** the same default hull, **When** the user takes a cross-section at amidships (LOA/2) in FreeCAD, **Then** the cross-section reads as a smooth curve transitioning continuously from keel through bilge arc to topside to sheer (no sharp corner between bottom and topside).
3. **Given** the default hull, **When** the user inspects the stem (forward-most station) in cross-section, **Then** the stem has zero forefoot (no 80mm half-beam offset at top or bottom) and reads as the blunt-but-thin vertical bow of the RC34 reference.
4. **Given** a `PartDesign::AdditiveLoft` feature with `Ruled=False`, **When** FreeCAD recomputes the Body, **Then** the loft converges without recompute errors, without self-intersections, and without producing a `Shape.isClosed() == False` result.

---

### User Story 2 - Backward-compatible additive parameter (Priority: P2)

A library consumer who has working code calling the v1.0.2 hull API can upgrade to v1.0.3 by bumping the dependency version. Their existing call sites (which construct `HullParameters` without the new `station_count` field) continue to work without source changes, and the resulting `.FCStd` reflects the new smooth-curved hull as the new default behavior. No existing public function signature, class init signature, or required field is removed or renamed.

**Why this priority**: PATCH releases must not break consumers. Spec 007 set this precedent (added `stem_rake_angle` as an additive field with a default), and spec 009 must follow it. Without backward compatibility, the smoothness work cannot ship as v1.0.3 and would force a v1.1.0 bump which is reserved for the larger v1.1 roadmap (specs 008–016 collectively).

**Independent Test**: Run the existing test suite (`uv run pytest`) against the new code with no test changes. Every existing test that constructs `HullParameters` without the new field MUST continue to pass. The output `.FCStd` from the same parameters may differ (it is expected to differ — the hull is smoother), but no public API surface change forces a test rewrite.

**Acceptance Scenarios**:

1. **Given** a test that constructs `HullParameters(loa=10.34, beam=3.13, draft=1.10, ...)` without specifying `station_count`, **When** the test runs against v1.0.3, **Then** the construction succeeds and `params.station_count` returns the new default (9).
2. **Given** all existing geometry tests (244 unit + 100 baseline geometry from spec 008's count), **When** the test suite runs against v1.0.3, **Then** every test passes except for tests that assert specific vertex counts, station counts, or `Ruled` flag values on the hull loft (these MUST be updated as part of this spec to reflect the new defaults).
3. **Given** the CLI invocation `storebro build --layout 3 --out boat.FCStd` with no new flags, **When** v1.0.3 runs, **Then** the build succeeds and produces a valid `.FCStd` reflecting the new smooth hull.

---

### User Story 3 - Quarter-circle bilge arc (Priority: P2)

A naval-architecture-aware viewer (the user is one) inspecting an amidships station cross-section sees a quarter-circle arc transitioning between the hull bottom and the topside, instead of the v1.0.2 sharp corner. The arc tangent is continuous at both endpoints (the bottom meets the arc tangentially, the arc meets the topside tangentially) so there is no visible chine on the rendered hull.

**Why this priority**: The bilge arc is one of the three deferred Allium markers from spec 007 and is a recognizable signature of the RC34 reference hull. It belongs in v1.0.3 alongside the B-spline loft because both require the denser station set to be implementable without overshoot — splitting them would force two PATCH releases with the same risk profile.

**Independent Test**: Build the hull, open in FreeCAD GUI, take an amidships cross-section, and visually verify the bottom-to-topside transition reads as a curved arc rather than a sharp corner. Programmatically, the arc's radius can be measured by sampling three points on the cross-section between the bottom and topside and computing the circumscribed circle's radius — it MUST match the `bilge_radius` parameter within ±1mm.

**Acceptance Scenarios**:

1. **Given** the default `HullParameters` (with the new `bilge_radius` default), **When** the user takes a cross-section at amidships, **Then** three sampled points on the transition between bottom and topside fit a circle whose radius matches `bilge_radius` within ±1mm.
2. **Given** `bilge_radius=0`, **When** the user builds the hull, **Then** the build succeeds and produces the legacy sharp-chine cross-section (escape hatch for users who prefer the chine).
3. **Given** `bilge_radius` larger than the bottom half-beam at amidships, **When** the user constructs `HullParameters`, **Then** the constructor raises `ValueError` citing the offending value and the maximum legal value.

---

### User Story 4 - Reproducible smooth-hull output (Priority: P2)

A CI pipeline (GitHub Actions on Ubuntu + macOS × Python 3.11 + 3.12) runs `storebro build` twice with identical parameters and obtains byte-identical STEP, STL, and BREP output. The within-document FCStd determinism preserved from spec 002 is not regressed by the new station count or loft type.

**Why this priority**: Constitution principle II is non-negotiable. A smooth hull that produces non-deterministic output breaks the reproducibility guarantee that distinguishes this library from one-off `.FCStd` snapshots. This must hold from v1.0.3 onward.

**Independent Test**: Run `storebro build` twice into different output paths, then `diff` the STEP files (and STL and BREP). They MUST be byte-identical. The FCStd files MUST be deterministic within-document per the spec 002 contract; cross-invocation FCStd byte determinism remains deferred per the v1.0.0 closure note.

**Acceptance Scenarios**:

1. **Given** identical `HullParameters` and CLI flags, **When** the user runs `storebro build` twice on the same machine, **Then** the two produced STEP files have identical SHA-256 hashes.
2. **Given** the same parameters on different OS/Python combinations in CI (Ubuntu + macOS × 3.11 + 3.12), **When** the build runs, **Then** the STEP file SHA-256 hash matches across the matrix (cross-platform determinism preserved).

---

### User Story 5 - No regression in deck/pillar seating contract (Priority: P3)

A user who builds a hull + deck + superstructure (the default `storebro build` flow) sees the hardtop pillars seat on the actual deck plate top Z, not pierce through the hull or float above the deck. The `_resolve_deck_top_z_at()` helper introduced in spec 008 continues to work against the new smooth-curved hull (the analytical sheer formula is NOT reintroduced as a shortcut).

**Why this priority**: Spec 008 closed this bug; spec 009 must not reopen it. A smoother hull means a slightly different sheer-line Z at any given X-station, and any caller that hardcodes the v1.0.2 analytical formula will drift. The deck module must continue to query the actual hull geometry via the resolver helper.

**Independent Test**: Build hull + deck + superstructure with default parameters, open in FreeCAD GUI, and visually verify all hardtop pillars meet the deck plate at the deck plate's top Z with no clipping into the hull and no gap above the deck. Programmatically, assert that for each pillar, `pillar.bottom_z == deck_plate.top_z_at(pillar.x_position)` within ±1mm.

**Acceptance Scenarios**:

1. **Given** default hull + deck + superstructure on v1.0.3, **When** the user inspects each hardtop pillar, **Then** the pillar base Z matches the deck plate top Z at the pillar's X-station within ±1mm.
2. **Given** the test in `tests/geometry/test_deck_pillar_seating.py` (from spec 008), **When** the suite runs against v1.0.3 hull, **Then** the test passes without modification.

---

### Edge Cases

- **Station count below B-spline convergence threshold**: A user explicitly sets `station_count=5` to recover legacy behavior. The build MUST succeed but MUST use `Ruled=True` (legacy piecewise-linear) automatically — Ruled=False with five stations is the known-broken configuration this spec exists to escape.
- **Station count too high**: A user sets `station_count=50`. The build SHOULD succeed but MAY take significantly longer; the validation MUST reject obviously absurd values (`station_count > 21`) with a clear `ValueError`.
- **Bilge radius zero**: Legacy sharp-chine behavior. Build succeeds. Bilge arc is collapsed to a single shared vertex between bottom and topside (one fewer station vertex, vertex count adjusted accordingly).
- **Bilge radius too large for beam**: A user sets `bilge_radius > beam/2` (geometrically impossible). Constructor raises `ValueError` citing the offending value and the maximum legal value computed from `beam`.
- **B-spline overshoots at stem**: Even with `station_count=9` and zero-forefoot stem, the B-spline may overshoot the stem profile if the rate of cross-section narrowing is too steep. The build MUST detect overshoot (Shape bounding box Z exceeds `parameters.draft + sheer_at_X(X)` at some X-station, with a tolerance of 1 mm) and raise a descriptive `ValueError` quoting the offending overshoot magnitude in mm, the X-station where it was detected, and a remediation hint ("increase `station_count`, reduce `bilge_radius`, or set `station_count < 8` for legacy piecewise-linear behavior"). Silent fallback to `Ruled=True` is forbidden — it would mask geometry pathologies.
- **Asymmetric station spacing**: All stations are currently evenly spaced along LOA. Non-uniform spacing (denser near stem and transom, sparser amidships) is out of scope for v1.0.3 — flagged for a future spec if needed.
- **FreeCAD version mismatch**: Loft behavior with `Ruled=False` may differ between FreeCAD 1.1.1 and earlier versions. The library declares FreeCAD 1.1+ as the supported runtime; behavior on older versions is undefined and not tested.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `HullParameters` MUST expose a new additive field `station_count: int` with a default value of `9`.
- **FR-002**: `HullParameters` MUST expose a new additive field `bilge_radius: float` (in meters) with a default value derived to be visually faithful to the RC34 reference (proposed: `0.20` m, ~6.4% of beam — falsifiable at visual signoff).
- **FR-003**: `HullParameters.__post_init__` (or equivalent validator) MUST reject `station_count < 3` and `station_count > 21` with a `ValueError` quoting the offending value and the valid range.
- **FR-004**: `HullParameters.__post_init__` MUST reject `bilge_radius < 0` and `bilge_radius > min(beam/2, draft)` with a `ValueError` quoting the offending value and the maximum legal value.
- **FR-005**: `build_hull(parameters)` MUST construct exactly `parameters.station_count` station sketches on the half-hull (and matching datum planes) as `PartDesign::Sketcher` features owned by the HullBody. The stations MUST be evenly spaced along LOA from stem (X=0) to transom (X=LOA), inclusive of both endpoints. The `PartDesign::Mirrored` feature produces the port side from the starboard half — `station_count` does not include the mirrored copies.
- **FR-006**: When `parameters.station_count >= 8`, `build_hull` MUST use `PartDesign::AdditiveLoft` with `Ruled=False` (B-spline interpolation across stations).
- **FR-007**: When `parameters.station_count < 8`, `build_hull` MUST use `PartDesign::AdditiveLoft` with `Ruled=True` (legacy piecewise-linear) to preserve known-working behavior at low station counts.
- **FR-008**: When `parameters.bilge_radius > 0`, each non-stem station sketch MUST include a quarter-circle arc with radius `bilge_radius` connecting the bottom edge (tangent at the bottom endpoint of the arc) to the topside edge (tangent at the topside endpoint of the arc). When `parameters.bilge_radius == 0`, the bottom and topside meet at a single shared vertex (legacy sharp chine).
- **FR-009**: When `parameters.station_count >= 8`, the stem (forward-most) station MUST have zero forefoot — top half-beam = 0 and bottom half-beam = 0 (a degenerate vertex). When `parameters.station_count < 8`, the stem MUST retain the spec 007 80mm-pentagon topology to preserve known-working behavior.
- **FR-010**: All existing fields of `HullParameters` (loa, beam, draft, deadrise, sheer_aft, sheer_fwd, transom_angle, stem_rake_angle) MUST remain present with their spec 007 defaults and validation ranges unchanged.
- **FR-011**: The HullBody MUST remain a valid `PartDesign::Body` container with editable feature stack (datum planes + sketches + AdditiveLoft + Mirrored), and `HullBody.Tip` MUST remain the mirrored feature.
- **FR-012**: Same input parameters MUST produce byte-identical STEP, STL, and BREP output across runs (constitution principle II — same as spec 002 contract).
- **FR-013**: Same input parameters MUST produce byte-identical STEP, STL, and BREP output across the CI matrix (Ubuntu + macOS × Python 3.11 + 3.12).
- **FR-014**: The `deck` module's `_resolve_deck_top_z_at()` helper MUST continue to query the actual hull geometry (not an analytical formula) — no regression in spec 008's pillar-seating contract.
- **FR-015**: The hull silhouette in side view MUST match the RC34 1972 reference (`docs/references/Alternativ3.JPG`) within ±1% on LOA, beam, draft, and sheer at the stem and transom (same fidelity bar as spec 007).
- **FR-016**: `HullParameters` MUST remain a `@dataclass(frozen=True)` (or equivalent immutable form) so existing call sites that compare or hash parameters continue to work.
- **FR-017**: The CLI invocation `storebro build --layout <N> --out <path>` MUST continue to accept the exact same flags as v1.0.2. The new `station_count` and `bilge_radius` parameters MUST NOT be exposed as CLI flags in v1.0.3; they are configured exclusively via direct `HullParameters` instantiation. (Decision deferred to v1.1+ pending user demand — see Clarifications.)
- **FR-018**: The full test suite (`uv run pytest`) MUST pass on FreeCAD 1.1+ × Python 3.11+ × Ubuntu + macOS with zero failures. `ruff check .` and `mypy --strict src/` MUST be clean.

### Key Entities

- **HullParameters** (extended): The frozen parameter dataclass driving hull construction. v1.0.3 adds two fields: `station_count: int = 9` and `bilge_radius: float = 0.20`. All existing fields preserved. Validation extended to enforce the new ranges. No removal, no rename.
- **HullBody** (behavior-changing): The `PartDesign::Body` produced by `build_hull`. Now contains `station_count` datum planes (instead of 5) and `station_count` sketches. The single `PartDesign::AdditiveLoft` feature now uses `Ruled=False` when `station_count >= 8`. The `PartDesign::Mirrored` feature continues to mirror to the port half. `HullBody.Tip` continues to point at the mirrored feature.
- **Station sketch** (behavior-changing): Each station's `PartDesign::Sketcher` now contains either a sharp-chine quadrilateral (when `bilge_radius == 0`) or a pentagon-with-quarter-circle-arc (when `bilge_radius > 0`) for non-stem stations. The stem station is either degenerate (single vertex, when `station_count >= 8`) or the spec 007 80mm-pentagon (when `station_count < 8`).
- **Bilge arc** (new, conditional): A quarter-circle of radius `bilge_radius` embedded in each non-stem station sketch, tangent to the bottom edge at one endpoint and tangent to the topside edge at the other endpoint. Absent when `bilge_radius == 0`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A naval-architecture-aware viewer, inspecting the default-parameter hull's side-view silhouette in FreeCAD GUI, judges it as "smooth-curved" with no visible polygon facets between adjacent stations (qualitative pass/fail at visual signoff).
- **SC-002**: A cross-section taken at amidships (LOA/2) on the default-parameter hull, when sampled at three points on the transition between bottom and topside, fits a circle whose radius matches `bilge_radius` within ±1 mm.
- **SC-003**: The `PartDesign::AdditiveLoft` feature with `Ruled=False` on the default-parameter hull recomputes without errors and produces a closed Shape (`Shape.isClosed() == True` and `Shape.Volume > 0`).
- **SC-004**: All existing tests from spec 008's closure baseline (485 tests: 244 baseline unit + 99 spec 008 unit + 100 baseline geometry + 41 spec 008 geometry + 1 xfailed unchanged) continue to pass against v1.0.3, modulo tests that explicitly assert spec-008-era vertex counts or `Ruled=True` — those tests are updated as part of spec 009 and the updated count is documented in the spec 009 closure note.
- **SC-005**: Pillar bases continue to seat on the actual deck plate top Z within ±1 mm at every X-station, against the new hull (spec 008 deck/pillar contract preserved).
- **SC-006**: Identical input parameters produce STEP, STL, and BREP files with identical SHA-256 hashes across two consecutive runs on the same machine, and across the four CI matrix combinations (Ubuntu + macOS × Python 3.11 + 3.12).
- **SC-007**: Hull silhouette principal dimensions (LOA, beam, draft, sheer at stem, sheer at transom) match the RC34 1972 reference within ±1% (constitution principle IV).
- **SC-008**: `HullParameters` constructed with no `station_count` or `bilge_radius` argument succeeds and exposes the new defaults — zero source-level changes required at existing call sites for backward compatibility.
- **SC-009**: `ruff check .` and `mypy --strict src/` complete with zero issues on the v1.0.3 codebase.
- **SC-010**: Build time for `storebro build --layout 3` on a baseline developer laptop (Apple M-series or equivalent) remains under 10 seconds for the hull module specifically (geometry-construction time, excluding FreeCAD startup and FCStd serialization).

## Assumptions

- **Default station count = 9**: Odd, symmetric around amidships, comfortably above the requested ≥8 floor. Chosen to give one station per LOA/8 segment plus an extra at the geometric centre, with an additional station near the stem and transom each implicitly via the existing endpoint stations. Falsifiable at visual signoff if 9 still produces visible facets in the cross-section.
- **Default bilge radius = 0.20 m**: Roughly 6.4% of beam (3.13 m default), visually faithful to the RC34 reference's moderate bilge. Falsifiable at visual signoff against `docs/references/Alternativ3.JPG`.
- **Station spacing remains uniform along LOA**: Non-uniform spacing (denser near endpoints) is out of scope. If smoothness in the bow/stern transitions remains unsatisfactory after spec 009 ships, a future spec may introduce non-uniform spacing or a `station_distribution` enum.
- **Legacy 5-station behavior preserved at station_count < 8**: Users who explicitly set `station_count=5` recover the v1.0.2 behavior (pentagon stem with 80mm forefoot, `Ruled=True` loft). This is an escape hatch, not the default.
- **v1.0.3 PATCH bump is correct**: New fields are additive with defaults; no removal, no rename, no required-field promotion. Existing call sites compile and run without source changes. The output `.FCStd` is intentionally different (smoother hull is the headline deliverable) — that is a behavior change, not an API break.
- **Cross-platform STEP/STL/BREP determinism continues to hold**: spec 002's deterministic writers are reused unchanged. The new geometry (more stations, different loft type, bilge arcs) MUST flow through the existing writers without bypassing their normalization.
- **B-spline convergence threshold at 8 stations is empirically sound**: The v1.0.2 closure note explicitly cited 5 stations as the broken configuration with `Ruled=False`. Spec 009 sets the threshold at 8 (with a default of 9). If 8 turns out to be insufficient at visual signoff, the default and validation range are bumped — spec 009 documents the floor as a parameter, not a hard-coded constant.
- **`docs/references/Alternativ3.JPG` remains the canonical reference** for hull silhouette and cross-section fidelity, as established by specs 007 and 008.
- **Spec 008 deck pillar resolver helper is API-stable**: `_resolve_deck_top_z_at(deck_plate, x)` continues to exist with the same signature. Spec 009 does not refactor it. Pillar seating remains its responsibility.
- **FreeCAD 1.1+ supports `PartDesign::AdditiveLoft` Ruled=False reliably**: Empirically true on FreeCAD 1.1.1; older versions are not in the supported matrix.
