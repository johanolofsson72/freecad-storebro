---
description: "Task list for the hull fidelity refresh (spec 007)"
---

# Tasks: Hull Fidelity Refresh

**Input**: Design documents from `/specs/007-hull-fidelity-refresh/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/python-api-preserved.md](./contracts/python-api-preserved.md), [quickstart.md](./quickstart.md), [spec.allium](./spec.allium)

**Tests**: REQUIRED per constitution V. The 96 currently-passing geometry tests must continue to pass on the new shape (with hash baseline refresh). Three new tests added: B-spline loft assertion, silhouette dimensions, optional stem_rake parameter validation.

**Critical context**: PATCH-level shape refresh (v1.0.0 → v1.0.1). Public API frozen except for one additive `HullParameters.stem_rake_angle` field with default. Implementation is tight: 1 source file (`src/storebro/hull.py`), ~80 LOC net new across 4 modified + 2 added private functions.

## Format: `[ID] [P?] [Story?] Description with file path`

## Path Conventions

Single Python project, src-layout (continues from specs 001-006):
- Library source: `src/storebro/hull.py` (only file modified)
- Tests: `tests/unit/` + `tests/geometry/` (3 new geometry tests)
- Hash baselines: `tests/geometry/fixtures/expected_hashes.toml` (regenerated)

---

## Phase 1: Setup

- [ ] T001 Confirm FreeCAD detection on host: `PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib uv run storebro info` reports `FreeCAD detected: 1.1.x`. Bail with a clear error if not (the rest of the spec needs FreeCAD to verify visually).
- [ ] T002 Snapshot the current v1.0.0-shaped hull's bounding box for reference: `PYTHONPATH=... uv run python -c "import FreeCAD; from storebro import build_hull; h = build_hull(); bb = h.body.Shape.BoundBox; print(f'before: X={bb.XLength:.0f} Y={bb.YLength:.0f} Z={bb.ZLength:.0f}')" | tee /tmp/spec007_before.log`. Expected baseline: X≈10350mm, Y≈3200mm, Z≈2250mm. After implementation, X/Y unchanged; **Z stays roughly the same** (v1.0.1 = 1.10m draft + 1.16m sheer_fwd ≈ 2260mm) — the bounding box doesn't tell the story. What changes visually is the **sheer differential** (sheer_fwd − sheer_aft drops from 0.45m to 0.21m, meaning the deck line is much flatter) plus the bow/transom rake angles. Z-range stays nearly identical because the draft increase (0.95 → 1.10) and the sheer_fwd decrease (1.30 → 1.16) roughly cancel.

---

## Phase 2: Foundational

These tasks modify `src/storebro/hull.py`. Sequential (same file).

- [ ] T003 In `src/storebro/hull.py`, update `HullParameters` defaults per FR-001: `draft = 1.10`, `sheer_height_aft = 0.95`, `sheer_height_fwd = 1.16`, `deadrise_amidships = 8.0`, `transom_angle = 5.0`. Add new field `stem_rake_angle: float = 6.0` (additive, with default). Update `REFERENCE_STOREBRO_ROYAL_CRUISER_34_1972` ClassVar to mirror.
- [ ] T004 In `src/storebro/hull.py`, update `_validate_hull_parameters` to add a range check for `stem_rake_angle`: `if not (0.0 <= p.stem_rake_angle <= 30.0): raise HullParameterError("stem_rake_angle", p.stem_rake_angle, "[0, 30] degrees")`. Place after the existing angular-range checks (deadrise, transom).
- [ ] T005 In `src/storebro/hull.py`, update the `_StationProfile` dataclass to add `stem_rake_angle_deg: float = 0.0` (additive with default; existing callers ignore).
- [ ] T006 In `src/storebro/hull.py`, rewrite `_compute_stations` per data-model §3. Five stations transom-aft-amidships-fwd-stem with updated profile values. Critical: the Stem station changes from `is_terminal=True, half_beam=0.0` to `is_terminal=False, half_beam_at_top=0.040, half_beam_at_bottom=0.040, keel_depth=0.0, freeboard=p.sheer_height_fwd, stem_rake_angle_deg=p.stem_rake_angle`. The 40mm half-beam produces an 80mm-wide stem face.
- [ ] T007 In `src/storebro/hull.py`, modify `_create_datum_plane` to add the stem-rake rotation branch: if `profile.name == "Stem" and profile.stem_rake_angle_deg > 0.0`, set `rotation = FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), profile.stem_rake_angle_deg)`; else `rotation = FreeCAD.Rotation()`. Apply via `datum.AttachmentOffset = FreeCAD.Placement(FreeCAD.Vector(0.0, 0.0, profile.x_position * _MM_PER_M), rotation)`.
- [ ] T008 In `src/storebro/hull.py`, modify `_create_station_sketch` to add the quarter-circle bilge arc for non-terminal stations. Compute `bilge_radius_mm = profile.half_beam_at_bottom * 1000.0 * 0.5`. Create `Part.ArcOfCircle` centered at `(bilge_radius_mm, -keel_depth_mm + bilge_radius_mm)` spanning `math.pi` to `1.5 * math.pi` (quarter-circle from keel-centerline to bottom-outer). Replace the first line segment with the arc; the remaining 4 line segments (bottom-outer → top-outer → outer-sheer → centerline-deck → close-to-keel) stay as `Part.LineSegment`. Coincident constraints chain: arc_end → seg1_start, seg1_end → seg2_start, ..., seg4_end → arc_start.
- [ ] T009 In `src/storebro/hull.py`, the Stem station ALWAYS produces a closed 5-line-segment rectangle — no bilge arc — per FR-003 + spec.allium invariant `StemSketchIsBlunt` (`has_blunt_stem_face = true`, `has_bilge_arc = false`). Special-case the stem in `_create_station_sketch` so the bilge-arc branch from T008 is bypassed when `profile.name == "Stem"`. The stem sketch is a simple rectangle: 5 LineSegments connecting `(0, 0)` → `(40mm, 0)` → `(40mm, sheer_fwd_mm)` → `(0, sheer_fwd_mm)` → close to `(0, 0)`, with 5 Coincident constraints chaining the endpoints.
- [ ] T010 In `src/storebro/hull.py`, add `import logging` to the module imports (top of file, alphabetical position with the other stdlib imports).
- [ ] T011 In `src/storebro/hull.py`, extract two helpers: `_build_loft(body, sketches, *, ruled) -> Any` (returns the AdditiveLoft with the given Ruled mode set) and `_loft_is_valid(loft) -> bool` (returns True iff `loft.Shape is not None and loft.Shape.Volume > 0 and loft.Shape.isClosed() and loft.Shape.BoundBox.XLength > 0`). Both helpers private. Place above `_apply_loft_and_mirror`.
- [ ] T012 In `src/storebro/hull.py`, rewrite `_apply_loft_and_mirror` per data-model §8: call `_build_loft(body, sketches, ruled=False)` and `target_doc.recompute()`. If `not _loft_is_valid(loft)`, log a warning via `logging.warning(...)`, `body.Document.removeObject(loft.Name)`, recompute, then build with `ruled=True` and recompute. Then create the mirror feature as before (`body.newObject("PartDesign::Mirrored", "HullMirror")` etc.) and return `(loft, mirror)`.
- [ ] T013 In `src/storebro/hull.py`, update `_bind_parameters_to_body_properties` to add the 9th property: `body.addProperty("App::PropertyAngle", "StemRakeAngle", "Hull", "Stem rake from vertical (forward lean of bow)")` and assign `body.StemRakeAngle = parameters.stem_rake_angle`.

### Foundational tests (parallel after T013)

- [ ] T014 [P] Create `tests/geometry/test_hull_bspline_loft.py`: build a hull with default parameters, locate the `HullLoft` (PartDesign::AdditiveLoft) child of the body, assert `loft.Ruled is False` and `loft.Shape.Volume > 0`. Marked `requires_freecad`. This catches the auto-fall-back regression (if `Ruled=True` somehow, the test fails).
- [ ] T015 [P] Create `tests/geometry/test_hull_silhouette.py`: build a hull, inspect `hull.body.Shape.BoundBox`. Assert `XLength` is `10350 ±100mm` (LOA ±1%), `YLength` is `3200 ±64mm` (beam ±2%), `ZLength` is between `1500mm` and `2300mm` (freeboard + draft envelope — accounts for the actual Z-range with new flatter sheer). Also assert `hull.body.Shape.isClosed()`.
- [ ] T016 [P] Create `tests/unit/test_hull_parameters_stem_rake.py`: parametrized over `stem_rake_angle` values `[-1.0, 31.0, 45.0]` — assert `HullParameterError` raised with `parameter_name == "stem_rake_angle"` and `valid_range == "[0, 30] degrees"`. Then test in-range values `[0.0, 6.0, 30.0]` — assert `HullParameters` constructs successfully. No FreeCAD needed.

**Checkpoint**: `uv run ruff check src/ tests/ && uv run mypy --strict src/` clean.

---

## Phase 3: User Story 1 — Side-view silhouette matches reference (P1, MVP)

**Goal**: Generated hull's right-side silhouette matches `docs/references/Alternativ3.JPG` reference within tolerance.

**Independent Test**: `uv run pytest -m requires_freecad tests/geometry/test_hull_silhouette.py -v` green; visual inspection in GUI matches reference per FR-012.

- [ ] T017 [US1] Run `PYTHONPATH=... uv run pytest -m requires_freecad tests/geometry/test_hull_default_call.py tests/geometry/test_hull_default_dimensions.py tests/geometry/test_hull_silhouette.py -v`. Verify all pass. This is the core US1 acceptance gate — the hull constructs, has correct LOA + beam, and matches reference within ±1% / ±5% tolerances.
- [ ] T018 [US1] Run `PYTHONPATH=... uv run pytest -m requires_freecad tests/geometry/test_hull_topology.py tests/geometry/test_hull_estimated_dimensions.py tests/geometry/test_hull_determinism.py -v`. Verify all pass. Topology (closed manifold), estimated-height envelope, and determinism (two consecutive builds → identical volume/bbox/face count).
- [ ] T019 [US1] Run `PYTHONPATH=... uv run pytest -m requires_freecad tests/geometry/test_hull_parametricity.py tests/geometry/test_hull_composition.py tests/geometry/test_hull_construction_errors.py tests/geometry/test_hull_gui_editability.py tests/geometry/test_hull_visual_signoff.py -v`. Verify all pass. Parametricity, composition with user document, error paths, GUI editability (9 named properties now), visual signoff artifact regeneration.
- [ ] T020 [US1] Run `PYTHONPATH=... uv run pytest -m requires_freecad tests/geometry/test_hull_partdesign_feature_types.py tests/geometry/test_hull_rollback_discipline.py -v`. Verify all pass. PartDesign feature graph topology unchanged (5+5+1+1), no legacy Part-workbench types, rollback discipline preserved.

**Checkpoint**: All hull-tier tests pass. The hull is constructable with the new dimensions.

---

## Phase 4: User Story 2 — Smooth surface (B-spline loft) (P1)

**Goal**: AdditiveLoft uses `Ruled=False` for canonical defaults; the auto-fall-back to `Ruled=True` only triggers for out-of-envelope parameters.

**Independent Test**: T014's `test_hull_bspline_loft.py` passes.

- [ ] T021 [P] [US2] Run `PYTHONPATH=... uv run pytest -m requires_freecad tests/geometry/test_hull_bspline_loft.py -v`. Verify pass — confirms `loft.Ruled is False` for canonical RC34 defaults. If this fails, the auto-fall-back was triggered (check stderr for the `WARNING` line); diagnose by visualizing the loft in FreeCAD GUI and adjusting station profile dimensions or the bilge arc geometry until B-spline interpolation succeeds.

---

## Phase 5: User Story 3 — Backward compatibility (P2)

**Goal**: All downstream modules (deck, interior, export, cli) work without source-code changes. Public Hull dataclass + 8 v1.0.0 named properties + exception attribute shapes unchanged. The new 9th property `StemRakeAngle` is additive.

**Independent Test**: Re-run downstream geometry tests after hash baselines refresh.

- [ ] T022 [P] [US3] Re-run unit-test suite `uv run pytest tests/unit/ -v` (no FreeCAD needed). All ~150 unit tests pass; new `test_hull_parameters_stem_rake.py` passes. No regression in any public-API behavior.
- [ ] T023 [P] [US3] Run `PYTHONPATH=... uv run pytest -m requires_freecad tests/geometry/test_deck_*.py tests/geometry/test_interior_*.py -v`. Verify all pass on the new hull shape. Deck adapts via `_sample_hull_sheer` (already follows whatever sheer values come from HullParameters). Interior compartment-fit tests use the new larger draft (1.10m vs 0.95m) — should still fit.

---

## Phase N: Polish & Cross-Cutting Concerns

- [ ] T024 [P] Run `uv run ruff check src/ tests/ docs/` and fix any complaints. Run `uv run ruff format src/ tests/ docs/`.
- [ ] T025 Regenerate hash baselines: `PYTHONPATH=... uv run python tests/geometry/fixtures/refresh_hashes.py` to print the new TOML stanzas. Replace the existing rows in `tests/geometry/fixtures/expected_hashes.toml` with the freshly-printed ones. Eyeball the new hashes (64-char hex). Commit.
- [ ] T026 Run `PYTHONPATH=... uv run pytest -m requires_freecad tests/geometry/test_export_*.py -v`. Verify all export tests pass against the refreshed baselines. STEP, STL, BREP, FCStd determinism + metadata scrub all green.
- [ ] T027 Run `PYTHONPATH=... uv run pytest -m requires_freecad tests/geometry/test_cli_build_*.py -v`. Verify CLI build tests pass (one xfail: `test_storebro_build_byte_deterministic` is documented v1.1+ deferral; others pass). End-to-end `storebro build` works.
- [ ] T028 Run `uv run mypy --strict src/` and verify clean. The `logging` import is stdlib; no new dependencies.
- [ ] T029 Run the v1.0.1 signoff build: `PYTHONPATH=... uv run storebro build --out /Users/jool/repos/storebro/storebro_v1.0.1_signoff.FCStd`. Verify exit code 0 and file exists. **MANUAL STEP**: open in FreeCAD GUI, press `3` for right-side view, compare against `docs/references/Alternativ3.JPG`'s upper-half profile. Verify (a) stem near-vertical with slight forward rake, (b) transom near-vertical, (c) sheer near-flat (no dramatic rise from aft to bow). Capture screenshot for PR description per constitution V.
- [ ] T030 Bump version: `pyproject.toml` `version = "1.0.0"` → `version = "1.0.1"`. `src/storebro/__init__.py` `__version__ = "1.0.0"` → `__version__ = "1.0.1"`. Run `uv sync --extra dev` to refresh.
- [ ] T031 [P] Update `PROJECT-BRIEF.md` Core Modules table: `storebro.hull` annotation gains `+ spec 007 hull fidelity refresh 2026-05-17` and version bumps to `v1.0.1`.
- [ ] T032 [P] Update `CHANGELOG.md` (or create with keep-a-changelog format if absent) with the v1.0.1 entry: parameter default changes, new stem_rake_angle field, B-spline loft, blunt stem, rounded bilges. Run draft through the `humanizer` skill per CLAUDE.md before final commit.
- [ ] T033 Full pytest `PYTHONPATH=... uv run pytest -v`. Confirm all unit + geometry tests green (with 1 documented xfail for cross-invocation FCStd determinism from spec 006). Total ≥330 tests green.
- [ ] T034 Tick `specs/INDEX.md`: `[/] 007` → `[x] 007`. Append register-history line: `2026-05-17 — spec 007 closed; v1.0.1 ready to tag. Hull silhouette now matches storebropassion.de reference within tolerance: blunt stem with 6° rake, near-vertical transom (5°), near-flat sheer (210mm rise), 8° deadrise (semi-displacement), smooth B-spline loft, quarter-circle rounded bilges. Public API additive only (new stem_rake_angle field).`
- [ ] T035 After T029 manual signoff records the constitution V line, commit spec 007 with humanizer-clean message and **tag v1.0.1**: `git tag -a v1.0.1 -m "..."`.

**Final checkpoint**: T033 green + T029 manual signoff captured + register has `[x] 007` + `git tag` shows `v1.0.1` → **v1.0.1 SHIPS**.

---

## Dependencies & Execution Order

### Phase dependencies

- Phase 1 (Setup): needs FreeCAD on host
- Phase 2 (Foundational): needs Phase 1; BLOCKS US1 / US2 / US3
- Phase 3 (US1): needs Phase 2; the MVP — silhouette matches reference
- Phase 4 (US2): needs Phase 2; tests B-spline loft mode
- Phase 5 (US3): tests already covered transitively through T017-T020 + T022-T023
- Phase N (Polish): needs all prior phases, especially T025 (hash refresh) before T026 (export tests against new baselines)

### Per-task dependencies

- T003-T013 all touch `src/storebro/hull.py` → sequential
- T014-T016 [P] after T013
- T017-T020 [US1] sequential (build on each other's green test runs)
- T021 [P] [US2] after T013
- T022 [P] [US3] independent of FreeCAD (unit tier)
- T023 [P] [US3] after T020 (hull must work first)
- T024 [P] before T025/T026/T028 (lint clean before final runs)
- T025 before T026 (hash refresh blocks export tests)
- T028 after T024 (type check after lint)
- T029 needs T020 (signoff artifact path)
- T030-T032 [P] in polish
- T033 needs all test tasks complete
- T034 needs T033 green
- T035 needs T029 manual signoff + T034 register tick

---

## Implementation Strategy

### MVP First (US1 — silhouette matches reference)

1. Setup (T001-T002): confirm FreeCAD + snapshot v1.0.0 bbox
2. Foundational (T003-T016): rewrite hull.py
3. US1 (T017-T020): verify all hull-tier tests green with new shape
4. STOP + VALIDATE: silhouette matches per FR-001 acceptance scenarios

### Incremental Delivery

1. Setup + Foundational → hull.py compiles and ruff/mypy clean
2. + US1 → 96 geometry tests pass on new shape; new silhouette test passes
3. + US2 → B-spline loft confirmed via test_hull_bspline_loft.py
4. + US3 → downstream modules + unit tests still pass
5. + Polish → hash baselines refreshed, manual signoff captured, **v1.0.1 tag**

### Solo Strategy

Direct push to master (per `.claude/rules/project-workflow.md`). One commit when the full pipeline ends (after `/tla` step). Tag `v1.0.1` immediately after the spec 007 commit lands on master and T029's manual signoff is recorded in the commit message.

---

## Notes

- Total tasks: 35. Smaller than spec 006 (which had 31 + the bug-fix follow-up) because spec 007 is genuinely scoped: 1 file, 6 functions, ~80 LOC.
- The MVP (US1) ships at T020 when the silhouette tests pass. Polish adds hash refresh + downstream verification + signoff + v1.0.1 tag.
- After v1.0.1, the next spec candidates are the v1.1+ items from the deferred markers across specs 005/006/007: hard chine variant, compound bilge curves, expression-engine bindings, full-assembly multi-format export, cross-invocation FCStd determinism, body plan from primary source.
