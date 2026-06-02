# Tasks: Interior Scale Fix

**Feature dir**: `specs/017-interior-scale-fix/` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**Track**: spec-only (fix; no new entities/state) → `/specify → /clarify → /plan → /tasks → /speckit.analyze → /implement`. No Allium, no TLA+.

**Single production file**: `src/storebro/interior.py`. Tests under `tests/`.

## Conventions

- The fix is atomic: compartments and furniture **must** move to millimetre scale in the same change (US1 + US2 cannot ship independently without leaving the other 1000× off). They are split into phases for clarity, not for independent delivery.
- `[P]` = parallelizable (distinct file, no dependency on an incomplete task).
- Verification gates after each implementation phase: `uv run pytest -m "not requires_freecad"`, `uv run ruff check .`, `uv run mypy src/`; geometry tier (`-m requires_freecad`) on a FreeCAD host.

---

## Phase 1: Setup

- [x] T001 Add the metre→millimetre conversion constant `_M_TO_MM = 1000.0` at module scope in `src/storebro/interior.py` (mirror of `hull._MM_PER_M`), placed in the Constants section near `_OVERLAP_THRESHOLD_M3`. Add a one-line comment stating it is the single conversion authority for the geometry-construction boundary (FR-005).

## Phase 2: Foundational (blocking prerequisite for US1 + US2)

- [x] T002 Decide and document the validator/geometry split in `src/storebro/interior.py`: geometry construction uses `_M_TO_MM` (metres→mm); validation (`_validate_furniture_envelope`) keeps converting furniture-mm down to metres for its height comparison. Rename/repurpose the existing `_MM_TO_UNIT` so its remaining use is unambiguously the *validation* metre-conversion (e.g. keep it only inside `_validate_furniture_envelope`, or replace its uses there with `/ _M_TO_MM`). No `_MM_TO_UNIT` may remain on any geometry-construction path (FR-003, FR-007). Update the section comment block above the furniture builders (currently describing the metre-magnitude convention) to describe the mm convention.

## Phase 3: User Story 1 — Compartment geometry at true mm scale (P1)

**Goal**: Unfurnished compartment boxes build at millimetre scale; GUI properties stay consistent.
**Independent test**: a 2.4 m compartment → `Shape.BoundBox.XLength ≈ 2400 mm`.

- [x] T003 [US1] In `_build_compartment` (`src/storebro/interior.py` ~L806-840) scale geometry to mm: multiply `spec.dimensions.length/width/height` and `spec.position.x/z` (and the derived `half_w`) by `_M_TO_MM` before `Part.makeBox` and `box.translate`. Leave the `obj.Length/Width/Height = spec.dimensions.* * 1000.0` property assignments unchanged — they already read mm and must NOT be double-scaled (FR-001, FR-008).
- [x] T004 [US1] Update the `_box` helper docstring (`src/storebro/interior.py` ~L861) to state its `size`/`origin` are millimetre-magnitude (was "meter-magnitude units"), so furniture callers passing mm are correct.

## Phase 4: User Story 2 — Furniture at true mm scale within its compartment (P1)

**Goal**: Furniture builders emit mm-scale geometry consistent with the corrected compartments; every piece stays inside its compartment envelope.
**Independent test**: furniture bounding boxes lie within the mm-scale compartment envelope; a galley counter top sits ~900 mm above the floor.

- [x] T005 [US2] `_build_berth` (`src/storebro/interior.py` ~L889): use `params.base_height/cushion_thickness/wall_inset` at face value (mm); convert spec-derived `length/width/x0/z0` (metres) via `* _M_TO_MM`. Remove `_MM_TO_UNIT` shrink (FR-002, FR-003).
- [x] T006 [US2] `_build_galley_counter` (~L918): convert the hardcoded `inset = 0.05` m → `50.0` mm (or `0.05 * _M_TO_MM`); use `counter_height/counter_thickness/sink_recess_depth/stove_recess_depth` at face value (mm); convert spec-derived `length/width/x0/z0` via `* _M_TO_MM`. Keep the recess geometry relative (proportions of `length`/`width`) so it auto-scales. Preserve the blind-recess invariant (recess depth < counter thickness).
- [x] T007 [US2] `_build_head_fittings` (~L953): convert hardcoded metre literals (`tl,tw = 0.5,0.4`; `sl,sw,st = 0.4,0.3,0.15`; the `0.1` wall offsets) to mm; use `toilet_height/sink_height` at face value (mm); convert spec-derived `x0/z0/aft_x/half_w` via `* _M_TO_MM`.
- [x] T008 [US2] `_build_salon_furniture` (~L978): convert hardcoded metre literals (`settee_d = 0.5`; `table_top_t = 0.04`; pedestal `0.08`/`0.04`; the `0.1`/`0.05` offsets) to mm; use `seat_height/table_height` at face value (mm); convert spec-derived `x0/z0/width/length/cx` via `* _M_TO_MM`. Keep `table_l,table_w` relative to `length`/`width`.
- [x] T009 [US2] `_build_bulkhead` (~L1009): use `params.thickness` at face value (mm); convert spec-derived `aft_x/width/height/position.z` via `* _M_TO_MM`.

## Phase 5: User Story 3 — Existing guarantees survive (P2)

**Goal**: validation, overlap, manifold, rollback, determinism unchanged.

- [x] T010 [US3] Confirm `_validate_compartment_in_envelope`, `_aabb_intersection_volume`/`_validate_no_overlaps`, and `_validate_furniture_envelope` remain entirely metre-space (no `_M_TO_MM` leaked into them) — they compare layout metres against `hull.parameters` metres (FR-007). Adjust only if T002's `_MM_TO_UNIT` repurposing touched `_validate_furniture_envelope` (keep its metre comparison correct).
- [x] T011 [US3] Confirm the galley manifold guard (`Solids == 1 && isValid()`) in `_build_furnished_compartment` is scale-invariant and still fires at mm scale (no code change expected; verify via T015).

## Phase 6: Tests (FR-011, FR-012, constitution V)

- [x] T012 [P] [US1] Update `tests/geometry/test_interior_berth_salon.py`: in `_within(piece_bb, comp)` scale the spec-derived envelope bounds (`x0`, `z0`, `hw`, `s.dimensions.*`) by 1000 so they compare against the now-mm `piece.Shape.BoundBox` (FR-011).
- [x] T013 [P] [US2] Scan the remaining interior geometry tests (`tests/geometry/test_interior_*`) for absolute-coordinate / absolute-length assertions against metre-magnitude geometry and lift them to mm. Leave scale-agnostic assertions (`Volume > 0`, relative `Volume >= Volume` in `test_interior_galley_counter.py`, `test_interior_alt345_default_fit.py`) unchanged. List each file touched.
- [x] T014 [US1] Add `tests/geometry/test_interior_scale.py` (regression, FR-012/SC-001): build Alternativ1 on a hull+deck, assert the forward-cabin `Shape.BoundBox.XLength` is within ±1% of 2400 mm. Mark `@pytest.mark.requires_freecad`.
- [x] T015 [US3] In `tests/geometry/test_interior_scale.py` add an interior-nests-in-hull check (SC-003): the interior's combined compartment bounding box is contained within `hull.body.Shape.BoundBox`. Also assert a furnished galley counter top sits within ±1% of its configured height above the compartment floor (SC-002 representative check).

## Phase 7: Polish & cross-cutting

- [x] T016 Bump `storebro.__version__` (PATCH) in `src/storebro/__init__.py` and update the version-consistency test (`tests/` — the existing `test_version_consistency`) to match, following the prior spec-only-release precedent.
- [x] T017 Run the full gate: `uv run pytest -m "not requires_freecad"`, `uv run ruff check .`, `uv run mypy src/`. On a FreeCAD host also run `uv run pytest -m requires_freecad` and GUI-eyeball the interior nesting inside the hull (constitution V). Record results in the spec status summary / register history.

## Dependencies

- T001 → everything (constant must exist first).
- T002 → T003–T009 (validator/geometry split must be settled before touching builders).
- T003–T004 (US1) and T005–T009 (US2) are independent of each other **as code** but ship together (atomic scale fix).
- T010–T011 (US3) verify after T003–T009.
- T012–T015 (tests) after the corresponding implementation; T012 and T013 are `[P]` (distinct files).
- T016–T017 last.

## Parallel execution example

```
# After T001 + T002, the per-builder edits touch distinct functions in one file
# (serialize edits to interior.py, but they are logically independent).
# Test files are genuinely parallel:
T012  (test_interior_berth_salon.py)   ┐
T013  (other test_interior_* files)    ┘  run in parallel
```

## Implementation strategy

MVP = the atomic scale fix: T001–T009 brings compartments and furniture to mm scale together. T010–T015 lock in non-regression + the explicit scale guard. T016–T017 release housekeeping. There is no partial-ship: shipping US1 without US2 (or vice versa) leaves half the interior 1000× off, so the whole set lands in one commit.
