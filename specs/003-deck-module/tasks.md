---
description: "Task list for the deck module (spec 003)"
---

# Tasks: Deck Module

**Input**: Design documents from `/specs/003-deck-module/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/python-api.md](./contracts/python-api.md), [quickstart.md](./quickstart.md), [spec.allium](./spec.allium)

**Tests**: REQUIRED per constitution V. Every public function + every sub-Body has at least one geometry test (SC-006). ≥7 invalid-input cases (SC-007). Rollback verified by one forced-failure test (SC-008). Sheer alignment verified by one explicit test (SC-009).

**Organization**: Tasks grouped by user story. Implementation tasks that touch the same file (`src/storebro/deck.py`) are sequential. `[P]` only marks tasks on distinct files with no dependency on incomplete work.

## Format: `[ID] [P?] [Story?] Description with file path`

## Path Conventions

Single Python project, src-layout (continues from spec 001/002):
- Library source: `src/storebro/`
- Tests: `tests/unit/` (no FreeCAD), `tests/geometry/` (marker `requires_freecad`)
- Examples: `docs/examples/`

---

## Phase 1: Setup

- [X] T001 Verify spec 001 + spec 002 scaffolding intact: `src/storebro/{__init__.py,hull.py,export.py,_freecad_check.py}`, `tests/conftest.py`, `tests/geometry/conftest.py`. `uv run pytest --collect-only` clean.

---

## Phase 2: Foundational

**Purpose**: Public exception classes, the `DeckParameters` dataclass, the six sub-Body wrapper dataclasses, the `Deck` aggregate, and the shared helpers (`_sample_hull_sheer`, `_RollbackTracker`). All US1/US2/US3 work depends on these.

- [X] T002 Create `src/storebro/deck.py`. Define `DeckParameterError(ValueError)` and `DeckConstructionError(RuntimeError)` at the top per data-model §4/§5
- [X] T003 In `src/storebro/deck.py` (after T002), define `DeckParameters` as `dataclass(frozen=True)` with the 14 fields, defaults per research.md R1, `REFERENCE_STOREBRO_DECK_RC34_1972: ClassVar` constant, `__post_init__` running `_validate_deck_parameters` (per-field positivity + windshield_rake range + intra-deck `hardtop_overhang_fwd + aft < hardtop_length`)
- [X] T004 In `src/storebro/deck.py`, define the six sub-Body wrapper dataclasses (`DeckPlate`, `CabinTrunk`, `Windshield`, `Hardtop`, `HardtopPillars`, `Railings`) as frozen dataclasses per data-model §2
- [X] T005 In `src/storebro/deck.py`, define `Deck` as `dataclass(frozen=True)` with all 11 fields (parameters, hull, document, label, build_duration_seconds + 6 sub-Body fields) per data-model §3
- [X] T006 In `src/storebro/deck.py`, implement private `_validate_hull(hull)` that checks `hull is not None`, `hull.body.Shape` is non-null/non-empty (raise `DeckParameterError("hull", None, "must have a non-empty Shape")` otherwise)
- [X] T007 In `src/storebro/deck.py`, implement private `_validate_cross_hull_constraints(hull, parameters)` per FR-004 + FR-012: cabin_trunk_length < hull.loa, cabin_trunk_fwd_offset + cabin_trunk_length <= hull.loa, cabin_trunk_width + 2*deck_side_walkway <= hull.beam_max. Raise `DeckParameterError` with cross-field key
- [X] T008 In `src/storebro/deck.py`, implement private `_resolve_document(hull, document)` per FR-016 + research.md R4: if document is None return hull.document; if document is hull.document return it; else raise `DeckParameterError("document", None, "must equal hull.document for cross-module consistency")`
- [X] T009 In `src/storebro/deck.py`, implement private `_ensure_freecad_supported()` that wraps `storebro._freecad_check.ensure_supported_freecad()` and re-raises as `DeckConstructionError` (matching spec 002's pattern, duck-typed on `detected_version` / `supported_range` attributes)
- [X] T010 In `src/storebro/deck.py`, implement private `_sample_hull_sheer(hull) -> list[tuple[float,float,float]]` per research.md R8: walk `hull.body.Shape.Faces`, find the topmost face (max Z, outward normal +Z), intersect with Y-Z planes at 5 station X positions, return the highest-Y point per station
- [X] T011 In `src/storebro/deck.py`, implement private `_rollback(target_doc, added_objects)` per research.md R7: iterate `added_objects` in reverse, call `target_doc.removeObject(obj.Name)` with `contextlib.suppress(Exception)`, then `target_doc.recompute()`
- [X] T012 Update `src/storebro/__init__.py` to re-export `DeckParameterError`, `DeckConstructionError`, `DeckParameters` (sub-Body wrappers + `Deck` re-exports come in later phases). Bump `__version__` to `"0.3.0"`
- [X] T013 [P] `tests/unit/test_deck_errors.py`: `issubclass(DeckParameterError, ValueError)`, `issubclass(DeckConstructionError, RuntimeError)`, attribute shapes, message formats. ≥5 invalid input cases (toward SC-007's 7 minimum)
- [X] T014 [P] `tests/unit/test_deck_parameters.py`: defaults match REFERENCE constant, per-field positivity rejections, angular-range rejections (windshield_rake), intra-deck cross-field rejection (hardtop overhang ≥ length), frozen behavior, hashable
- [X] T015 [P] `tests/unit/test_deck_leaf_dependencies.py`: AST scan of `src/storebro/deck.py` verifies `from storebro.hull` import is present, NO `from storebro.{interior,export,cli}` imports (FR-011)

**Checkpoint**: `uv run pytest tests/unit/test_deck_*.py -v` green.

---

## Phase 3: User Story 1 - Scripter mounts a deck on a hull (P1, MVP)

**Goal**: `build_deck(build_hull())` returns a Deck whose six sub-Bodies appear in the hull's document.

**Independent Test**: REPL → `from storebro import build_hull, build_deck; d = build_deck(build_hull())` → `len(d.document.Objects)` includes 6 new Bodies beyond the hull's contribution.

### Implementation (sequential, same file `src/storebro/deck.py`)

- [X] T016 [US1] Implement private `_build_deck_plate(hull, parameters, target_doc, added) -> DeckPlate` per research.md R2: build a sketch from `_sample_hull_sheer(hull)` points, close, pad downward by `parameters.deck_plate_thickness`. Append the created Body + sketch to `added`. Bind `DeckPlateThickness` as an `App::PropertyLength` on the Body for GUI editing (FR-007, analyze remediation A1). Return the wrapper.
- [X] T017 [US1] Implement private `_build_cabin_trunk(hull, parameters, deck_plate, target_doc, added) -> CabinTrunk` per research.md R2: rounded-rect sketch on X-Y plane at deck plate top with fillet radius `cabin_trunk_corner_radius`, pad upward by `cabin_trunk_height`. Bind `TrunkLength`, `TrunkWidth`, `TrunkHeight`, `CornerRadius` as `App::PropertyLength` properties on the Body for GUI editing (FR-007, analyze remediation A1).
- [X] T018 [US1] Implement private `_build_windshield(hull, parameters, cabin_trunk, target_doc, added) -> Windshield`: trapezoid sketch raked aft by `windshield_rake`, padded for thickness, mirrored about centerline. Bind `WindshieldRake` as an `App::PropertyAngle` on the Body for GUI editing (FR-007, analyze remediation A1).
- [X] T019 [US1] Implement private `_build_hardtop(hull, parameters, cabin_trunk, target_doc, added) -> Hardtop`: rounded-rect at cabin_trunk_top + `hardtop_height`, padded by a small internal slab thickness. Bind `HardtopLength`, `HardtopHeight`, `HardtopOverhangFwd`, `HardtopOverhangAft` as `App::PropertyLength` properties on the Body (FR-007, analyze remediation A1).
- [X] T020 [US1] Implement private `_build_hardtop_pillars(hull, parameters, hardtop, deck_plate, target_doc, added) -> HardtopPillars`: two `Part::Cylinder` instances at the hardtop's aft corners (port/starboard symmetric), combined into a `Part::Compound` (v0.3.0-alpha — the PartDesign equivalent is tracked alongside spec 001's FR-006 v0.2.0 upgrade per analyze remediation A2). Bind `PillarDiameter` as an `App::PropertyLength` on the Compound (FR-007, analyze remediation A1).
- [X] T021 [US1] Implement private `_build_railings(hull, parameters, deck_plate, target_doc, added) -> Railings`: `Part::Pipe` swept around the deck plate's perimeter offset, at `railing_height` above deck plate, with internal-constant cross-section diameter. Bind `RailingHeight` as an `App::PropertyLength` on the Body (FR-007, analyze remediation A1).
- [X] T022 [US1] Implement public `build_deck(hull, parameters=None, *, document=None, name="Deck") -> Deck` per contracts/python-api.md: (a) `_ensure_freecad_supported()`; (b) `_validate_hull(hull)`; (c) coerce `parameters or DeckParameters()` (dataclass post-init already validated); (d) `_validate_cross_hull_constraints(hull, parameters)`; (e) `target_doc = _resolve_document(hull, document)`; (f) `time.perf_counter()` start; (g) `added: list = []`; try block calling `_build_deck_plate` → `_build_cabin_trunk` → `_build_windshield` → `_build_hardtop` → `_build_hardtop_pillars` → `_build_railings` (passing `added` to each); (h) `target_doc.recompute()`; (i) on any non-DeckParameterError exception → `_rollback(target_doc, added)` then raise `DeckConstructionError(parameters=parameters, hull=hull, underlying=exc)`; (j) return `Deck(...)`
- [X] T023 [US1] Update `src/storebro/__init__.py` to re-export `build_deck`, `Deck`. Add to `__all__`.

### Tests for US1 (parallel, distinct files; run after T023)

- [X] T024 [P] [US1] `tests/geometry/test_deck_default_call.py`: build hull → build deck → assert returned Deck has all 6 sub-Body fields non-None, `0 < build_duration_seconds < 45.0` (SC-002), `deck.document is hull.document`, each sub-Body Body has volume > 0
- [X] T025 [P] [US1] `tests/geometry/test_deck_default_labels.py`: each of the 6 Bodies has label `Deck_<Element>` per FR-017; second build_deck call produces `Deck001_<Element>` labels
- [X] T026 [P] [US1] `tests/geometry/test_deck_document_mismatch.py`: pass an alternative FreeCAD.newDocument as `document=` kwarg → raises `DeckParameterError("document", ...)` (FR-016)

**Checkpoint**: `uv run pytest -m requires_freecad tests/geometry/test_deck_default_*.py tests/geometry/test_deck_document_*.py -v` green.

---

## Phase 4: User Story 2 - Restorer renders canonical Storebro silhouette (P2)

**Goal**: Default deck on default hull matches RC34 1972 reference within ±1% on citation-grade dimensions.

**Independent Test**: `build_deck(build_hull())` → bbox dimensions of `CabinTrunk`, `Hardtop`, `Railings` Bodies match REFERENCE constants within ±1%.

### Tests for US2 (parallel)

- [X] T027 [P] [US2] `tests/geometry/test_deck_default_dimensions.py`: per FR-003 + SC-001, default deck's cabin trunk bbox length within ±1% of `DeckParameters.REFERENCE_STOREBRO_DECK_RC34_1972["cabin_trunk_length"]`; hardtop length within ±1%; railing height within ±1%. Three separate assertions for the three citation-grade dimensions
- [X] T028 [P] [US2] `tests/geometry/test_deck_sheer_alignment.py` (SC-009): sample hull sheer Z at 5 stations; sample deck plate underside Z at the same 5 stations; assert each pair differs by < 1e-6 m
- [X] T029 [P] [US2] `tests/geometry/test_deck_visual_signoff.py`: build hull + deck, `export_fcstd` to `/tmp/storebro_deck_signoff_003.FCStd`, print the SIGNOFF reminder per spec 001's pattern

**Checkpoint**: `uv run pytest -m requires_freecad tests/geometry/test_deck_default_dimensions.py tests/geometry/test_deck_sheer_alignment.py -v` green.

---

## Phase 5: User Story 3 - Student studies parametrics (P3)

**Goal**: Every named deck parameter, when changed by ±10%, produces a measurable change in the corresponding sub-Body dimension.

### Tests for US3 (parallel)

- [X] T030 [P] [US3] `tests/geometry/test_deck_parametricity.py`: parameterize over the 14 named params. For each, build hulls + decks at default and at default ±10% (clamped to valid ranges + cross-hull constraints), assert the corresponding measured dimension changes in the documented direction (SC-004)
- [X] T031 [P] [US3] `tests/geometry/test_deck_determinism.py`: two back-to-back `build_deck(hull, params)` calls in separate documents → per sub-Body, volume + bbox + topology counts identical to within 1e-9 relative (SC-003)
- [X] T032 [P] [US3] `tests/geometry/test_deck_symmetric.py`: each of 6 Bodies has bbox YMin / YMax symmetric about 0 within 1 mm (FR-009)

---

## Phase N: Polish & Cross-Cutting Concerns

- [X] T033 [P] `tests/geometry/test_deck_construction_rollback.py` (SC-008): monkeypatch `_build_hardtop` to raise after `_build_deck_plate`, `_build_cabin_trunk`, `_build_windshield` already succeeded. Record document object names before the call. Call `build_deck`. Assert `DeckConstructionError` raised, AND document objects list after the call equals the list before (no orphan Bodies, no partial geometry)
- [X] T034 [P] `tests/unit/test_deck_public_docstrings.py` (FR-014): introspect `storebro.deck.__all__`; for each public name assert non-empty `__doc__` containing a `>>>` example block
- [X] T035 [P] `tests/unit/test_deck_parameters_cross_hull_helper.py`: unit-test `_validate_cross_hull_constraints` directly with a stub hull-like object (Mock with `.parameters.loa`, `.parameters.beam_max` attributes) — covers the cross-field validation logic without needing FreeCAD
- [X] T036 [P] Write `docs/examples/deck_quickstart.py` matching the first three sections of `quickstart.md`
- [X] T037 [P] Run `uv run ruff check src/ tests/ docs/`; fix any complaints
- [X] T038 [P] Run `uv run mypy --strict src/`; fix any type errors
- [X] T039 Full pytest run `uv run pytest -v`; confirm all unit tests green, geometry tests cleanly skip without FreeCAD, no unexpected failures
- [X] T040 Manual visual signoff: open `/tmp/storebro_deck_signoff_003.FCStd` in FreeCAD GUI, eyeball against docs/references/, capture "Visually verified in FreeCAD: <version> on <OS>" PR description line per constitution V
- [X] T041 [P] Update `README.md`: mark `storebro.deck` as v0.3.0-alpha in the Module table
- [X] T042 [P] Update `PROJECT-BRIEF.md` Core Modules table to mark `storebro.deck` as "v0.3.0-alpha (this spec)"
- [X] T043 Tick `specs/INDEX.md`: change spec 003 marker from `[/]` to `[x]`

**Final checkpoint**: T039 + T040 green AND specs/INDEX.md ticks `[x] 003`.

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)**: needs specs 001 + 002 merged
- **Phase 2 (Foundational)**: needs Phase 1; BLOCKS US1/US2/US3
- **Phase 3 (US1 MVP)**: needs Phase 2; provides the MVP — `build_deck()` works
- **Phase 4 (US2)**: needs Phase 3; reference-fidelity tests
- **Phase 5 (US3)**: needs Phase 3; parametricity + determinism tests
- **Phase N (Polish)**: needs all of US1-US3 done

### Per-task dependencies

- T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011 → T012 (all touch `deck.py` or `__init__.py`)
- T013, T014, T015 [P] after T012
- T016 → T017 → T018 → T019 → T020 → T021 → T022 → T023 (US1 implementation sequential within `deck.py`)
- T024, T025, T026 [P] after T023
- T027, T028, T029 [P] after T023
- T030, T031, T032 [P] after T023
- T033, T034, T035, T036 [P] in Polish; T037, T038 [P] before T039; T040 needs T029 (the .FCStd file)

---

## Parallel Opportunities

### Foundational

- T013, T014, T015 parallel after T012

### US1 / US2 / US3

- T024, T025, T026 (US1) all parallel after T023
- T027, T028, T029 (US2) all parallel after T023
- T030, T031, T032 (US3) all parallel after T023

### Polish

- T033, T034, T035, T036, T037, T038, T041, T042 all parallel
- T039 sequential after the test/quality-gate group
- T040 sequential after T039 + T029 (which produces the .FCStd)

---

## Implementation Strategy

### MVP First (US1)

1. Setup (T001)
2. Foundational (T002–T015)
3. US1 (T016–T026)
4. STOP + VALIDATE: open `.FCStd` from T029-equivalent (or just from a script) in FreeCAD GUI; confirm hull + 6 deck Bodies appear

### Incremental Delivery

1. Setup + Foundational → toolchain green, types importable
2. + US1 → MVP, scripter can build deck on hull
3. + US2 → reference fidelity proven
4. + US3 → parametricity + determinism proven
5. + Polish → ruff/mypy/pytest green, visual signoff, v0.3.0-alpha shippable

### Solo Strategy

Per `project_workflow` memory: solo, direct-push. Commit at each phase checkpoint; tag `v0.3.0-alpha` when T040 is green and the spec register ticks `[x] 003`.

---

## Notes

- `[P]` tasks touch distinct files with no dependency on incomplete work.
- All `src/storebro/deck.py` tasks are sequential — same file.
- `tests/geometry/test_deck_*.py` skip cleanly without FreeCAD on PATH (matches spec 001/002 pattern).
- Spec 003 is the first non-leaf module; the leaf-dependency test (T015) is the FR-011 enforcement.
- Rollback discipline (SC-008) is verified by exactly one forced-failure test (T033); the implementation in T022 must thread an `added: list` accumulator through every helper.
