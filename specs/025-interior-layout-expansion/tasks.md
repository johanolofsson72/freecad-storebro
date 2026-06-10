# Tasks: Interior Layout Expansion

**Feature**: 025-interior-layout-expansion | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

**Scope**: All production code in `src/storebro/interior.py` (+ the `Alternativ5.yaml` fixture, version in `__init__.py`/`pyproject.toml`). Tests in `tests/unit/` and `tests/geometry/`.

**Testing note**: geometry library, NOT interactive UI → the destructive-test analog is invalid-type, out-of-envelope, out-of-half-beam, and byte-identity scenarios (not browser tests). No reproducibility spike needed — all new geometry is analytic Part primitives (the spec 024 byte-reproducible class).

---

## Phase 1: Foundational (blocking prerequisites for all stories)

- [ ] T001 [P] Extend `_COMPARTMENT_TYPES` in `src/storebro/interior.py` with `aft_cabin`, `dinette`, `engine_room`, `wet_locker`, `salon_galley`; add `_FURNISHABLE_TYPES = _COMPARTMENT_TYPES` as the single dispatch+gate source of truth.
- [ ] T002 [P] Add `EngineRoomParameters` and `WetLockerParameters` frozen dataclasses (data-model.md §New parameter dataclasses) with validation; append `engine_room` + `wet_locker` fields to `FurnitureParameters`; export both from `interior.__all__` and `storebro/__init__.py`.
- [ ] T003 Drop the `position.y != 0` reject in `_parse_compartment_entry` (`src/storebro/interior.py`); add the transverse bound to `_validate_compartment_in_envelope`: `abs(y) + width/2 > beam_max/2 → InteriorParameterError` (FR-006/FR-007).
- [ ] T004 Replace the layout-name furnishing gate (`furnished = layout_name in _FURNISHED_LAYOUTS`) with per-compartment dispatch-by-type: a compartment whose type is in `_FURNISHABLE_TYPES` is furnished in any layout; run the furniture-fit validation over every furnishable compartment (FR-002).
- [ ] T005 [P] [Unit] Write `tests/unit/test_interior_compartment_types.py`: the five new types are accepted; an unknown type is rejected; new-type param defaults + validation rejections; `_FURNISHABLE_TYPES` covers every type; the furnish gate no longer depends on layout name (a fake custom-named layout with a furnishable type is marked furnishable).
- [ ] T006 [P] [Unit] Write `tests/unit/test_interior_asymmetric_validation.py`: `position.y != 0` is accepted by the parser; `abs(y)+width/2 <= beam_max/2` passes; `abs(y)+width/2 > beam_max/2` raises `InteriorParameterError` with field `position.y`; `y=0` still valid.

**Checkpoint**: type set + params + validators + the two gate drops exist and are unit-green (no FreeCAD). Geometry stories can proceed.

---

## Phase 2: User Story 1 — Alternativ5 integrated galley-in-salon (P1) 🎯 MVP

**Goal**: a `salon_galley` compartment carries settee+table AND a galley counter; Alt5 fixture uses it.
**Independent test**: `tests/geometry/test_interior_alt5_galley.py` green.

- [ ] T007 [US1] Add the `salon_galley` dispatch in `_build_compartment` (`src/storebro/interior.py`): build `_build_salon_furniture` + `_build_galley_counter`, both fused into the compartment compound; preserve the spec 012 galley manifold guard (`Solids==1`). Extend `_validate_furniture_envelope` for `salon_galley` (salon + galley heights).
- [ ] T008 [US1] Change the Alternativ5 combined compartment in `src/storebro/fixtures/Alternativ5.yaml` from `type: salon` to `type: salon_galley`.
- [ ] T009 [P] [US1] Write `tests/geometry/test_interior_alt5_galley.py`: the Alt5 `salon_galley` compartment is furnished, its compound contains settee/table pieces AND a galley counter; the galley counter is a single valid solid; every piece is `Solids==1`/`isValid()`.

**Checkpoint**: Alt5 shows its galley — MVP deliverable.

---

## Phase 3: User Story 2 — Custom-layout furniture mode (P1)

**Goal**: a custom (non-canonical) layout's compartments are furnished by type, not boxed.
**Independent test**: `tests/geometry/test_interior_custom_furnished.py` green.

- [ ] T010 [US2] Verify/finish the T004 gate drop so a non-canonical layout name furnishes by type (no production change beyond T004 if already general); add a custom YAML fixture under `tests/geometry/fixtures/` (forward_cabin + galley + head) for the test.
- [ ] T011 [P] [US2] Write `tests/geometry/test_interior_custom_furnished.py`: build the custom layout; every furnishable-type compartment has `is_furnished == true`, its body is a `Part::Compound`, the galley compartment has a counter with sink+stove recesses (single solid), and no compartment is a bare box.

---

## Phase 4: User Story 3 — Additional compartment types (P2)

**Goal**: aft_cabin/dinette/engine_room/wet_locker accepted + furnished appropriately.
**Independent test**: `tests/geometry/test_interior_new_types.py` green.

- [ ] T012 [US3] Add the new-type dispatch in `_build_compartment` (`src/storebro/interior.py`): `aft_cabin`→`_build_berth`, `dinette`→`_build_salon_furniture`; new builders `_build_engine_room_fitting` (engine-block-like box, analytic primitives) and `_build_wet_locker` (locker box + `shelf_count` shelves). Extend `_validate_furniture_envelope` to all four new types.
- [ ] T013 [P] [US3] Write `tests/geometry/test_interior_new_types.py`: a layout with one compartment of each new type builds; each is furnished with its fitting (aft_cabin berth, dinette settee/table, engine_room block, wet_locker locker); every piece is `Solids==1`/`isValid()`; an over-tall fitting raises `InteriorParameterError` before geometry.

---

## Phase 5: User Story 4 — Asymmetric layouts (P2)

**Goal**: off-centre compartments + furniture build; transverse bound enforced.
**Independent test**: `tests/geometry/test_interior_asymmetric_geometry.py` green.

- [ ] T014 [US4] Thread `offset_y = spec.position.y * _M_TO_MM` into every furniture builder (`_build_berth`, `_build_galley_counter`, `_build_head_fittings`, `_build_salon_furniture`, `_build_helm`, `_build_bulkhead`, and the new `_build_engine_room_fitting`/`_build_wet_locker`) so furniture centres on the compartment's y; `y=0` stays byte-identical.
- [ ] T015 [P] [US4] Write `tests/geometry/test_interior_asymmetric_geometry.py`: a compartment at `y=0.6` builds with its body + furniture centred near y≈600 mm (port); a starboard `y=-0.7` compartment centres near y≈-700 mm; a compartment with `abs(y)+width/2 > beam_max/2` raises before geometry; and an asymmetric layout with two non-overlapping off-centre compartments still passes the no-overlap validation (FR-013), while two overlapping off-centre compartments are rejected.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T016 Bump version 1.11.0 → 1.12.0 in `src/storebro/__init__.py` and `pyproject.toml`; update the version-consistency test.
- [ ] T017 [P] Write `tests/geometry/test_interior_canonical_byte_identity.py`: Alternativ1–4 and the DS layout produce byte-identical geometry (per-compartment volume + overall shape digest) across the change — guards FR-011/SC-005 (only Alt5 differs).
- [ ] T018 [P] Write `tests/geometry/test_interior_expansion_determinism.py`: two builds each of Alt5, a custom layout, and an asymmetric layout produce byte-identical per-compartment volumes (FR-009/SC-006).
- [ ] T019 Run the gate: `uv run pytest` (unit) + `PYTHONPATH=… uv run pytest -m requires_freecad` (geometry) + `uv run ruff check .` + `uv run mypy src/`. Fix failures. Build a signoff `.FCStd` (`storebro build --layout Alternativ5`) and record its SHA-256.

---

## Dependencies & Execution Order

- **Phase 1 (T001–T006) blocks all stories** — type set, params, validators, gate drops.
- **Stories after Phase 1**: US1 (T007–T009), US2 (T010–T011), US3 (T012–T013), US4 (T014–T015) all touch `_build_compartment`/builders in the same file → serialize production edits, but they have no logical inter-dependency. US4's `offset_y` threading is a cross-cutting edit to all builders — do it after US1/US3 add their builders so all builders get threaded once.
- **Phase 6**: T017 (byte-identity) must run after T014 (offset_y) to prove `y=0` unchanged; T016/T019 last.
- **[P]** marks parallelizable test-writing + independent unit tasks; production edits to `interior.py` are serialized.

## MVP

**US1 (Alt5 galley-in-salon) alone is a shippable increment** — it fixes the one visibly-wrong canonical layout. Phases 1–2 deliver it; Phases 3–5 add custom furnishing, new types, and asymmetry; Phase 6 finalizes.

## Implementation Strategy

Foundational types/params/validators/gate-drops first (Phase 1, unit-green without FreeCAD) → Alt5 MVP (Phase 2) → custom furnishing (Phase 3) → new types (Phase 4) → asymmetric + offset_y (Phase 5) → byte-identity + determinism + version + full verification (Phase 6). One continuous run.
