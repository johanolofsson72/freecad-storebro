---
description: "Task list for the interior module (spec 004)"
---

# Tasks: Interior Module

**Input**: Design documents from `/specs/004-interior-module/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/python-api.md](./contracts/python-api.md), [quickstart.md](./quickstart.md), [spec.allium](./spec.allium)

**Tests**: REQUIRED per constitution V. Every public function has ≥1 geometry test. Each canonical layout + each compartment type has ≥1 test (SC-006). ≥10 invalid-input cases (SC-007). Rollback verified (SC-008). Envelope fit verified (SC-009).

## Format: `[ID] [P?] [Story?] Description with file path`

## Path Conventions

Single Python project, src-layout (continues from spec 001/002/003):
- Library source: `src/storebro/`
- Fixtures: `src/storebro/fixtures/` (new sub-package)
- Tests: `tests/unit/` + `tests/geometry/`

---

## Phase 1: Setup

- [X] T001 Verify spec 001/002/003 scaffolding intact: `src/storebro/{__init__.py,hull.py,export.py,deck.py,_freecad_check.py}`, conftests. `uv run pytest --collect-only` clean.
- [X] T002 Add `PyYAML>=6.0` to `pyproject.toml` `[project.dependencies]` (first third-party Python dependency per research.md R8). Run `uv sync --extra dev` to refresh the lockfile.

---

## Phase 2: Foundational

- [X] T003 Create `src/storebro/fixtures/` directory with empty `__init__.py` (importlib.resources sub-package marker per plan.md).
- [X] T004 Create `src/storebro/interior.py`. Define `InteriorParameterError(ValueError)` with `(source, compartment_name, field, reason)` constructor + message format per data-model §7
- [X] T005 In `src/storebro/interior.py`, define `InteriorConstructionError(RuntimeError)` with `(message, *, layout_name, hull, deck, underlying, detected_version, supported_range)` constructor per data-model §8
- [X] T006 In `src/storebro/interior.py`, define `Position3D`, `Dimensions3D`, `CompartmentSpec`, `LayoutSpec` frozen dataclasses per data-model §1-§4
- [X] T007 In `src/storebro/interior.py`, define `Compartment` and `Interior` frozen dataclasses per data-model §5-§6
- [X] T008 In `src/storebro/interior.py`, implement `_COMPARTMENT_TYPES = {"forward_cabin", "galley", "head", "salon"}` and `_CANONICAL_LAYOUT_NAMES = {"Alternativ1", ..., "Alternativ5"}` module constants
- [X] T009 In `src/storebro/interior.py`, implement `_load_layout(source)` per research.md R2: if source is a canonical name, use `importlib.resources.files("storebro.fixtures") / f"{source}.yaml"`; else treat as filesystem path. Returns raw `dict` from `yaml.safe_load`. Wraps any IO/parse error in `InteriorParameterError(source=..., compartment_name=None, field=None, reason=...)`
- [X] T010 In `src/storebro/interior.py`, implement `_validate_layout_schema(raw_dict, source)` per research.md R2: check `schema_version == 1` (FR-021), `layout_name` non-empty, `source` non-empty, `compartments` is a non-empty list. For each compartment: validate `name` unique, `type` in `_COMPARTMENT_TYPES`, `position.{x,y,z}` and `dimensions.{length,width,height}` all numeric, `dimensions.length > 0` AND `dimensions.width > 0` AND `dimensions.height > 0` (analyze remediation A5), `position.y == 0`. Build and return a `LayoutSpec` dataclass.
- [X] T011 In `src/storebro/interior.py`, implement `_validate_hull(hull)` and `_validate_deck(deck, hull)` per FR-004 + FR-019: hull/deck non-None, non-empty shapes, deck.document is hull.document
- [X] T012 In `src/storebro/interior.py`, implement `_validate_compartment_in_envelope(spec, hull)` per research.md R4: per-axis envelope checks against `hull.parameters.{loa, beam_max, draft, sheer_height_fwd}`
- [X] T013 In `src/storebro/interior.py`, implement `_aabb_intersection_volume(c1, c2)` per research.md R5: compute volume of axis-aligned bounding-box intersection for two compartment specs centered on Y=0
- [X] T014 In `src/storebro/interior.py`, implement `_validate_no_overlaps(compartments)` per FR-012: pairwise check via `_aabb_intersection_volume`; raise `InteriorParameterError` with both compartment names when overlap > 1e-6 m³
- [X] T015 In `src/storebro/interior.py`, implement `_resolve_document(hull, document)` (FR-016, mirrors spec 003)
- [X] T016 In `src/storebro/interior.py`, implement `_ensure_freecad_supported()` wrapping the shared `storebro._freecad_check.ensure_supported_freecad()` and re-raising as `InteriorConstructionError` (matches spec 002/003 pattern)
- [X] T017 In `src/storebro/interior.py`, implement `_rollback(target_doc, added_objects)` per research.md R7
- [X] T018 Update `src/storebro/__init__.py` to re-export `InteriorParameterError`, `InteriorConstructionError` (full public surface comes in later phases). Bump `__version__` to `"0.4.0"`.

### Foundational tests (parallel after T018)

- [X] T019 [P] `tests/unit/test_interior_errors.py`: `issubclass(InteriorParameterError, ValueError)`, `issubclass(InteriorConstructionError, RuntimeError)`, attribute shapes, message formats for both empty-fields and populated-fields cases
- [X] T020 [P] `tests/unit/test_interior_layout_loader.py`: load each canonical name resolves to a fixture path; load nonexistent name raises with `source` populated; load nonexistent path raises; load malformed YAML raises wrapping the yaml.YAMLError; missing schema_version raises; schema_version != 1 raises; missing compartments list raises; missing required field on a compartment raises citing compartment_name + field; duplicate compartment names raise; position.y != 0 raises; unknown compartment type raises; loading the same canonical name twice produces equal LayoutSpec dataclasses (SC-004 deterministic loader, analyze remediation A3); negative or zero `dimensions.length/width/height` raises (FR-020 positivity, analyze remediation A5)
- [X] T021 [P] `tests/unit/test_interior_envelope_validator.py`: parametric checks for each envelope rejection (x<0, x+length>loa, width>beam, z<-draft, z+height>sheer+headroom) using a stub-hull SimpleNamespace
- [X] T022 [P] `tests/unit/test_interior_overlap_detector.py`: AABB intersection math — disjoint pair returns 0; full overlap returns full volume; face-touching pair returns 0; partial overlap returns expected volume; the 1e-6 threshold behavior at boundary
- [X] T023 [P] `tests/unit/test_interior_leaf_dependencies.py`: AST scan of `src/storebro/interior.py` — must import `storebro.hull` and `storebro.deck`; must NOT import `storebro.export` or `storebro.cli`

### Canonical YAML fixtures (parallel; data only)

- [X] T024 [P] Write `src/storebro/fixtures/Alternativ1.yaml` per research.md R1 (4 compartments: forward_cabin, head, galley, salon)
- [X] T025 [P] Write `src/storebro/fixtures/Alternativ2.yaml` per research.md R1 (4 compartments: forward_cabin, galley, head aft, salon)
- [X] T026 [P] Write `src/storebro/fixtures/Alternativ3.yaml` per research.md R1 (4 compartments — the canonical / default layout)
- [X] T027 [P] Write `src/storebro/fixtures/Alternativ4.yaml` per research.md R1 (4 compartments)
- [X] T028 [P] Write `src/storebro/fixtures/Alternativ5.yaml` per research.md R1 (3 compartments — day-cruiser variant)

**Checkpoint**: `uv run pytest tests/unit/test_interior_*.py -v` green. Foundational layer ready for US1 implementation.

---

## Phase 3: User Story 1 - Restorer materializes a canonical layout (P1, MVP)

**Goal**: `build_interior(hull, deck)` produces a 4-compartment Interior on the default hull + deck using Alternativ3.

**Independent Test**: REPL → `from storebro import build_hull, build_deck, build_interior; i = build_interior(build_deck(build_hull()))` → `len(i.compartments) == 4`.

- [X] T029 [US1] In `src/storebro/interior.py`, implement private `_compartment_label(spec, layout_name)` returning `f"Interior_{layout_name}_{ToCamelCase(spec.compartment_type)}"`
- [X] T030 [US1] In `src/storebro/interior.py`, implement `_build_compartment(spec, layout_name, target_doc, added) -> Compartment` per research.md R3: `Part.makeBox` translated to forward-bottom-center, addObject + property bindings + add to `added` tracker. Returns `Compartment(spec, body)`
- [X] T031 [US1] In `src/storebro/interior.py`, implement public `build_interior(hull, deck, layout="Alternativ3", *, document=None, name=None) -> Interior` per contracts/python-api.md: (a) `_ensure_freecad_supported`; (b) `_validate_hull` + `_validate_deck`; (c) `_load_layout` + `_validate_layout_schema`; (d) per-compartment envelope checks + cross-compartment overlap check; (e) `_resolve_document`; (f) `time.perf_counter` start; (g) `added = []`; try block calling `_build_compartment` once per spec; (h) `target_doc.recompute()`; (i) on any non-InteriorParameterError exception → `_rollback` + raise `InteriorConstructionError`; (j) return `Interior(...)`
- [X] T032 [US1] Update `src/storebro/__init__.py` to re-export `build_interior`, `Interior`. Add to `__all__`.

### Tests for US1 (parallel after T032)

- [X] T033 [P] [US1] `tests/geometry/test_interior_default_call.py`: build hull → deck → interior; assert `interior.layout.layout_name == "Alternativ3"`, `len(compartments) == 4`, `interior.document is hull.document`, `0 < interior.build_duration_seconds < 60.0`
- [X] T034 [P] [US1] `tests/geometry/test_interior_default_labels.py`: each of 4 compartment Bodies has label matching `Interior_Alternativ3_<ToCamelCase(type)>`; second build produces auto-numbered labels
- [X] T035 [P] [US1] `tests/geometry/test_interior_document_mismatch.py`: pass an alternative `FreeCAD.newDocument()` as `document=` kwarg → raises `InteriorParameterError("document", ...)`

**Checkpoint**: `uv run pytest -m requires_freecad tests/geometry/test_interior_default*.py tests/geometry/test_interior_document_mismatch.py -v` green.

---

## Phase 4: User Story 2 - Student compares all five layouts (P2)

**Goal**: All five canonical layout names produce successful builds with distinct compartment sets.

**Independent Test**: Loop over the five layout names, build each into a fresh document, assert distinct compartment counts/types between any two.

- [X] T036 [P] [US2] `tests/geometry/test_interior_all_five_layouts.py`: parameterize over `["Alternativ1", "Alternativ2", "Alternativ3", "Alternativ4", "Alternativ5"]`. For each, build hull + deck + interior into a fresh `FreeCAD.newDocument`; assert `interior.layout.layout_name == name`, all compartment Bodies have positive volume, `len(compartments) >= 3` (Alternativ5 is the 3-compartment outlier per research.md R1)
- [X] T037 [P] [US2] `tests/geometry/test_interior_layouts_differ.py`: build two layouts on the same hull/deck shape (in separate documents); assert their compartment counts or per-compartment dimensions differ (proves the YAML data is actually different)
- [X] T038 [P] [US2] `tests/geometry/test_interior_envelope_fit.py` (SC-009): for each of the five canonical layouts, assert every compartment Body's bbox falls fully inside `hull.body.Shape.BoundBox` (with 1 mm slack for FreeCAD rounding). Additionally for each compartment per layout: assert `abs(bbox_length_m - spec.dimensions.length) <= 0.05 * spec.dimensions.length` (FR-003 + SC-001 ±5% fidelity, analyze remediation A1) AND assert `abs((bbox.YMin + bbox.YMax)/2) < 0.001` mm (FR-009 centerline symmetry, analyze remediation A2)

**Checkpoint**: `uv run pytest -m requires_freecad tests/geometry/test_interior_all_five_layouts.py tests/geometry/test_interior_layouts_differ.py tests/geometry/test_interior_envelope_fit.py -v` green.

---

## Phase 5: User Story 3 - Power user supplies custom YAML (P3)

**Goal**: A custom YAML path produces a valid interior; malformed YAML produces clear errors.

**Independent Test**: Write a minimal valid YAML to a tmp path, pass as `layout=`, verify the compartments match. Write a malformed YAML, verify the error names the path and the schema violation.

- [X] T039 [P] [US3] `tests/geometry/test_interior_custom_yaml.py`: write a minimal valid YAML (single forward_cabin) to tmp_path; call `build_interior(hull, deck, layout=str(yaml_path))`; assert `interior.layout.layout_name == "MyTestLayout"`, `len(compartments) == 1`, the compartment's dimensions match the YAML
- [X] T040 [P] [US3] `tests/unit/test_interior_custom_yaml_errors.py`: write YAMLs with various schema violations (missing schema_version, schema_version=99, missing compartments, missing required compartment field, compartment.position.y != 0, unknown compartment type, duplicate names). For each, assert `InteriorParameterError` is raised with `source` set to the YAML path and `field` / `compartment_name` populated where applicable. Contributes to SC-007's ≥10 invalid-input cases.

**Checkpoint**: `uv run pytest tests/unit/test_interior_custom_yaml_errors.py tests/geometry/test_interior_custom_yaml.py -v` green.

---

## Phase N: Polish & Cross-Cutting Concerns

- [X] T041 [P] `tests/geometry/test_interior_determinism.py` (SC-003): two back-to-back `build_interior(hull, deck)` calls in separate docs → per-compartment volume + bbox + topology identical to within 1e-9 relative
- [X] T042 [P] `tests/geometry/test_interior_construction_rollback.py` (SC-008): monkeypatch `_build_compartment` to raise on its 3rd call. Record objects before; build; expect `InteriorConstructionError`; assert document objects after equals before (no orphan compartments)
- [X] T043 [P] `tests/geometry/test_interior_visual_signoff.py`: build hull + deck + interior(Alternativ3); `export_fcstd` to `/tmp/storebro_interior_signoff_004.FCStd`; print SIGNOFF reminder per project pattern
- [X] T044 [P] `tests/unit/test_interior_public_docstrings.py` (FR-014): introspect `storebro.interior.__all__`; assert non-empty `__doc__` + `>>>` example block per public name
- [X] T045 [P] Write `docs/examples/interior_quickstart.py` matching the first three sections of `quickstart.md`
- [X] T046 [P] Run `uv run ruff check src/ tests/ docs/`; fix any complaints
- [X] T047 [P] Run `uv run mypy --strict src/`; fix any type errors
- [X] T048 Full pytest `uv run pytest -v`; confirm green
- [X] T049 Manual visual signoff: open `/tmp/storebro_interior_signoff_004.FCStd` in FreeCAD GUI, eyeball whole-boat (hull + deck + Alternativ3 interior) against `docs/references/Alternativ3.JPG`, capture "Visually verified in FreeCAD: <version> on <OS>" PR description note per constitution V
- [X] T050 [P] Update `README.md`: mark `storebro.interior` v0.4.0-alpha
- [X] T051 [P] Update `PROJECT-BRIEF.md` Core Modules table for interior
- [X] T052 Tick `specs/INDEX.md`: `[/] 004` → `[x] 004`
- [X] T053 [P] `tests/geometry/test_interior_per_compartment_type.py` (SC-006, analyze remediation A4): parameterize over the 4 compartment types `{forward_cabin, galley, head, salon}`. For each type, walk the 5 canonical layouts and assert at least one layout contains a compartment of that type; for the first such compartment found, assert the produced Body has positive volume and the documented FreeCAD property names (`Length`, `Width`, `Height`) bound to its dimensions.

**Final checkpoint**: T048 + T049 + T053 green AND register ticks `[x] 004`.

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)**: needs specs 001/002/003 merged
- **Phase 2 (Foundational)**: needs Phase 1; BLOCKS US1/US2/US3
- **Phase 3 (US1 MVP)**: needs Phase 2 — build_interior end-to-end on the default
- **Phase 4 (US2)**: needs Phase 3 — five-layout coverage
- **Phase 5 (US3)**: needs Phase 3 — custom-YAML coverage
- **Phase N (Polish)**: needs Phases 1-5

### Per-task dependencies

- T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011 → T012 → T013 → T014 → T015 → T016 → T017 → T018 (all touch `interior.py` or `__init__.py`)
- T019, T020, T021, T022, T023 [P] after T018
- T024-T028 [P] after T003 (fixtures depend only on the fixtures dir)
- T020 (loader tests) needs T024-T028 (the fixtures it loads)
- T029 → T030 → T031 → T032 (US1 implementation sequential within interior.py)
- T033, T034, T035 [P] after T032
- T036, T037, T038 [P] after T032 + T024-T028
- T039, T040 [P] after T032
- T041, T042, T043, T044 [P] after T032
- T045 [P] after T032
- T046, T047 [P] before T048
- T048 needs all test tasks complete
- T049 needs T043 (signoff file)
- T050, T051 [P] in Polish
- T052 last

### Parallel Opportunities

- T024-T028 (5 YAML fixtures): all parallel
- T019-T023 (5 unit tests after foundation): all parallel
- T033-T035 (US1 tests): parallel
- T036-T038 (US2 tests): parallel
- T039-T040 (US3 tests): parallel
- T041-T045 (Polish parallel block): parallel
- T046-T047 (ruff + mypy): parallel before T048

---

## Implementation Strategy

### MVP First (US1 only — Alternativ3 default)

1. Setup (T001-T002)
2. Foundational (T003-T028; ALL fixtures land here because tests need them)
3. US1 (T029-T035)
4. STOP + VALIDATE: open `.FCStd` from T043-equivalent in FreeCAD GUI; confirm hull + deck + 4 compartments visible

### Incremental Delivery

1. Setup + Foundational → toolchain green, exception types + loader testable
2. + US1 → Alternativ3 default works end-to-end
3. + US2 → all five layouts proven
4. + US3 → custom YAML proven
5. + Polish → ruff/mypy/pytest green, visual signoff, v0.4.0-alpha shippable

### Solo Strategy

Direct push per `project_workflow` memory. Tag `v0.4.0-alpha` when T049 green + spec register ticked.

---

## Notes

- This spec adds the project's first third-party Python dependency (PyYAML). The pyproject.toml bump must land in T002 before any other foundational task imports `yaml`.
- The 5 YAML fixtures (T024-T028) are pure data — the only "code" review on them is schema conformance. Implementation effort is small but the cross-layout differentiation (US2) depends on getting the data right.
- Total tasks: 52. Bigger than spec 003 (43) because: 5 fixtures + 5 schema-validation tests + 3 user stories with more tests each.
