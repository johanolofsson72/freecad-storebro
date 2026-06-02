# Tasks: Window Glass Panes

**Feature**: 019 | **Track**: full | **Spec**: [spec.md](./spec.md)

## Phase 1: Setup
- [x] T001 Baseline: `uv run pytest -m "not requires_freecad" -q`, ruff, mypy.

## Phase 2: Hull porthole glass (US1)
- [x] T002 [US1] `hull.py`: add `glass_panes: bool=True` + `glass_thickness: float` to `HullGlazingParameters` (validated); add `PortholeGlass` wrapper.
- [x] T003 [US1] `hull.py`: `_build_porthole_glass(...)` — one circular disc body per porthole recess, seated at the outer hull surface, inset by recess_depth, name `Hull_PortholeGlass{side}{seq}`, added to rollback list; wire into `build_hull` glazing branch, gated on `glass_panes`; expose on the glazing result.

## Phase 3: Deck cabin + DS window glass (US1)
- [x] T004 [US1] `deck.py`: add `glass_panes`/`glass_thickness` to the cabin-window + DS-window param paths; add `CabinWindowGlass`/`DeckhouseWindowGlass` wrappers.
- [x] T005 [US1] `deck.py`: `_build_cabin_window_glass(...)` + `_build_deckhouse_window_glass(...)` — one rectangular slab per recess, inset, names `Deck_CabinWindowGlass*`/`Deck_DeckhouseWindowGlass*`, added to rollback; wire into the standard + DS branches; expose on the Deck result.

## Phase 4: Render + exports (US1)
- [x] T006 [US1] `render.py`: role rules `Hull_PortholeGlass`/`Deck_CabinWindowGlass`/`Deck_DeckhouseWindowGlass` → `glass`; add panes to the render-target lists in hull/deck.
- [x] T007 `__init__.py`: re-export new wrappers/params.

## Phase 5: Tests (US1 + US2)
- [x] T008 [P] [US1] Unit: glazing-param validation for the new `glass_panes`/`glass_thickness` fields.
- [x] T009 [P] [US1] Geometry `tests/geometry/test_window_glass_panes.py`: default hull → 1 disc per porthole, each `Solids==1`+valid; standard deck → 1 slab per cabin window; DS deck → 1 slab per deckhouse window; host hull/trunk/deckhouse still `Solids==1` + STL ok; panes resolve to `glass` role.
- [x] T010 [P] [US2] Geometry: panes off → no pane bodies + host solids unchanged + STL ok; `count_per_side=0` → no panes.

## Phase 6: Polish
- [x] T011 Version 1.4.0 → 1.5.0 (`__init__.py`, `pyproject.toml`, version test).
- [x] T012 Full verify on FreeCAD 1.1.1 + ruff + mypy.

## Notes
- Full track; /tla skipped (additive synchronous geometry, no state machine/concurrency).
- Panes are additive (never boolean the host) → manifold by construction.
