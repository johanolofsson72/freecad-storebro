# Tasks: DS Deckhouse Detailing

**Feature**: 023 | **Track**: light | **Spec**: [spec.md](./spec.md)

## Phase 1: Setup
- [x] T001 Baseline: `uv run pytest -m "not requires_freecad"` + ruff + mypy green.

## Phase 2: Deckhouse parameters (US1–US3)
- [x] T002 [US1/2/3] `deck.py` `DsWindowParameters`: add `front_window`, `front_length`, `front_height`, `mullions_per_window`, `mullion_width`, `helm_door`, `helm_door_length`, `helm_door_height`, `helm_door_side` + `__post_init__` validation (positive dims; `helm_door_side in {Port, Starboard}`; `mullions_per_window >= 0`).

## Phase 3: Deckhouse geometry (US1–US3)
- [x] T003 [US1] `deck.py` `_cut_deckhouse_windows` (or a new `_detail_deckhouse`): cut the front-window recess on a YZ datum rotated about Y by `front_rake_angle` at the front-face center (spike pattern); manifold-or-skip gate (roll back the recess if not `Solids==1 && isValid()`); seat a glass pane on the raked face when `glass_panes`. Set `front_window_skipped` accordingly.
- [x] T004 [US2] Add `mullions_per_window` raised vertical `PartDesign::Pad` bosses across each side window opening (on the side face); keep `Solids==1`.
- [x] T005 [US3] Cut the tall helm-door blind `PartDesign::Pocket` in the `helm_door_side` wall; keep `Solids==1`.
- [x] T006 Assert `Solids==1 && isValid()` after the detailing (FR-005); the deckhouse window_count / detailing flags flow into the `Deckhouse` wrapper.

## Phase 4: DS interior (US4)
- [x] T007 [US4] `interior.py`: add `helm` to `_COMPARTMENT_TYPES`; add `HelmParameters` (console_height, console_depth, seat_height) to `FurnitureParameters`; add `_build_helm` furniture builder (console box + seat box, Part::Feature, trim) + dispatch branch.
- [x] T008 [US4] `interior.py`: thread `headroom_budget_m` through `_validate_compartment_in_envelope` (default 1.5 → standard unchanged).
- [x] T009 [US4] `fixtures/DsSaloon.yaml`: the enclosed-saloon layout (forward cabin + head + galley + helm saloon + saloon).
- [x] T010 [US4] `build_interior(..., superstructure_variant="standard"|"ds")`: `"ds"` loads DsSaloon, furnishes it (add DsSaloon to `_FURNISHED_LAYOUTS`), uses the DS headroom budget; `"standard"` byte-identical.

## Phase 5: Unit tests (no FreeCAD)
- [x] T011 [P] [US1-3] Unit: `DsWindowParameters` defaults + each validation rejection.
- [x] T012 [P] [US4] Unit: `HelmParameters` defaults + validation; `helm` in `_COMPARTMENT_TYPES`.
- [x] T013 [P] [US4] Unit: `DsSaloon.yaml` loads + validates (schema, compartment types incl. helm).
- [x] T014 [P] [US4] Unit: `superstructure_variant="standard"` build path unchanged (layout name preserved, no helm); `"ds"` selects DsSaloon.

## Phase 6: Geometry tests (requires_freecad)
- [x] T015 [US1] Geometry: DS deckhouse has the front recess + a front glass pane; `Solids==1 && isValid()`; `front_window=False` → no front recess.
- [x] T016 [US1] Geometry: forced front-recess failure → deterministic skip; deckhouse still valid (`front_window_skipped`).
- [x] T017 [US2] Geometry: `mullions_per_window` bosses present; `Solids==1`; `0` → none.
- [x] T018 [US3] Geometry: helm-door recess present in the chosen side; `Solids==1`; `helm_door=False` → none.
- [x] T019 Geometry (NOBOOL, FR-006): hull + deck-plate identical with vs without the deckhouse detailing.
- [x] T020 Geometry (STL, SC-002): DS deckhouse exports watertight.
- [x] T021 [US4] Geometry: `build_interior(..., superstructure_variant="ds")` builds the DsSaloon furnished (incl. helm console+seat valid solids); `"standard"` unchanged.

## Phase 7: Polish
- [x] T022 Version 1.8.0 -> 1.9.0 (`__init__.py`, `pyproject.toml`, `test_version_consistency`).
- [x] T023 Verify: full unit + ruff + mypy clean; geometry tier on FreeCAD 1.1.1; signoff `.FCStd` via `storebro build --superstructure ds`. Back-compat: all spec 016/019 DS tests pass unchanged (FR-008/SC-005). Run docs/commit text through `humanizer`.

## Notes
- Light track: synchronous geometry + a new interior layout reusing spec 012/013 builders, no state machine → **/tla skipped**.
- Deckhouse stays a FILLED solid with BLIND recesses (user kept this; through-cuts deferred).
- Full DS interior layout absorbed from spec 025 (register rewrite 2026-06-03).
- The front-recess manifold-or-skip gate is deterministic (geometry-only) — no spec 022 arc-loft reproducibility issue (clean rectangular cut).
