---

description: "Implementation tasks for spec 009 — hull-surface-smoothness"
---

# Tasks: Hull surface smoothness (spec 009)

**Input**: Design documents from `specs/009-hull-surface-smoothness/`

**Prerequisites**: `plan.md` (✅), `spec.md` (✅), `spec.allium` (✅), `research.md` (✅), `data-model.md` (✅), `contracts/hull_parameters.md` (✅), `quickstart.md` (✅)

**Tests**: Tests are MANDATORY per Constitution V (Test-Gated Releases). Every PR — including spec 009 — must pass `pytest`, `ruff`, and `mypy --strict` before merge. Test tasks below are not optional.

**Organization**: Tasks are grouped by user story to enable independent implementation. User Story 1 (P1) is the MVP — smooth-curved hull surface; subsequent stories layer additional refinements on top.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

## Path Conventions

- Single project (flat-module-per-body-part). Source under `src/storebro/`, tests under `tests/unit/` and `tests/geometry/`. Signoff fixtures under `tests/fixtures/signoff/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new infrastructure required for spec 009 — the project tooling (uv, pytest, ruff, mypy, FreeCAD runtime) is already in place from earlier specs. This phase records the only setup-flavored item: module-level constants.

- [ ] T001 Add module-level constants `DEFAULT_STATION_COUNT = 9`, `DEFAULT_BILGE_RADIUS_M = 0.20`, `STATION_COUNT_MIN = 3`, `STATION_COUNT_MAX = 21`, `B_SPLINE_STATION_COUNT_THRESHOLD = 8`, `OVERSHOOT_TOLERANCE_MM = 1.0`, `REFERENCE_FIDELITY_TOLERANCE_PCT = 1.0`, `HULL_BUILD_TIME_BUDGET_SECONDS = 10.0` near the existing module-level constants in `src/storebro/hull.py` (above `class HullParameters`).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extend the parameter dataclass and the internal station-profile dataclass. All user stories depend on these data-model changes.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 Add fields `station_count: int = 9` and `bilge_radius: float = 0.20` to `HullParameters` (frozen dataclass) in `src/storebro/hull.py`. Preserve frozen-dataclass semantics. Update the per-class docstring with units and ranges.
- [ ] T003 [P] Add `@property` computed accessors `uses_b_spline_loft`, `uses_zero_forefoot_stem`, `uses_bilge_arc`, `max_bilge_radius` on `HullParameters` in `src/storebro/hull.py` (each one-liner returning the formula from `data-model.md` §1).
- [ ] T004 Extend `HullParameters.__post_init__` (or the validator block) in `src/storebro/hull.py` to enforce `STATION_COUNT_MIN <= station_count <= STATION_COUNT_MAX` and `0 <= bilge_radius <= max_bilge_radius`. Raise `HullParameterError(field, value, valid_range)` with the message format from `contracts/hull_parameters.md`.
- [ ] T005 [P] Add `StationTopology` enum (`DEGENERATE_VERTEX`, `SHARP_CHINE_QUADRILATERAL`, `PENTAGON_WITH_ARC`, `PENTAGON_80MM_FOREFOOT`) near the existing `_StationProfile` dataclass in `src/storebro/hull.py`. Match values from `data-model.md` §2.
- [ ] T006 Extend `_StationProfile` (internal dataclass) in `src/storebro/hull.py` with fields `topology: StationTopology`, `bilge_radius_m: float = 0.0`, `vertex_count: int` (the legacy `is_terminal` flag stays for migration but new code reads `topology`).

**Checkpoint**: Parameter contract and internal data model ready. User stories can begin.

---

## Phase 3: User Story 1 — Smooth-curved hull surface across stations (Priority: P1) 🎯 MVP

**Goal**: Build a hull with `station_count >= 8` and `Ruled=False` AdditiveLoft so the rendered hull surface reads as smooth-curved instead of faceted. This is the headline deliverable.

**Independent Test**: Run `uv run storebro build --layout 3 --out boat.FCStd` with default v1.0.3 parameters; open `boat.FCStd` in FreeCAD 1.1.1 GUI; confirm no visible polygon edges between adjacent stations in side view; confirm `body.Shape.isClosed() == True` and `body.Shape.Volume > 0` programmatically.

### Tests for User Story 1

- [ ] T007 [P] [US1] Write `tests/unit/test_hull_parameters_station_count.py` — assert `HullParameters()` exposes `station_count = 9` by default; assert `HullParameters(station_count=8)` succeeds; assert `HullParameters(station_count=2)` raises `HullParameterError` with field `"station_count"` and valid range string `"[3, 21]"`; assert `HullParameters(station_count=22)` raises similarly.
- [ ] T008 [P] [US1] Write `tests/unit/test_hull_parameters_derived_flags.py` — assert `uses_b_spline_loft` is `True` for `station_count = 8, 9, 21`; `False` for `station_count = 3, 5, 7`. Assert `uses_zero_forefoot_stem` mirrors `uses_b_spline_loft`. Assert all four computed properties are read-only (frozen dataclass).
- [ ] T009 [P] [US1] Write `tests/geometry/test_hull_b_spline_loft.py` (marker: `requires_freecad`) — build hull with default params; assert `body.Shape.isClosed() == True`; `body.Shape.Volume > 0`; locate the `PartDesign::AdditiveLoft` feature and assert `loft.Ruled is False`; assert the body has exactly 9 station sketches and 9 datum planes; assert `body.Tip` is the `PartDesign::Mirrored` feature.
- [ ] T010 [P] [US1] Write `tests/geometry/test_hull_zero_forefoot_stem.py` (marker: `requires_freecad`) — build hull with default params (station_count=9); locate the stem station sketch (lowest X-coordinate datum plane); assert it has exactly 1 vertex (degenerate). Build hull with `station_count=5`; assert stem sketch has 5 vertices (legacy pentagon-with-80mm-forefoot).
- [ ] T011 [P] [US1] Write `tests/geometry/test_hull_overshoot_detection.py` (marker: `requires_freecad`) — construct a pathological `HullParameters` that would produce overshoot (large `bilge_radius` + low `station_count` near threshold); assert `build_hull(params)` raises `HullConstructionError` whose message contains the X-station, the overshoot magnitude, and the remediation hint text. Use a known-bad combination from research R6.

### Implementation for User Story 1

- [ ] T012 [US1] In `src/storebro/hull.py`, replace the hard-coded 5-station list in `_compute_stations()` with a parametric loop over `range(parameters.station_count)`. Station X-positions are `i * loa / (n - 1)` for `i in 0..n-1` (half-hull, stem at X=0 not transom — verify against existing spec 007 convention; if existing code uses transom-at-0 / stem-at-LOA, preserve that orientation). For each station, set `_StationProfile.topology` per the table in `data-model.md` §2 (stem branches on `uses_zero_forefoot_stem`; non-stem branches on `uses_bilge_arc`). Set `vertex_count` from topology. Set `bilge_radius_m` to `parameters.bilge_radius * 1000` when `topology == PENTAGON_WITH_ARC`, else `0.0`. Update the existing half-beam interpolation formula to handle N stations (was hard-coded for 5).
- [ ] T013 [US1] In `src/storebro/hull.py`, update `_create_station_sketch()` to handle `StationTopology.DEGENERATE_VERTEX` (no closed-pentagon construction, just place a single point at the datum origin). Keep the existing pentagon construction for `PENTAGON_80MM_FOREFOOT` and `SHARP_CHINE_QUADRILATERAL`. Defer `PENTAGON_WITH_ARC` to T021 (User Story 3).
- [ ] T014 [US1] In `src/storebro/hull.py`, update `_apply_loft_and_mirror()` to branch on the loft mode: `loft.Ruled = not parameters.uses_b_spline_loft`. Pass `parameters` into the helper (signature change: `_apply_loft_and_mirror(body, sketches, parameters)`). Update the existing v1.1-deferred docstring to point at spec 009 closure. Update the caller in `build_hull()`.
- [ ] T015 [US1] Add `_detect_b_spline_overshoot(body, parameters)` helper in `src/storebro/hull.py`. For each station X-position, slice the loft Shape (`body.Shape.slice(FreeCAD.Vector(1, 0, 0), x_mm)`) and compare the resulting wire's bounding-box Z extent against `parameters.draft + sheer_at_X(x_mm) * 1000`. If any overshoot exceeds `OVERSHOOT_TOLERANCE_MM`, raise `HullConstructionError` with the message format from `contracts/hull_parameters.md`. Helper is a no-op when `not parameters.uses_b_spline_loft`.
- [ ] T016 [US1] In `src/storebro/hull.py`, call `_detect_b_spline_overshoot(body, parameters)` from `build_hull()` after `_apply_loft_and_mirror()` but before the document is finalized. The call is unconditional; the helper short-circuits when not in B-spline mode.

**Checkpoint at end of US1**: Default hull builds smooth-curved with B-spline loft. Overshoot is detected and raised. Legacy `station_count=5` still works via the escape hatch. Tests T007–T011 all green. This is a shippable MVP if any further stories slip.

---

## Phase 4: User Story 2 — Backward-compatible additive parameter (Priority: P2)

**Goal**: Existing v1.0.2 call sites continue to work without source changes. Existing tests (modulo those that pin to old vertex counts) continue to pass.

**Independent Test**: Run the full pre-existing test suite (`uv run pytest`) against the v1.0.3 codebase. Assert zero regressions in tests that do not specifically pin to vertex counts or loft `Ruled` values.

### Tests for User Story 2

- [ ] T017 [P] [US2] Write `tests/unit/test_hull_parameters_v102_compat.py` — assert `HullParameters(loa=10.34, beam=3.13, draft=1.10)` (only legacy fields) constructs successfully; assert the resulting instance has `station_count == 9` and `bilge_radius == 0.20`; assert that omitting the new fields does NOT raise.
- [ ] T018 [US2] Audit `tests/` for tests that pin to spec 008-era values (e.g., `loft.Ruled is True`, `assert station_sketches.count == 5`, `assert stem.vertex_count == 5`). For each such test, update the assertion to the v1.0.3 value with an inline comment `# spec 009: bumped from 5 to 9 stations, B-spline loft now default`. Inventory before editing: search for `Ruled` and `station_count` in `tests/` and list matching files in the task body of T018 (or split into T018a/b/c per file if more than 3 files match).

### Implementation for User Story 2

User Story 2 does not introduce new implementation tasks — backward compatibility is satisfied entirely by T002–T004 (additive fields with defaults). T018 is a test re-baseline task, not new implementation.

**Checkpoint at end of US2**: Full test suite green against v1.0.3 codebase. Old call sites unchanged. Legacy fields preserved.

---

## Phase 5: User Story 3 — Quarter-circle bilge arc (Priority: P2)

**Goal**: Non-stem station cross-sections include a quarter-circle arc between bottom and topside, tangent-continuous at both endpoints.

**Independent Test**: Build hull with default params; take amidships cross-section in FreeCAD; sample three points on the bottom-to-topside transition; assert circumscribed circle radius matches `bilge_radius` within ±1 mm.

### Tests for User Story 3

- [ ] T019 [P] [US3] Write `tests/unit/test_hull_parameters_bilge_radius.py` — assert default `HullParameters().bilge_radius == 0.20`; assert `HullParameters(bilge_radius=0.0)` succeeds; assert `HullParameters(bilge_radius=-0.01)` raises `HullParameterError`; assert `HullParameters(bilge_radius=5.0)` raises (exceeds `max_bilge_radius`); assert the message includes the maximum legal value.
- [ ] T020 [P] [US3] Write `tests/geometry/test_hull_bilge_arc.py` (marker: `requires_freecad`) — build hull with default params; for the amidships station sketch, locate the bilge arc element (`Part.ArcOfCircle`); assert its radius equals `parameters.bilge_radius * 1000` mm within `bilge_arc_radius_match_tolerance_mm`; assert there is a `Tangent` constraint between the arc and both adjacent line segments. Build hull with `bilge_radius=0.0`; assert no arc element exists in non-stem sketches (sharp-chine quadrilateral).

### Implementation for User Story 3

- [ ] T021 [US3] In `src/storebro/hull.py:_create_station_sketch()`, add the `PENTAGON_WITH_ARC` branch: construct the bottom and topside line segments as before, then insert a `Part.ArcOfCircle` between them whose radius is `profile.bilge_radius_m`. Add `Sketcher.Constraint("Tangent", arc_idx, bottom_line_idx)` and `Sketcher.Constraint("Tangent", arc_idx, topside_line_idx)`. Add `Sketcher.Constraint("Radius", arc_idx, profile.bilge_radius_m)` to lock the radius (parametric, editable in GUI). Sketch geometry order is deterministic (arc inserted at a fixed position in the sketch element list to preserve reproducibility — see research R9).

**Checkpoint at end of US3**: Bilge arc visible in amidships cross-section. Radius matches parameter. Sharp-chine escape hatch (`bilge_radius=0.0`) preserved.

---

## Phase 6: User Story 4 — Reproducible smooth-hull output (Priority: P2)

**Goal**: Same parameters produce byte-identical STEP, STL, and BREP across runs and across the CI matrix.

**Independent Test**: Run `storebro build` twice on the same machine; `shasum -a 256` both STEP files; assert hashes match. CI matrix verifies cross-platform.

### Tests for User Story 4

- [ ] T022 [P] [US4] Write `tests/geometry/test_hull_reproducibility_v103.py` (marker: `requires_freecad`) — build hull twice from identical `HullParameters()`; export STEP, STL, BREP for both; compute SHA-256 of each pair; assert hashes match for STEP, STL, and BREP. Test parametrized over `(default, station_count=12, bilge_radius=0.05, station_count=5)` to cover all four major code paths.

### Implementation for User Story 4

User Story 4 does not introduce new implementation tasks — determinism is inherited from spec 002 writers (research R9). T022 is verification, not implementation.

**Checkpoint at end of US4**: SHA-256 hashes match across runs. Will also pass on the CI matrix (verified in T031).

---

## Phase 7: User Story 5 — No regression in deck/pillar seating contract (Priority: P3)

**Goal**: The hull + deck + superstructure pipeline continues to work with the new smoother hull. Pillars seat on deck plate top Z within ±1 mm via the spec 008 resolver helper.

**Independent Test**: Build full hull + deck + superstructure (`Alternativ3`); for each pillar, assert `pillar.lower_endpoint_z_mm == deck_top_z_at(pillar.x) ± 1 mm`.

### Tests for User Story 5

- [ ] T023 [P] [US5] Write `tests/geometry/test_hull_pillar_seating_regression.py` (marker: `requires_freecad`) — build hull (default v1.0.3 params) + deck + superstructure; for every pillar in `bundle.pillars`, compute `deck_top_z = deck._resolve_deck_top_z_at(bundle.deck_plate, pillar.longitudinal_x_mm)`; assert `abs(pillar.lower_endpoint_z_mm - deck_top_z) <= PILLAR_SEATING_TOLERANCE_MM`. Cross-reference spec 008's existing `test_no_pillar_geometry_below_deck_plate_top` and confirm it still passes against the new hull.
- [ ] T024 [P] [US5] Re-baseline (if necessary) spec 008's `tests/geometry/test_deck_pillar_seating*.py` so its hard-coded Z-coordinate assertions reflect the smoother v1.0.3 hull's sheer line at the pillar X-stations. Identify affected files via grep on `deck_top_z` and `pillar.*_z`. If no spec 008 tests need re-baselining, document that in the task body.

### Implementation for User Story 5

User Story 5 does not introduce new implementation. The `deck._resolve_deck_top_z_at()` helper from spec 008 already queries actual hull geometry; the smoother hull is automatically reflected in the resolver's output. T023 + T024 are verification + re-baseline tasks.

**Checkpoint at end of US5**: All 5 user stories implemented and tested. Ready for polish + cross-cutting verification.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Reference-fidelity verification, visual signoff, type/lint hygiene, CI matrix verification, and the v1.0.3 tag prep.

- [ ] T025 [P] Write `tests/geometry/test_hull_silhouette_fidelity.py` (marker: `requires_freecad`) — build hull with default v1.0.3 params; measure principal dimensions (LOA, beam, draft, sheer at stem, sheer at transom) from `body.Shape`; assert each is within `REFERENCE_FIDELITY_TOLERANCE_PCT` (±1 %) of the RC34 1972 reference values from `docs/references/Alternativ3.JPG`. Reference values to be sourced from the spec 007 closure note (parameters were already aligned then).
- [ ] T026 [P] Update the `_apply_loft_and_mirror()` docstring in `src/storebro/hull.py` to remove the "Ruled=False deferred to v1.1+" comment block (L491–L498 area). Replace with a one-sentence note: "Ruled mode is parametric per spec 009: `Ruled=False` (B-spline) when `parameters.uses_b_spline_loft`, else `Ruled=True` (piecewise-linear)."
- [ ] T027 [P] Update the inline comments in `_compute_stations()` that reference "the 5 station profiles" or "spec 007 R2" to reflect spec 009's parametric station set. Preserve attribution comments referencing earlier specs (do not delete history). Add a one-line comment at the top of `_compute_stations()` pointing at spec 009 as the parametric refactor source.
- [ ] T028 Run `uv run pytest` from the repo root. All tests MUST pass (including all spec 009 new tests, all spec 008 regression tests, all spec 001–007 baseline tests). Iterate on failing tests until 100 % green. Document the post-spec-009 test count in the task body when complete (baseline before this spec: 485 tests).
- [ ] T029 Run `uv run ruff check .` and `uv run ruff format .` from the repo root. Fix any lint findings. Re-run until clean.
- [ ] T030 Run `uv run mypy src/` from the repo root. Fix any type errors. Pay particular attention to: the `StationTopology` enum's exhaustive matching, the `HullParameters` computed properties' return types (annotate `-> bool` and `-> float`), and the `_detect_b_spline_overshoot` helper's `Any` returns vs. `Optional` annotations. Re-run until clean.
- [ ] T031 Verify cross-platform reproducibility: push the branch (`master`, per the solo direct-push convention) and let the GitHub Actions CI matrix run. Confirm all 4 cells (Ubuntu + macOS × Python 3.11 + 3.12) green. Confirm the STEP file SHA-256 hash matches across cells (the existing reproducibility test from T022 should run on all 4 cells; cross-cell hash equality is implicit if each cell's test passes against a checked-in expected-hash fixture — if no such fixture exists, add one as part of T022 / T031 follow-up).
- [ ] T032 Build the signoff fixture: `uv run storebro build --layout 3 --out tests/fixtures/signoff/storebro_v1_0_3_signoff.FCStd`. Open in FreeCAD 1.1.1 on macOS Darwin arm64. Visually compare against `docs/references/Alternativ3.JPG`. Verify (per `quickstart.md` workflow): smooth-curved hull surface, quarter-circle bilge transition at amidships, blunt zero-forefoot stem, pillars seated cleanly on deck plate. Record the file's SHA-256 hash (via `shasum -a 256`) and the "Visually verified in FreeCAD 1.1.1 on macOS Darwin arm64" line for the spec-register closure note.
- [ ] T033 Update `pyproject.toml` version: bump from `v1.0.2` to `v1.0.3`. Update `CHANGELOG.md` with the v1.0.3 entry following keep-a-changelog format: new fields, new behavior, the three closed deferred markers from spec 007 (`Hull.b_spline_loft`, `Hull.bilge_arc`, `Hull.stem_with_zero_forefoot`), the new behavior (B-spline loft, bilge arc, zero-forefoot stem), and the three deferred markers carried forward to v1.1+ (non_uniform_station_spacing, cli_flags_for_station_count_and_bilge_radius, cross_invocation_fcstd_byte_determinism). Run the changelog text through the `humanizer` skill before finalizing.
- [ ] T034 [P] Write `tests/unit/test_cli_flags_v103.py` — assert that `storebro.cli` exposes the same argparse flag set as v1.0.2. Concretely: parse `--help` output (or directly inspect the `argparse.ArgumentParser` instance) and assert that `--layout`, `--out`, and any other v1.0.2 flags remain present; assert no flag named `--station-count` or `--bilge-radius` exists in v1.0.3 (per spec.md FR-017 + clarification 3). Hard-coded v1.0.2 baseline list lives in the test file as a frozen reference. (Covers spec analyze finding C1.)
- [ ] T035 [P] Extend `tests/geometry/test_hull_b_spline_loft.py` (T009) with an elapsed-time assertion: wrap the `build_hull(params)` call in `time.perf_counter()` and assert the geometry-construction wall-clock time is ≤ `HULL_BUILD_TIME_BUDGET_SECONDS` (10.0). Exclude FreeCAD startup and FCStd serialization from the measured interval. Also add `HULL_BUILD_TIME_BUDGET_SECONDS = 10.0` to the module-level constants from T001 if not already present. (Covers spec analyze finding C2 / spec.md SC-010.)

---

## Dependencies

### Phase-level dependencies

- Phase 1 (Setup) → Phase 2 (Foundational): T001 must complete before T002 (constants used by validation).
- Phase 2 (Foundational) → Phases 3–7 (User Stories): T002–T006 must complete before any [US*] task.
- Phases 3–7 are mostly parallel after Phase 2 completes — but T012 (US1 implementation of `_compute_stations`) is a hard dependency for T021 (US3 bilge arc) because the arc lives inside the station sketch that T012 emits.

### User-story dependency graph

```
Phase 2 (Foundational)
    │
    ├──► US1 (P1) — smooth-curved hull surface     ◄── MVP
    │       │
    │       └──► US3 (P2) — bilge arc              [reads US1's station-sketch dataflow]
    │
    ├──► US2 (P2) — backward compat                [independent — needs only Phase 2 fields]
    │
    ├──► US4 (P2) — reproducibility                [independent — verification only]
    │
    └──► US5 (P3) — pillar seating regression      [independent — verification only]
            │
            ▼
        Phase 8 (Polish): T025 (fidelity) [P] T026–T030 (docs+lint+types) → T031 (CI) → T032 (visual signoff) → T033 (version+changelog)
```

### Within-story dependencies

- US1: T007–T011 (tests) [P] amongst themselves; T012 → T013 → T014 → T015 → T016 (implementation, sequential because each modifies overlapping regions of `hull.py`).
- US3: T019–T020 (tests) [P]; T021 depends on T012 (US1 must emit the station-sketch dataflow with `PENTAGON_WITH_ARC` topology before T021 can populate the arc inside).
- US5: T023 [P] T024; no implementation dependency.

---

## Parallel execution examples

### After Phase 2 completes (T002–T006 done):

Run in parallel:
- T007 [P] [US1] unit tests for station_count validation
- T008 [P] [US1] unit tests for derived flags
- T017 [P] [US2] unit test for v1.0.2 compat construction
- T019 [P] [US3] unit tests for bilge_radius validation

These touch four different test files with no shared fixtures (parameter-validation tests, not geometry).

### During US1 implementation:

Run in parallel:
- T009 [P] [US1] geometry test: B-spline loft
- T010 [P] [US1] geometry test: zero-forefoot stem
- T011 [P] [US1] geometry test: overshoot detection
- T020 [P] [US3] geometry test: bilge arc

All four are independent `requires_freecad` test files. T021 (US3 implementation) must wait for T012 (US1 implementation of `_compute_stations`), but the US3 test (T020) can be written first against the expected behavior.

### In Phase 8 (Polish):

Run in parallel:
- T025 [P] silhouette fidelity test
- T026 [P] docstring update in `_apply_loft_and_mirror`
- T027 [P] comment updates in `_compute_stations`
- T029 [P] ruff check + format (after all source changes settled)

T028 (pytest) and T030 (mypy) must run last among the lint/type tasks because they consume the final state of the source tree.

---

## Implementation strategy

**MVP scope** = User Story 1 (T001–T016). At the US1 checkpoint the hull is smooth-curved, B-spline loft works, overshoot is fail-fast, and backward compat is preserved automatically by T002–T004's additive-with-defaults pattern. Everything past US1 is a refinement layered on top.

**Incremental delivery order** (each phase is independently shippable):

1. Setup + Foundational (T001–T006) — parameter contract ready.
2. US1 (T007–T016) — MVP shippable; hull is smooth-curved.
3. US2 (T017–T018) — full backward-compat test pass; existing tests re-baselined.
4. US3 (T019–T021) — bilge arc visible in cross-section.
5. US4 (T022) — reproducibility hashes match.
6. US5 (T023–T024) — deck pillar regression covered.
7. Polish (T025–T033) — fidelity test, docs, lint, types, CI, signoff, version, changelog.

Visual signoff (T032) is the last gate before tagging v1.0.3 — it is the only check that catches qualitative "smooth-curved" failures the test suite cannot encode (constitution principle V).

---

## Task counts

- **Phase 1 (Setup)**: 1 task (T001)
- **Phase 2 (Foundational)**: 5 tasks (T002–T006)
- **Phase 3 (US1)**: 10 tasks — 5 tests (T007–T011) + 5 implementation (T012–T016) — MVP
- **Phase 4 (US2)**: 2 tasks (T017–T018) — tests + re-baseline; no new implementation
- **Phase 5 (US3)**: 3 tasks (T019–T021) — 2 tests + 1 implementation
- **Phase 6 (US4)**: 1 task (T022) — test only; no new implementation
- **Phase 7 (US5)**: 2 tasks (T023–T024) — verification + spec 008 re-baseline
- **Phase 8 (Polish)**: 11 tasks (T025–T035) — includes T034 (CLI-flags smoke test, gap C1 from `/speckit.analyze`) and T035 (build-time budget assertion, gap C2 from `/speckit.analyze`).

**Total**: 35 tasks. Parallel opportunities: at least 16 tasks marked [P].

---

## Format validation

- [x] Every task has `- [ ]` checkbox.
- [x] Every task has a sequential `TXXX` ID.
- [x] Every user-story-phase task has a `[US{N}]` label.
- [x] Setup, Foundational, and Polish phase tasks have no story label.
- [x] Every task includes an exact file path (`src/storebro/hull.py`, `tests/unit/test_*.py`, `tests/geometry/test_*.py`, etc.).
- [x] `[P]` marker present only on tasks safe to parallelize.
