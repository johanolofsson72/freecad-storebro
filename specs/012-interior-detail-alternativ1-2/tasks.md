# Tasks: Interior Detail — Alternativ1 & 2

**Input**: Design documents from `specs/012-interior-detail-alternativ1-2/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/python-api.md

**Tests**: REQUIRED — constitution V + spec.md Success Criteria. Functional coverage (≥1 test per builder) + destructive validation across the 6 attack categories.

> **Verification status (2026-05-29):** FreeCAD is **not installed on the implementation host**, so the `requires_freecad` geometry tier + GUI signoff are **WRITTEN but PENDING execution on a FreeCAD 1.1+ host**. Lower boolean risk than spec 011 (only the galley counter uses one `Part.Cut`, into an axis-aligned box). Verified locally: unit tests, `ruff check src/ tests/`, `mypy --strict src/`. This is the third consecutive spec whose geometry tier is unverified here — run `pytest -m requires_freecad` for specs 010–012 before tagging.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable; **[Story]**: US1 (berth+salon), US2 (galley), US3 (head+bulkhead+Alt2)

---

## Phase 1: Setup

- [x] T001 Bump version: `version = "1.0.6"` in `pyproject.toml`, `__version__ = "1.0.6"` in `src/storebro/__init__.py`, and update `tests/unit/test_version_consistency.py` to `1.0.6`.

## Phase 2: Foundational (BLOCKING)

- [x] T002 In `src/storebro/interior.py`, add the 5 furniture parameter dataclasses + `FurnitureParameters` composite (data-model §1) with `__post_init__` raising `InteriorParameterError`. Update `interior.__all__`.
- [x] T003 In `src/storebro/interior.py`, extend the `Compartment` wrapper with `furniture: tuple[Any, ...]` + `is_furnished: bool` (data-model §2). Update `build_interior` signature with `parameters_furniture` kwarg (data-model §3); resolve `parameters_furniture or FurnitureParameters()`.
- [x] T004 Update `src/storebro/__init__.py` imports + `__all__` (alphabetical) to export the 6 new dataclasses. Verify no new cross-module imports.
- [x] T005 [P] Unit tests per dataclass validation branch: `tests/unit/test_berth_parameters.py`, `test_galley_parameters.py`, `test_head_parameters.py`, `test_salon_parameters.py`, `test_bulkhead_parameters.py`, `test_furniture_parameters.py`. Cover positivity, recess<thickness, non-negative counts, composite default_factory independence.

## Phase 3: User Story 1 — Furnished forward cabin & salon (P1) 🎯 MVP

**Goal**: berth+cushion in forward_cabin, seating+table in salon, for Alt1.

**Independent test**: `build_interior(h,d,"Alternativ1")` → forward cabin has berth+cushion, salon has settee+table, all within envelope.

- [x] T006 [US1] In `interior.py`, implement `_build_berth(spec, params, target_doc, added)` — base box + `cushion_count` cushion boxes (`Part.makeBox` + translate), inset `wall_inset`, within the compartment envelope. Returns the furniture bodies.
- [x] T007 [US1] In `interior.py`, implement `_build_salon_furniture(spec, params, target_doc, added)` — settee box + table (top + pedestal), within envelope.
- [x] T008 [US1] In `interior.py`, add the per-type dispatch + Alt1/Alt2 gate in `build_interior`: when furnished, build per-type furniture + bulkhead, wrap as a `Part::Compound` for the compartment `body`; populate `Compartment.furniture` + `is_furnished`. Envelope guards (raise `InteriorParameterError`).
- [x] T009 [P] [US1] Geometry test `tests/geometry/test_interior_berth_salon.py`: Alt1 forward cabin has berth+cushion bodies within envelope; salon has settee+table; cushion sits on top of the berth base.

## Phase 4: User Story 2 — Galley with worktop cutouts (P2)

**Goal**: galley counter with blind sink + stove recesses, stays manifold.

**Independent test**: Alt1 galley has a counter with sink+stove recesses; counter `Solids == 1`.

- [x] T010 [US2] In `interior.py`, implement `_build_galley_counter(spec, params, target_doc, added)` — worktop `Part.makeBox`; sink + stove recesses via `Part.Cut` of shallow boxes (depth `< counter_thickness`); `cutouts_enabled=False` → plain counter. Returns the (single-solid) counter body.
- [x] T011 [US2] In `interior.py`, add the galley counter manifold assertion (`len(Solids)==1`, `isValid()`) raising `InteriorConstructionError` (FR-007); recess-depth guard raises `InteriorParameterError`. Wire galley into the dispatch (T008).
- [x] T012 [P] [US2] Geometry test `tests/geometry/test_interior_galley_counter.py`: Alt1 galley counter has 2 recesses, `Solids == 1`, `isValid()`; `cutouts_enabled=False` → no recesses; recess≥thickness rejected.

## Phase 5: User Story 3 — Head, bulkheads, Alternativ2 (P3)

**Goal**: head toilet+sink, bulkheads, full Alt2 coverage.

**Independent test**: Alt1 head has toilet+sink; bulkheads exist; Alt2 furnished by the same builders.

- [x] T013 [US3] In `interior.py`, implement `_build_head_fittings(spec, params, target_doc, added)` — toilet (pedestal+bowl boxes) + sink box, within envelope.
- [x] T014 [US3] In `interior.py`, implement `_build_bulkhead(spec, params, target_doc, added)` — thin box at the compartment aft boundary spanning width/height. Wire head + bulkhead into the dispatch.
- [x] T015 [P] [US3] Geometry test `tests/geometry/test_interior_head_bulkhead.py`: Alt1 head has toilet+sink within envelope; each compartment has a bulkhead.
- [x] T016 [P] [US3] Geometry test `tests/geometry/test_interior_alt2_furnished.py`: Alt2 produces furnished compartments via the same builders (berth/galley/head/salon all present).

## Phase 6: Cross-cutting + destructive + signoff

- [x] T017 Geometry test `tests/geometry/test_interior_furniture_default_call.py`: default Alt1 build furnishes all 4 compartments, no error (SC-001).
- [x] T018 Geometry test `tests/geometry/test_interior_gate.py`: Alt3/4/5 compartments remain single boxy `Part::Feature` (unfurnished), no error (SC-006, FR-011).
- [x] T019 Geometry test `tests/geometry/test_interior_furniture_determinism.py`: two Alt1 builds → identical furniture volumes (SC-004).
- [x] T020 Geometry test `tests/geometry/test_interior_furniture_rollback.py`: inject a failure mid-furniture-build → document restored to pre-call state (FR-012, SC-005).
- [x] T021 Geometry test `tests/geometry/test_interior_furniture_zero_counts.py`: zero cushions / galley cutouts disabled build the rest, no error (FR-010).
- [x] T022 Geometry test `tests/geometry/test_interior_stl_watertight.py`: `export_stl` of a furnished Alt1 model still yields a watertight mesh (SC-002).
- [x] T023 [P] Destructive unit tests in `tests/unit/test_furniture_destructive_validation.py`: 6 attack categories — invalid (negative/zero), boundary (recess == thickness, recess just over), oversized vs envelope (in build_interior, geometry tier where envelope needed), zero-count no-ops. ≥8 scenarios.
- [x] T024 Update existing interior tests that assert exactly N boxy bodies for Alt1/Alt2: `tests/geometry/test_interior_*` + any unit test asserting compartment body is a single box (expected behavior change per spec Assumptions). Alt3-5 assertions stay valid.
- [x] T025 [P] Update `tests/unit/test_interior_public_docstrings.py` (new public names need one-line docstrings with `>>>` examples); confirm `test_interior_*` leaf-dependency tests still green.
- [x] T026 Geometry visual-signoff test `tests/geometry/test_interior_furniture_visual_signoff.py`: produce `tests/fixtures/signoff/storebro_v1_0_6_signoff.FCStd` (Alt1 + deck + hull), record SHA-256, assert reproducible.
- [x] T027 Run the full gate: `uv run pytest`, `uv run ruff check src/ tests/`, `uv run mypy src/`. Fix failures. Then `graphify update .`.

---

## Dependencies & execution order

- Phase 1 → 2 → 3 (MVP) → 4 → 5 → 6.
- Phase 2 (T002–T005) BLOCKS all stories. T008 (dispatch + gate) is the integration point; T011/T014 extend the dispatch (sequential within build_interior).
- [P] test tasks touch distinct new files.

## MVP scope

US1 (berth + salon for Alt1) is the shippable increment — the largest, most recognizable furniture.

## Implementation strategy

Land Phase 1+2, then US1 (berth+salon) end-to-end, then US2 (galley + manifold guard), then US3 (head+bulkhead+Alt2), then cross-cutting/destructive/signoff. Keep the rollback list inclusive of every added body.
