# Tasks: Interior Contoured Fittings

**Feature**: 024 | **Track**: light | **Spec**: [spec.md](./spec.md)

## Phase 1: Setup
- [x] T001 Baseline: unit + ruff + mypy green.

## Phase 2: Parameters
- [x] T002 `interior.py`: extend `BerthParameters` (contoured, cushion_segments, seam_gap, cushion_fillet, buttons_per_row, button_rows, button_radius, piping, piping_radius, fold_creases) + validation.
- [x] T003 `SalonParameters` (contoured, seat_fillet + fabric fields) + validation.
- [x] T004 `HeadParameters` (contoured, toilet_fillet, bowl_radius, faucet, faucet_height) + validation.
- [x] T005 `GalleyParameters` (contoured, edge_fillet, fascia, fascia_thickness) + validation.
- [x] T006 `BulkheadParameters` (contoured, corner_fillet, doorway, doorway_width, doorway_height) + validation.

## Phase 3: Helpers
- [x] T007 `interior.py`: `_rounded_box_shape` (clamped fillet, fallback to box), `_cushion_shape` (rounded + cut-sphere buttons + fused piping welt + cut fold grooves), `_finalize_piece` (Part::Feature wrap + manifold-or-box gate, FR-007).

## Phase 4: Builder refits
- [x] T008 [US1] `_build_berth`: segmented contoured cushions (cushion_segments sub-cushions with seam gaps), each via `_cushion_shape`; `contoured=False` → spec 012 boxes.
- [x] T009 [US1] `_build_salon_furniture`: contoured settee seat via `_cushion_shape`; table unchanged.
- [x] T010 [US2] `_build_head_fittings`: rounded pedestal + bowl `fuse` (toilet) + faucet (stem+spout); `contoured=False` → boxes.
- [x] T011 [US3] `_build_galley_counter`: rounded worktop edges + fascia panel; preserve the spec 012 `Solids==1` sink/stove guard.
- [x] T012 [US4] `_build_bulkhead`: filleted vertical edges + rounded-top doorway cut (when tall enough); `contoured=False` → spec 012 box.

## Phase 5: Unit tests
- [x] T013 [P] Unit: each furniture dataclass new-field defaults + validation rejections.
- [x] T014 [P] Unit: `contoured=False` round-trips the dataclasses to spec 012/013 shapes (param-level).

## Phase 6: Geometry tests (requires_freecad)
- [x] T015 [US1] Geometry: berth cushions segmented + each `Solids==1 && isValid()`; settee seat `Solids==1`; buttons/piping present (volume < plain box).
- [x] T016 [US2] Geometry: toilet `Solids==1` with bowl; faucet present.
- [x] T017 [US3] Geometry: galley counter `Solids==1` (manifold guard) with contour + fascia.
- [x] T018 [US4] Geometry: bulkhead `Solids==1` rounded; doorway cut present when tall.
- [x] T019 Geometry (back-compat, FR-008): `contoured=False` furniture matches the spec 012/013 boxes (volume parity).
- [x] T020 Geometry (determinism, FR-011): two furnished builds produce identical furniture volumes (contours reproducible).
- [x] T021 Geometry (STL, SC-002): a furnished interior exports watertight.

## Phase 7: Polish
- [x] T022 Version 1.9.0 -> 1.10.0.
- [x] T023 Verify: full unit + ruff + mypy clean; geometry tier on FreeCAD 1.1.1; all spec 012/013 interior tests pass unchanged (FR-010/SC-005). Run docs/commit text through `humanizer`.

## Notes
- Light track: cosmetic furniture refinement, no state machine → **/tla skipped**.
- Fabric detail (buttons + piping + fold creases) promoted from deferred to in-scope during elicitation.
- All contour ops spiked manifold AND byte-reproducible (no spec 022 arc-loft issue — analytic primitives).
