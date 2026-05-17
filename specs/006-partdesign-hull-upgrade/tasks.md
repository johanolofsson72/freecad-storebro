---
description: "Task list for the PartDesign hull upgrade (spec 006)"
---

# Tasks: PartDesign Hull Upgrade

**Input**: Design documents from `/specs/006-partdesign-hull-upgrade/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/python-api-preserved.md](./contracts/python-api-preserved.md), [quickstart.md](./quickstart.md), [spec.allium](./spec.allium)

**Tests**: REQUIRED per constitution V. The 86 currently-failing geometry tests are the primary acceptance gate; one new test asserts PartDesign feature types are used (no legacy Part-workbench types inside the Body).

**Critical context**: this spec is BLOCKING for v1.0.0 tag. The legacy hull does not construct on FreeCAD 1.1.1 — every downstream module fails until this lands. Implementation scope is surgical: 2 private functions in `src/storebro/hull.py` rewritten, 1 added, plus rollback discipline in `build_hull`.

## Format: `[ID] [P?] [Story?] Description with file path`

## Path Conventions

Single Python project, src-layout (continues from spec 001-005):
- Library source: `src/storebro/` (only `hull.py` modified in this spec)
- Tests: `tests/unit/` (unchanged) + `tests/geometry/` (86 failing tests turn green + 1 new test)
- Hash baselines: `tests/geometry/fixtures/expected_hashes.toml` (regenerated)

---

## Phase 1: Setup

- [x] T001 Confirm the FreeCAD-equipped host is ready: `uv run storebro info` reports `FreeCAD detected: 1.1.x` (or any version inside the supported range). If not, fix `PYTHONPATH` per the macOS onboarding note (`export PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib`) and re-run.
- [x] T002 Snapshot the current state of the 86 failing geometry tests: `uv run pytest -m requires_freecad -v 2>&1 | tee /tmp/spec006_before.log`. Verify the log shows 86 failures, all with `HullConstructionError: ValueError: Body: object is not allowed`. This is the regression baseline — the count must drop to 0 after T015.

---

## Phase 2: Foundational

These tasks rewrite `src/storebro/hull.py`'s private functions and add the rollback discipline. They are sequential because they all touch the same file.

- [x] T003 In `src/storebro/hull.py`, add a new private helper `_create_datum_plane(profile: _StationProfile, body: Any) -> Any` immediately before `_create_station_sketch`. The helper does: `datum = body.newObject("PartDesign::Plane", f"HullDatum{profile.name}")`; `datum.AttachmentSupport = (body.Origin.YZ_Plane, "")`; `datum.MapMode = "FlatFace"`; `datum.AttachmentOffset = FreeCAD.Placement(FreeCAD.Vector(profile.x_position, 0.0, 0.0), FreeCAD.Rotation())`; `return datum`. Imports `FreeCAD` locally inside the function (matches the existing pattern in `hull.py`).
- [x] T004 In `src/storebro/hull.py`, rewrite `_create_station_sketch` to use `Sketcher::SketchObject` attached to a datum plane. New signature: `_create_station_sketch(profile: _StationProfile, body: Any, datum: Any) -> Any` (the `parent_doc` parameter is dropped; `datum` replaces it). Body: `sketch = body.newObject("Sketcher::SketchObject", f"HullStation{profile.name}")`; `sketch.AttachmentSupport = (datum, "")`; `sketch.MapMode = "FlatFace"`. For terminal stem: a single zero-length `Part.LineSegment(Vector(0,0,0), Vector(0,0,0))` via `sketch.addGeometry(seg, False)`. For non-terminal: five `Part.LineSegment(...)` calls forming the closed half-section polygon per data-model §5. Return the sketch.
- [x] T005 In `src/storebro/hull.py`, rewrite `_apply_loft_and_mirror(body: Any, sketches: list[Any]) -> None` (drop the `parent_doc` parameter — the Body knows its document). Body: `loft = body.newObject("PartDesign::AdditiveLoft", "HullLoft")`; `loft.Profile = (sketches[0], [""])`; `loft.Sections = [(s, [""]) for s in sketches[1:]]`; `loft.Ruled = False`; `loft.Closed = False`; `loft.Solid = True`. Then: `mirror = body.newObject("PartDesign::Mirrored", "HullMirror")`; `mirror.Originals = [loft]`; `mirror.MirrorPlane = (body.Origin.XZ_Plane, [""])`. Finally: `body.Tip = mirror`. Remove every reference to `Part::Loft`, `Part::Mirroring`, `Part::MultiFuse`, and `body.addObject(...)`.
- [x] T006 In `src/storebro/hull.py`, update `build_hull` to wire up the new helpers and add rollback discipline. After `body_label = _resolve_body_label(name)` and before the try block, initialize `added: list[Any] = []`. Inside the try: append `body` to `added` after the `addObject` call; for each station profile, call `datum = _create_datum_plane(profile, body)` then `sketch = _create_station_sketch(profile, body, datum)` and append both to `added`; collect sketches into a list; call `_apply_loft_and_mirror(body, sketches)` and append the loft + mirror to `added` (returned via a refactored signature — see T005 follow-up below). Catch `HullConstructionError`: for `obj in reversed(added): target_doc.removeObject(obj.Name)`; re-raise. Catch `BaseException`: same rollback + wrap in `HullConstructionError(...)` per spec.allium `RollbackOnConstructionFailure`.
- [x] T007 In `src/storebro/hull.py`, refactor `_apply_loft_and_mirror` to return `tuple[Any, Any]` (the loft and the mirror) so `build_hull` can append them to its `added` rollback list. Or expose them via a `body.Group` iteration after the call — pick whichever is cleaner. The rollback discipline MUST be able to remove every object that was created during the call, in reversed order.
- [x] T008 In `src/storebro/hull.py`, audit the module top for stale comments referring to "v0.1.0-alpha", "future PartDesign upgrade", or "PartDesign loft requires more setup". Update the docstrings of `_create_station_sketch` and `_apply_loft_and_mirror` to describe the PartDesign feature graph they actually build (data-model §5-§8). Remove the `_ = body` placeholder comment in `_create_station_sketch` — `body` is now meaningfully used.

### Foundational tests (parallel after T007)

- [x] T009 [P] Create `tests/geometry/test_hull_partdesign_feature_types.py`: build a hull, assert `hull.body.TypeId == "PartDesign::Body"`, assert `hull.body.Tip.TypeId == "PartDesign::Mirrored"`, iterate `hull.body.Group` and collect `obj.TypeId` values, assert the set is `{"App::Origin", "PartDesign::Plane", "Sketcher::SketchObject", "PartDesign::AdditiveLoft", "PartDesign::Mirrored"}` (with the expected counts: 1 Origin, 5 Planes, 5 Sketches, 1 AdditiveLoft, 1 Mirrored), assert no legacy Part-workbench types appear in the set. Marked `requires_freecad`.
- [x] T009a [P] Create `tests/geometry/test_hull_rollback_discipline.py` (FR-012 + spec.allium `RollbackOnConstructionFailure`): monkeypatch one of the internal helpers (`_create_station_sketch`, `_apply_loft_and_mirror`, or `_compute_stations` deep enough that the Body has already been added) to raise a forced `RuntimeError` mid-construction. Then call `build_hull(document=fresh_doc)`, catch the `HullConstructionError`, and assert `len([o for o in fresh_doc.Objects if o.TypeId.startswith("PartDesign::") or o.TypeId == "Sketcher::SketchObject"]) == 0`. The document must be byte-identical to its pre-call state — no orphan datums, sketches, lofts, mirrors, or Bodies. Marked `requires_freecad`.

**Checkpoint**: `uv run ruff check src/ && uv run mypy --strict src/` clean — pure syntactic / type validation, no FreeCAD needed.

---

## Phase 3: User Story 1 — Hull constructs on FreeCAD 1.1+ (P1, MVP)

**Goal**: All 86 currently-failing geometry tests pass on FreeCAD 1.1.1.

**Independent Test**: `uv run pytest -m requires_freecad -v` reports 0 failures (plus the new PartDesign test from T009 also green).

- [x] T010 [US1] Run `uv run pytest -m requires_freecad tests/geometry/test_hull_default_call.py -v`. Verify all tests pass. This is the core construction test — if it passes, every downstream test that wraps `build_hull()` is unblocked.
- [x] T011 [US1] Run `uv run pytest -m requires_freecad tests/geometry/test_hull_default_dimensions.py tests/geometry/test_hull_estimated_dimensions.py tests/geometry/test_hull_topology.py tests/geometry/test_hull_determinism.py -v`. Verify all pass. Reference fidelity (FR-014, constitution IV), topology (FR-007), determinism (FR-008) at the hull tier.
- [x] T012 [US1] Run `uv run pytest -m requires_freecad tests/geometry/test_hull_parametricity.py tests/geometry/test_hull_composition.py tests/geometry/test_hull_construction_errors.py tests/geometry/test_hull_gui_editability.py tests/geometry/test_hull_visual_signoff.py -v`. Verify all pass. Parametricity (changing LOA changes the bounding box), composition (user-supplied document), error paths, GUI editability (named properties on Body), visual signoff artifact.
- [x] T013 [US1] Run `uv run pytest -m requires_freecad tests/geometry/test_deck_*.py tests/geometry/test_interior_*.py -v`. Verify all pass (deck and interior depend transitively on hull). Spec 003 + spec 004 acceptance gates re-validate now that the hull constructs.
- [x] T013a [US1] Regenerate hash baselines BEFORE running export tests, since the PartDesign feature graph produces structurally different `.FCStd` / `.step` / `.stl` / `.brep` bytes than the legacy v0.1.0-alpha. Run `uv run python tests/geometry/fixtures/refresh_hashes.py`, eyeball `git diff tests/geometry/fixtures/expected_hashes.toml` (new hashes should be 64-char hex strings, no obvious corruption). The legacy baselines (if any) get replaced. This was originally T019 in the Polish phase but reordered to here so T014 runs cleanly. (T019 is retained as a no-op final-state verification.)
- [x] T014 [US1] Run `uv run pytest -m requires_freecad tests/geometry/test_export_*.py -v`. Verify all pass. Spec 002 acceptance gates: STEP, STL, BREP, FCStd writers all work because they each construct a hull first, plus byte-determinism gates against the freshly-seeded hash baselines from T013a.
- [x] T015 [US1] Run `uv run pytest -m requires_freecad tests/geometry/test_cli_build_*.py -v`. Verify all pass. Spec 005 acceptance gate: end-to-end `storebro build` CLI invocation.

**Checkpoint**: `uv run pytest -m requires_freecad -v 2>&1 | tee /tmp/spec006_after.log`. Compare to `/tmp/spec006_before.log` from T002 — the 86 failures should be 0 failures. If hash-baseline failures remain, they get fixed in T019 (polish).

---

## Phase 4: User Story 2 — GUI editability (P2)

**Goal**: A user can open the generated `.FCStd` in FreeCAD GUI, see the PartDesign tree, double-click a station sketch, modify a handle, recompute, and see the hull deform.

**Independent Test**: Manual signoff on a FreeCAD-equipped host (deferred to T020 with the visual signoff).

- [x] T016 [P] [US2] T009's `test_hull_partdesign_feature_types.py` provides the automated check: PartDesign feature types are present, no legacy Part-workbench types. Re-run after T015 to ensure no regression: `uv run pytest -m requires_freecad tests/geometry/test_hull_partdesign_feature_types.py -v`.

---

## Phase 5: User Story 3 — Backward compatibility (P2)

**Goal**: Downstream modules (deck, interior, export, CLI) work without source code changes.

**Independent Test**: T013 + T014 + T015 are the verification.

- [x] T017 [P] [US3] Re-run the full unit-test suite `uv run pytest tests/unit/ -v` (no FreeCAD needed). All ~150 unit tests pass; no module's public API contract was broken by the hull refactor.

---

## Phase N: Polish & Cross-Cutting Concerns

- [x] T018 [P] Run `uv run ruff check src/ tests/ docs/` and fix any complaints from the hull.py edits. Run `uv run ruff format src/ tests/ docs/` to normalize.
- [x] T019 (Done at T013a — verification only) Confirm `tests/geometry/fixtures/expected_hashes.toml` is staged with the regenerated hashes and `git diff` shows no further drift after the full polish-phase test runs. Hash refresh itself happened at T013a; this is the audit checkpoint.
- [x] T020 Re-run the full geometry suite once more to capture the deterministic post-refresh state: `uv run pytest -m requires_freecad -v 2>&1 | tee /tmp/spec006_final.log`. Expected: 0 failures, 0 skips (or only the documented "no baseline for this FreeCAD version" skips if hash refresh produced format-conditional outputs).
- [x] T021 Run `uv run mypy --strict src/` and verify clean. The PartDesign feature graph code is typed `Any` throughout (FreeCAD bindings have no stubs); the mypy override in `pyproject.toml`'s `[[tool.mypy.overrides]]` should already cover it.
- [x] T022 Verify `pyproject.toml` shows `version = "1.0.0"` and `Development Status :: 5 - Production/Stable` (both set during spec 005's T002). Verify `src/storebro/__init__.py` shows `__version__ = "1.0.0"`. No edits expected — this is an audit checkpoint only. If anything has drifted, fix it as part of T029's tag commit.
- [~] T023 Run the v1.0.0 signoff build: `uv run storebro build --out /tmp/storebro_v1_signoff.FCStd`. Verify exit code 0 and file exists. **MANUAL STEP**: open `/tmp/storebro_v1_signoff.FCStd` in FreeCAD GUI. Expand the HullBody in the tree, verify the structure matches data-model §1 (5 datum planes + 5 sketches + 1 AdditiveLoft + 1 Mirrored). Double-click `HullStation3` (amidships sketch), drag a single handle 100 mm outward, accept the sketch, recompute the document, verify the hull's amidships beam visibly changes. This is constitution V's manual visual signoff gate.
- [x] T024 [P] Update `PROJECT-BRIEF.md` Core Modules table: `storebro.hull` annotation changes from "v1.0.0 (spec 001 implemented 2026-05-17)" to "v1.0.0 (spec 001 + spec 006 PartDesign rebuild 2026-05-17)" or similar. Bump no version number; this is internal lineage.
- [x] T025 [P] Update `README.md`'s "Project status" section if needed. The 5/5 module table can stay; consider adding a footnote noting the v1.0.0 hull is PartDesign-idiomatic per spec 006.
- [~] T026 [P] Update `CHANGELOG.md` (or create it if absent) with the v1.0.0 entry per constitution's "keep-a-changelog" reference. Initial entry: list the 5 module deliverables plus the spec 006 PartDesign rebuild fix. Mark the changelog as "draft" and run through the `humanizer` skill per CLAUDE.md before final commit.
- [x] T027 Run `uv run pytest -v` (full suite, unit + geometry). Confirm: ~150 unit tests pass + 86+1 geometry tests pass + the visual signoff artifact present at `/tmp/storebro_v1_signoff.FCStd`. Total ≥237 tests green.
- [x] T028 Tick `specs/INDEX.md`: `[/] 006` → `[x] 006`. **This UNBLOCKS the v1.0.0 register tag.** Append a register-history line: `2026-05-17 — spec 006 closed; v1.0.0 milestone unblocked. Tag pending manual visual signoff (T023).`
- [~] T029 After T023 manual signoff records "Visually verified in FreeCAD: 1.1.1 on macOS arm64 — dragged HullStation3 handle, hull recomputed and amidships beam changed correspondingly", commit spec 006 with the humanizer-clean message and **tag v1.0.0** per the constitution: `git tag v1.0.0`. This is the constitution's "all four v1.0 modules + CLI" milestone — finally achieved.

**Final checkpoint**: T027 green + T023 manual signoff captured + register has 5/5 + 1/1 (006) ticked + `git tag` shows `v1.0.0` → **v1.0.0 SHIPS**.

---

## Dependencies & Execution Order

### Phase dependencies

- Phase 1 (Setup): needs FreeCAD on host (`storebro info` confirms)
- Phase 2 (Foundational): needs Phase 1; BLOCKS US1 / US2 / US3
- Phase 3 (US1): needs Phase 2; the MVP — 86 failing tests turn green
- Phase 4 (US2): tests already covered in foundational tier (T009), no separate work
- Phase 5 (US3): tests already covered transitively through T013/T014/T015
- Phase N (Polish): needs all prior phases, especially T019 (hash refresh) before T020 (full re-run)

### Per-task dependencies

- T003-T008 all touch `src/storebro/hull.py` → sequential
- T009, T009a [P] after T008
- T010-T013 [US1] sequential (build on each other's green test runs)
- T013a between T013 and T014 (hash baseline refresh — was T019, reordered per spec 006 analyze remediation A2)
- T014-T015 [US1] sequential
- T016 [P] [US2] after T009 (re-runs the same test for regression check)
- T017 [P] [US3] independent of FreeCAD tests
- T018 [P] before T020
- T019 before T020 (hash refresh blocks deterministic full-suite run)
- T021 after T020 (type check is independent but cleaner to run last)
- T022-T026 [P] in polish, independent
- T027 needs all prior tests green
- T028 needs T027 green
- T029 needs T023 manual signoff + T028 register tick

---

## Implementation Strategy

### MVP First (US1 — hull constructs end-to-end)

1. Setup (T001-T002): confirm FreeCAD + snapshot baseline failures
2. Foundational (T003-T009): rewrite hull.py
3. US1 (T010-T015): verify all 86 tests turn green
4. STOP + VALIDATE: full geometry suite green, ready for v1.0.0 signoff

### Incremental Delivery

1. Setup + Foundational → hull.py compiles and ruff/mypy clean
2. + US1 → 86 failing tests turn green; downstream modules work end-to-end
3. + US2 + US3 → PartDesign feature-type assertion + unit-test regression check
4. + Polish → hash baselines refreshed, manual signoff captured, **v1.0.0 tag**

### Solo Strategy

Direct push to master (per `.claude/rules/project-workflow.md`). One commit when the full pipeline ends (after `/tla` step). Tag `v1.0.0` immediately after the spec 006 commit lands on master and T023's manual signoff is recorded in the commit message.

---

## Notes

- Total tasks: 29. Most are verification runs (T010-T015 are pytest invocations); the actual code rewrite is T003-T008 (6 small focused changes).
- The MVP (US1) ships at T015 when the 86 failing tests turn green. Polish adds the hash baseline refresh, the manual signoff, and the v1.0.0 tag.
- After this spec, the next spec candidates are the v1.1+ items from the spec 005 + spec 006 deferred markers: full-assembly STEP/STL/BREP export, expression-engine binding, multi-format CLI, configuration files, hull/deck CLI overrides.
