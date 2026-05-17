---
description: "Task list for the hull module (spec 001)"
---

# Tasks: Hull Module

**Input**: Design documents from `/specs/001-hull-module/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/python-api.md](./contracts/python-api.md), [quickstart.md](./quickstart.md), [spec.allium](./spec.allium)

**Tests**: REQUIRED. Tests are mandatory per constitution principle V (Test-Gated Releases) — `pytest` is CI-enforced and PRs cannot merge without green tests. Every public function has at least one geometry property test (SC-006) and at least 5 invalid-input cases exist (SC-007).

**Organization**: Tasks are grouped by user story. Within each story, implementation tasks that touch the same file (`src/storebro/hull.py`) are intentionally sequential — `[P]` is only used when tasks touch distinct files with no dependency on incomplete work.

## Format: `[ID] [P?] [Story] Description with file path`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User-story label (US1, US2, US3) — Setup, Foundational, and Polish phases have no story label
- File paths are repository-relative

## Path Conventions

Single Python project, src-layout. Paths are repo-relative:
- Library source: `src/storebro/`
- Tests: `tests/unit/` (no FreeCAD), `tests/geometry/` (marker `requires_freecad`)
- Examples: `docs/examples/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and toolchain configuration. No story label.

- [X] T001 Create directory tree: `src/storebro/`, `tests/unit/`, `tests/geometry/`, `docs/examples/`
- [X] T002 Create `pyproject.toml` at repo root: hatchling build backend, project name `freecad-storebro`, version `0.1.0`, Python `>=3.11,<3.13`, dependency `freecad-storebro` extras: `[tool.freecad-storebro] supported_freecad = ">=1.1,<2.0"` (per research.md R6), description matching constitution
- [X] T003 [P] Configure ruff in `pyproject.toml` under `[tool.ruff]`: line-length 100, target-version py311, select rules E/F/W/I/UP/B/SIM/RUF, exclude `.venv` and FreeCAD-stub directories
- [X] T004 [P] Configure mypy in `pyproject.toml` under `[tool.mypy]`: strict mode, target python_version "3.11", ignore_missing_imports for `FreeCAD` and `Part` and `Sketcher` modules
- [X] T005 [P] Configure pytest in `pyproject.toml` under `[tool.pytest.ini_options]`: testpaths `["tests"]`, register markers `requires_freecad` and `unit`, addopts `-ra --strict-markers`
- [X] T006 Create placeholder `src/storebro/__init__.py` with `__version__ = "0.1.0"` and empty `__all__ = []` (to be expanded as public names are added)

**Checkpoint**: `uv sync` completes; `uv run ruff check .` and `uv run mypy src/` and `uv run pytest --collect-only` all run cleanly against an empty source tree.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Test scaffolding, exception classes, parameter dataclass, and the FreeCAD version-check helper. **All user stories depend on these.** No story label.

**⚠️ CRITICAL**: No US1/US2/US3 work can begin until this phase is complete.

- [X] T007 Create `tests/conftest.py` at repo root: register the `requires_freecad` and `unit` markers via `pytest_configure(config)`; add a global `pytest_collection_modifyitems` hook that auto-tags `tests/geometry/**` items with `requires_freecad`
- [X] T008 [P] Create empty `tests/unit/__init__.py` and `tests/geometry/__init__.py`
- [X] T009 [P] Create `tests/geometry/conftest.py`: try-import `FreeCAD`; on `ImportError`, register a session-level fixture that calls `pytest.skip(allow_module_level=True)` for any test loaded in this directory; provide a `freecad_doc` fixture that creates a fresh in-memory FreeCAD document per-test and closes it on teardown
- [X] T010 [P] Implement `src/storebro/_freecad_check.py`: module-level `_FREECAD_VERSION_OK: bool | None = None` cache; `_read_supported_range_from_pyproject()` using `tomllib` (stdlib in 3.11+); `ensure_supported_freecad()` raises `HullConstructionError` with `detected_version` and `supported_range` set when FreeCAD's `Version` falls outside the declared range; lazy — only called from `build_hull`, never at import
- [X] T011 Define exception classes in `src/storebro/hull.py` at the top of the file: `HullParameterError(ValueError)` with `__init__(parameter_name, parameter_value, valid_range)` and the three named attributes; `HullConstructionError(RuntimeError)` with `__init__(message, *, parameters=None, underlying=None, detected_version=None, supported_range=None)` and the four named attributes; both classes formatted message per data-model §3/§4
- [X] T012 In `src/storebro/hull.py` (after T011), define `HullParameters` as a `dataclass(frozen=True)` with the 8 fields, defaults, and `REFERENCE_STOREBRO_ROYAL_CRUISER_34_1972: ClassVar[dict[str, float]]` per data-model §1; implement `__post_init__` calling a private `_validate_hull_parameters(self)` that performs per-field range checks then cross-field geometric-impossibility checks in the documented order, raising `HullParameterError` on the first violation with the offending field name, value, and range
- [X] T013 Update `src/storebro/__init__.py` to re-export `HullParameters`, `HullParameterError`, `HullConstructionError` (and add them to `__all__`); the public surface is now non-empty even before `build_hull` exists, so unit tests can import the foundational types

### Foundational tests (run after corresponding implementation)

- [X] T014 [P] `tests/unit/test_hull_errors.py`: assert `issubclass(HullParameterError, ValueError)` and `issubclass(HullConstructionError, RuntimeError)`; verify each public attribute is set by `__init__`; verify the message format matches the SC-007 contract (cites parameter name, value, valid range) — at minimum 5 invalid-input cases (FR-004, FR-015, SC-007)
- [X] T015 [P] `tests/unit/test_hull_parameters.py`: defaults equal `REFERENCE_STOREBRO_ROYAL_CRUISER_34_1972`; per-field positivity rejections (loa<=0, beam_max<=0, draft<=0, freeboard<=0, sheer_height_aft<=0, sheer_height_fwd<=0); angular-range rejections (deadrise outside [0,30], transom_angle outside [0,45]); cross-field rejections (loa<=beam_max, sheer_height_fwd<sheer_height_aft); frozen-ness via `dataclasses.FrozenInstanceError`; hashable + equal-by-value
- [X] T016 [P] `tests/unit/test_freecad_check.py`: monkeypatch `FreeCAD.Version` to a stub returning `(1, 1, 0)` → passes; stub `(0, 20, 0)` → raises `HullConstructionError` with `detected_version=(0, 20)` and `supported_range="1.1 to <2.0"`; second call after a successful first call does not re-probe (caching behavior)

**Checkpoint**: Foundational types importable, all foundational unit tests pass: `uv run pytest tests/unit/ -v`.

---

## Phase 3: User Story 1 - FreeCAD scripter composes hull (Priority: P1) 🎯 MVP

**Goal**: A FreeCAD scripter imports `storebro.hull`, calls `build_hull(...)` with optional parameters, receives a fully editable parametric `Part::Body` they can compose with their own geometry. This is the foundational use case — without it the rest of the package is unusable.

**Independent Test**: From a Python REPL with FreeCAD on PATH, run `from storebro import build_hull; h = build_hull(); print(h.bbox, h.label, h.build_duration_seconds)` and verify the Body appears in the FreeCAD document tree with named editable hull dimensions.

### Implementation (all tasks touch `src/storebro/hull.py` and are sequential)

- [X] T017 [US1] Implement private `_resolve_document(document)` in `src/storebro/hull.py` per FR-016 / R4: if document is non-None use it; elif `FreeCAD.activeDocument()` is non-None use it; else `FreeCAD.newDocument()` and activate the new doc. Returns the resolved document.
- [X] T018 [US1] Implement private `_resolve_body_label(name)` in `src/storebro/hull.py` per FR-017 / R5: default `"Hull"`; FreeCAD applies auto-numbering when the label collides — the helper simply sets `body.Label = name` and relies on FreeCAD to disambiguate
- [X] T019 [US1] Implement private `_StationProfile` dataclass and `_compute_stations(parameters)` in `src/storebro/hull.py` per data-model §5 / research.md R2: produce 5 `_StationProfile` instances at `x ∈ {0, 0.25·loa, 0.5·loa, 0.75·loa, loa}`, each carrying the half-beam, keel depth, and freeboard cross-section parameters for that station, plus a `is_terminal` flag for the stem
- [X] T020 [US1] Implement private `_create_station_sketch(profile, body, name)` in `src/storebro/hull.py`: creates a `Sketcher::Sketch` on the YZ plane at `x = profile.x_position`, draws a half-section line set with horizontal/vertical/distance constraints bound to Body-level expressions; returns the sketch
- [X] T021 [US1] Implement private `_apply_loft_and_mirror(body, sketches)` in `src/storebro/hull.py`: add a `PartDesign::AdditiveLoft` feature consuming the 5 sketches in order; add a `PartDesign::Mirrored` feature reflecting the loft across the X-Z plane (FR-009 symmetric about centerline)
- [X] T022 [US1] Implement private `_bind_parameters_to_body_properties(body, parameters)` in `src/storebro/hull.py` per FR-007 / R2: add `App::PropertyLength` properties `LOA`, `BeamMax`, `Draft`, `Freeboard`, `SheerHeightAft`, `SheerHeightFwd`, and `App::PropertyAngle` properties `DeadriseAmidships`, `TransomAngle`; bind sketch constraints to these properties via the FreeCAD expression engine so GUI edits propagate
- [X] T023 [US1] In `src/storebro/hull.py`, define the `Hull` return dataclass per data-model §2 (non-frozen, identity-equal, `bbox` and `volume` properties)
- [X] T024 [US1] In `src/storebro/hull.py`, implement the public `build_hull(parameters=None, *, document=None, name="Hull")` function per contracts/python-api.md: (a) call `_freecad_check.ensure_supported_freecad()`; (b) coerce `parameters or HullParameters()`; the dataclass post-init already validated — re-validation only if caller passed a non-frozen mutated instance (defensive); (c) `_resolve_document`; (d) `time.perf_counter()` start; (e) create `Part::Body`, `_resolve_body_label`, `_bind_parameters_to_body_properties`; (f) `_compute_stations` → loop `_create_station_sketch` → `_apply_loft_and_mirror`; (g) `document.recompute()`; (h) wrap any FreeCAD exception in `HullConstructionError(parameters=..., underlying=...)`; (i) return `Hull(body, parameters, document, label, build_duration_seconds)`
- [X] T025 [US1] Update `src/storebro/__init__.py` to re-export `build_hull` and `Hull` (add to `__all__`)

### Tests for US1 (parallel, distinct files; run after T024)

- [X] T026 [P] [US1] `tests/geometry/test_hull_default_call.py`: `build_hull()` returns a `Hull` whose `body` is added to the active doc, `label == "Hull"`, `0 < build_duration_seconds < 30.0` (FR-001 + SC-002 30-s budget assertion), and `volume > 0`; second call returns a Hull whose label is `"Hull001"` (FR-017)
- [X] T027 [P] [US1] `tests/geometry/test_hull_gui_editability.py`: returned `body` has `App::PropertyLength` named properties `LOA`, `BeamMax`, `Draft`, `Freeboard`, `SheerHeightAft`, `SheerHeightFwd` and `App::PropertyAngle` properties `DeadriseAmidships`, `TransomAngle`; setting `body.BeamMax = 4.0` and calling `document.recompute()` changes `body.Shape.BoundBox.YLength` (FR-007)
- [X] T028 [P] [US1] `tests/geometry/test_hull_composition.py`: caller-supplied document name is not mutated; the active document remains active after `build_hull` returns; building into a user-supplied document leaves the document's existing top-level objects untouched (FR-016 contract guarantee 3)
- [X] T029 [P] [US1] `tests/geometry/test_hull_construction_errors.py`: force a FreeCAD construction failure (e.g. monkeypatch `Part::Body.addObject` to raise; or build with a parameter combination that passes validation but breaks the loft) and assert the raised exception is `HullConstructionError` with `parameters` and `underlying` attributes populated (FR-015, Edge Cases)
- [X] T030 [P] [US1] `tests/geometry/test_hull_topology.py`: `body.Shape.isClosed()` is True (FR-010 closed shell); for every face, mirroring its centroid across the X-Z plane yields another face on the body (FR-009 symmetric about centerline)

**Checkpoint**: `uv run pytest -m requires_freecad tests/geometry/test_hull_default_call.py tests/geometry/test_hull_gui_editability.py tests/geometry/test_hull_composition.py tests/geometry/test_hull_construction_errors.py tests/geometry/test_hull_topology.py -v` all pass. The MVP is functional — a scripter can build, inspect, and edit a default Storebro hull.

---

## Phase 4: User Story 2 - Boat restorer generates canonical Storebro hull (Priority: P2)

**Goal**: A boat restorer runs `build_hull()` with defaults and the resulting Body's principal dimensions match the historical Storebro Royal Cruiser 34 (1972) reference within ±1% (constitution principle IV, SC-001). Visual signoff in the FreeCAD GUI is the final acceptance.

**Independent Test**: `build_hull()` with no arguments → bbox length within 0.1035 m of 10.35 m, bbox width within 0.032 m of 3.20 m.

### Tests for US2 (parallel, distinct files)

- [X] T031 [P] [US2] `tests/geometry/test_hull_default_dimensions.py`: build the default hull and assert `abs(bbox_length - 10.35) <= 0.1035` and `abs(bbox_width - 3.20) <= 0.032` (citation-grade SC-001 fidelity check)
- [X] T032 [P] [US2] `tests/geometry/test_hull_estimated_dimensions.py`: build the default hull and assert draft / freeboard / sheer_height_aft / sheer_height_fwd values measured off the body match the estimate-grade defaults in `REFERENCE_STOREBRO_ROYAL_CRUISER_34_1972` to within ±1% (self-citing; the test catches silent drift inside the construction pipeline)
- [X] T033 [P] [US2] `tests/geometry/test_hull_visual_signoff.py`: build the default hull, save the document to `/tmp/storebro_hull_signoff_001.FCStd` via `document.saveAs(...)`, and write to stdout a one-line reminder: `"MANUAL SIGNOFF: open /tmp/storebro_hull_signoff_001.FCStd in FreeCAD and confirm proportions match docs/references/Alternativ*.JPG — record FreeCAD version + OS in PR description per constitution V"` (constitution principle V mandatory visual verification)

**Checkpoint**: All US2 tests green. Run `uv run python -c "from storebro import build_hull; h = build_hull(); h.document.saveAs('/tmp/storebro_hull.FCStd')"` and open the result in the FreeCAD GUI; eyeball against `docs/references/Alternativ3.JPG`.

---

## Phase 5: User Story 3 - Naval architecture student studies parametric variation (Priority: P3)

**Goal**: Every named hull parameter, when changed by ±10% from its default, produces a hull whose corresponding measured dimension changes monotonically in the expected direction — proving no silent no-op parameters (SC-004). Plus structural determinism for fixed inputs (SC-003, FR-005).

**Independent Test**: For each of the 8 named parameters, generate two hulls differing only in that parameter at ±10% and assert the corresponding bbox/topology measurement changes in the expected direction.

### Tests for US3 (parallel, distinct files)

- [X] T034 [P] [US3] `tests/geometry/test_hull_parametricity.py`: parameterized via `pytest.mark.parametrize` over the 8 named parameters. For each, build hulls at default and at default ±10% (clamped to valid ranges), assert the corresponding measured dimension (bbox length for `loa`, bbox width for `beam_max`, bbox height for `freeboard + draft`, etc.) changes monotonically in the documented direction (SC-004)
- [X] T035 [P] [US3] `tests/geometry/test_hull_determinism.py`: call `build_hull()` twice in succession (in separate fresh documents via fixture); assert `volume`, all three bbox dimensions, and topology counts (`Shape.Vertexes`, `Shape.Edges`, `Shape.Faces`) are identical to within `1e-9` relative tolerance for the floats and exact equality for the counts (FR-005, SC-003)

**Checkpoint**: All three user stories' tests pass: `uv run pytest -m requires_freecad -v` is fully green.

---

## Phase N: Polish & Cross-Cutting Concerns

- [X] T036 [P] Write `docs/examples/hull_quickstart.py` — a runnable example matching the first three sections of `quickstart.md` (default hull, save and inspect, custom parameters); add a docstring header that links back to `specs/001-hull-module/quickstart.md`
- [X] T037 [P] Run `uv run ruff check . && uv run ruff format --check .` over `src/storebro/` and `tests/`; fix any complaints; the result MUST be zero-warning before US1 is considered done (constitution V)
- [X] T038 [P] Run `uv run mypy --strict src/`; fix any type errors; FreeCAD is `ignore_missing_imports`'d in mypy config so external-API calls do not produce false positives (constitution V)
- [X] T039 Run the full suite `uv run pytest -v` and confirm: zero failures; zero unexpected skips; `tests/unit/` green on every host; `tests/geometry/` green where FreeCAD is installed and cleanly skipped where it isn't (constitution V)
- [X] T040 Manual visual signoff: open `/tmp/storebro_hull_signoff_001.FCStd` (from T033) in the FreeCAD GUI, overlay mentally against `docs/references/Alternativ3.JPG`, take a screenshot, and prepare a PR description line of the form `"Visually verified in FreeCAD: <version> on <OS>"` per constitution V
- [X] T041 [P] Update `CLAUDE.md` Commands section if any new CLI invocations were added (none expected for this module; this task is a no-op marker for the audit trail)
- [X] T042 [P] Update `PROJECT-BRIEF.md` Core Modules table to mark `storebro.hull` as "v0.1.0 alpha (this spec)"
- [X] T043 [P] Create `README.md` at the repo root with: project description, `pip install freecad-storebro`, a 5-line quickstart, the supported-FreeCAD-version range (`>=1.1, <2.0`) declared in a section titled "Supported FreeCAD versions" (per constitution principle VII — declaration MUST appear in both `pyproject.toml` AND `README.md`), and a link to `specs/INDEX.md` for project status (analyze remediation A1, CRITICAL)
- [X] T044 [P] `tests/unit/test_hull_leaf_module.py`: import `storebro.hull` and assert that none of `storebro.deck`, `storebro.interior`, `storebro.export`, `storebro.cli` is in `sys.modules` after the import; also AST-walk `src/storebro/hull.py` and assert no `from storebro.deck/interior/export/cli` import statements appear (FR-011, analyze remediation A2)
- [X] T045 [P] `tests/unit/test_hull_public_docstrings.py`: introspect every name in `storebro.hull.__all__`; for each callable, assert `__doc__` is non-empty AND contains at least one `>>>` example line; for each class, do the same for the class docstring (FR-014, analyze remediation A5)

**Final checkpoint**: Spec 001 is done when T039 + T040 + T043 + T044 + T045 are green AND `specs/INDEX.md` is ticked for `001-hull-module`.

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)**: no upstream deps; starts immediately
- **Phase 2 (Foundational)**: needs Phase 1 toolchain; BLOCKS all user-story phases
- **Phase 3 (US1)**: needs Phase 2 (foundational types); US1 is the MVP and gates US2/US3 testing
- **Phase 4 (US2)**: needs Phase 3 (because `build_hull` must exist before SC-001 can be measured); but US2 tests are independent of US3 tests
- **Phase 5 (US3)**: needs Phase 3; independent of US2; can run in parallel with US2 once Phase 3 is done
- **Phase N (Polish)**: needs Phases 1-5

### Per-task dependencies (the important ones)

- T011 → T012 → T013 (all touch `hull.py` or `__init__.py`, sequential)
- T010 → T016 (test depends on the helper)
- T011 → T014, T015 (tests depend on the classes they assert against)
- T012 → T015 (HullParameters tests need the dataclass)
- T013 → all subsequent test tasks (need the public re-exports)
- T017 → T018 → T019 → T020 → T021 → T022 → T023 → T024 → T025 (all touch `hull.py` or `__init__.py`, sequential)
- T024 → T026, T027, T028, T029, T030, T031, T032, T033, T034, T035 (all tests need `build_hull` to exist)
- T039 needs T037, T038, plus all test tasks completed
- T040 needs T033 (the signoff file must exist)

### Within each user story

- Tests are written AFTER implementation in this spec (TDD-flavored but not TDD-strict — geometry tests are infeasible to write before the build_hull pipeline exists). Tests MUST be runnable and green before the story checkpoints.
- Models / dataclasses before functions that consume them.
- Public function before public re-exports.

---

## Parallel Opportunities

### Setup (Phase 1)

- T003, T004, T005 can all run in parallel (different sections of `pyproject.toml`, but a careful merge tool or sequential execution within a single editor pass works fine)

### Foundational (Phase 2)

- T008, T009, T010 all parallel after T007
- T014, T015, T016 all parallel after T011/T012/T013 respectively

### User Story 1 (Phase 3)

- T026, T027, T028, T029, T030 all parallel after T024

### User Story 2 (Phase 4) and User Story 3 (Phase 5)

- All US2 tests (T031, T032, T033) parallel with each other
- All US3 tests (T034, T035) parallel with each other
- US2 and US3 can run in parallel once T024 (build_hull implementation) is done

### Polish (Phase N)

- T036, T037, T038, T041, T042, T043, T044, T045 all parallel

---

## Parallel Example: User Story 1 tests

```bash
# After T025 (build_hull is wired up and re-exported), launch US1 tests together:
uv run pytest tests/geometry/test_hull_default_call.py        # T026
uv run pytest tests/geometry/test_hull_gui_editability.py     # T027
uv run pytest tests/geometry/test_hull_composition.py         # T028
uv run pytest tests/geometry/test_hull_construction_errors.py # T029
uv run pytest tests/geometry/test_hull_topology.py            # T030
# Or just: uv run pytest tests/geometry/ -m requires_freecad -n auto
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1: Setup (`uv sync`, ruff/mypy/pytest configured)
2. Complete Phase 2: Foundational (foundational unit tests green)
3. Complete Phase 3: User Story 1 (geometry tests T026-T030 green)
4. **STOP and VALIDATE**: open the generated `.FCStd` in the FreeCAD GUI, confirm parametric editability
5. Demo: a Python scripter can now compose hulls into their own documents — that's the MVP slice

### Incremental Delivery

1. Setup + Foundational → toolchain green, types importable
2. + User Story 1 → MVP shipped (v0.1.0-alpha hull)
3. + User Story 2 → reference fidelity proven (constitutional principle IV passes its test)
4. + User Story 3 → parametricity + determinism proven (principles I + II pass)
5. + Polish → ruff/mypy/pytest all green, visual signoff captured, ready to merge

### Solo Strategy (this project)

This is a solo OSS project per CLAUDE.md and the project_workflow rule. Direct push to `main` is allowed; no PR ceremony. Each task is committed individually or in small logical groups; tag `v0.1.0-alpha` when T040 is green.

---

## Notes

- `[P]` tasks touch distinct files with no dependency on incomplete work.
- `[Story]` labels (US1, US2, US3) trace each task to its user story for auditability.
- All hull.py-internal implementation tasks are intentionally sequential — same file means serialized writes.
- Tests in `tests/geometry/` are skipped on hosts without FreeCAD; this is by design (R8).
- Spec 001 is done at T040 + register tick; subsequent specs (002-export, 003-deck, etc.) are blocked by this spec.
