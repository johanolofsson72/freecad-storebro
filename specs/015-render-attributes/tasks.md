# Tasks: Render Attributes (Colors & Materials)

**Input**: Design documents from `specs/015-render-attributes/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/render-api.md

**Tests**: INCLUDED — constitution V mandates pytest (incl. geometry property tests) + ruff + mypy --strict on every change.

**Track**: spec-only (cosmetic). No `/allium`, no `/tla`. FreeCAD 1.1.1 runs on this host via `PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib`, so the geometry tier executes here.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable (different files, no incomplete deps)

---

## Phase 1: Setup

- [x] T001 Confirm FreeCAD geometry tier runs on this host: `PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib uv run pytest -m requires_freecad -q` collects (baseline green from spec 014: 917 passed) — record baseline count.

## Phase 2: Foundational (BLOCKING — the palette + applier all stories depend on)

- [x] T002 Create `src/storebro/render.py` with: `RenderAttribute` frozen dataclass (`color: tuple[float,float,float,float]`, `material: str`); module-level `PALETTE: dict[str, RenderAttribute]` covering roles `hull, superstructure, frame, glass, trim, metal, bulkhead, engine, steel, bronze, DEFAULT` per data-model.md (glass alpha < 1.0); a private `_ROLE_RULES` ordered (most-specific-first) label→role table; `role_for_label(label: str) -> str` (pure, no FreeCAD import); and `apply_render_attributes(objects, *, enabled: bool = True) -> int`. The applier sets `App::PropertyColor` `"ShapeColor"` + `App::PropertyMaterial` `"ShapeMaterial"` (group `"Render"`, added only if absent) and, when `obj.ViewObject is not None`, mirrors `ShapeColor`/`ShapeAppearance` + `Transparency = round((1-alpha)*100)`. Never touches `.Shape`. Module-level imports must not hard-require FreeCAD (defer `import FreeCAD`/`Part` to inside the applier so `role_for_label`/`PALETTE` are unit-testable without FreeCAD).
- [x] T003 Export `RenderAttribute`, `PALETTE`, `role_for_label`, `apply_render_attributes` from `src/storebro/__init__.py` (`__all__`) and bump `__version__` `"1.1.0"` → `"1.2.0"`.
- [x] T004 [P] Unit tests `tests/unit/test_render_palette.py` (no FreeCAD): contract invariants 1–3 and 7–8 — palette covers all required roles incl. `DEFAULT`; `glass` alpha < 1.0; every color channel ∈ [0,1] and material non-empty; `role_for_label` most-specific-first (`Deck_WindshieldGlass`→`glass`, `Deck_Windshield`→`frame`, `Deck_Rubrail_port`→`trim`, `Deck_Railings_port`→`metal`, `Propulsion_Propeller`→`bronze`, `HullBody`→`hull`); unknown label → `DEFAULT`.
- [x] T005 [P] Update `tests/unit/test_version_consistency.py` to assert `1.2.0`.

## Phase 3: User Story 1 — Built model looks like a Storebro (Priority: P1) 🎯 MVP

**Goal**: Every shape-bearing body produced by a default build carries its role color + material.

**Independent test**: Build a layout, assert each top-level body reports its expected `ShapeColor`/`ShapeMaterial`; verify persistence across save/reload.

- [x] T006 [US1] Add `apply_render_attributes: bool = True` kwarg to `build_hull` in `src/storebro/hull.py`; when true, call `render.apply_render_attributes([body], enabled=True)` on the top-level `HullBody` before returning the `Hull` aggregate.
- [x] T007 [US1] Add `apply_render_attributes: bool = True` kwarg to `build_deck` in `src/storebro/deck.py`; collect the top-level objects (deck plate, cabin trunk, windshield, windshield glass, hardtop, hardtop pillars compound, railings compound, rubrail compound, bow pulpit, anchor locker, cleats compound, lifelines compound) and apply when true. Color the compound wrappers (not per-side sub-bodies).
- [x] T008 [US1] Add `apply_render_attributes: bool = True` kwarg to `build_interior` in `src/storebro/interior.py`; apply to each compartment's top-level object + furniture compound. Ensure furniture/compartment labels resolve to `trim`, bulkheads to `bulkhead` (extend `_ROLE_RULES` in render.py if interior labels need explicit rules — verify actual labels first).
- [x] T009 [US1] Add `apply_render_attributes: bool = True` kwarg to `build_propulsion` in `src/storebro/propulsion.py`; apply to engine bed, engine, shaft(s), propeller(s), rudder(s) (both trains for twin-screw).
- [x] T010 [US1] Geometry tests `tests/geometry/test_render_apply.py`: after a default build, each named body has `ShapeColor` == expected palette RGBA (within 8-bit quantization) and `ShapeMaterial` set; windshield glass alpha < 1.0; an object with an unmatched label gets `DEFAULT`; attributes survive a `saveAs`→`closeDocument`→`openDocument` round-trip (data persists headless).

## Phase 4: User Story 2 — Opt out for a neutral model (Priority: P2)

**Goal**: Coloring can be globally disabled, leaving default appearance and identical geometry.

**Independent test**: Build twice (on/off); off build has no `Render` properties; geometry identical.

- [x] T011 [US2] Add `--no-colors` flag to the `build` subcommand in `src/storebro/cli.py`; thread `apply_render_attributes=not args.no_colors` into all four `build_*` calls (note `build_interior`/`build_propulsion` call sites).
- [x] T012 [US2] Geometry test `tests/geometry/test_render_cli_opt_out.py`: `apply_render_attributes=False` build → zero objects carry `ShapeColor`/`ShapeMaterial` (invariant 4); STEP/STL/BREP exports byte-identical between a `--no-colors` build and the pre-feature uncolored baseline (invariant in FR-012).

## Phase 5: User Story 3 — Never breaks reproducibility or headless builds (Priority: P3)

**Goal**: Coloring is deterministic and headless-safe; no geometry mutation.

**Independent test**: Two headless builds → identical attributes; exports byte-identical; shape properties unchanged.

- [x] T013 [US3] Geometry test `tests/geometry/test_render_geometry_invariance.py`: capture `Shape.Volume`, `BoundBox`, `Solids` count, `isValid()` per body before vs after `apply_render_attributes` → all unchanged (invariant 5, FR-011).
- [x] T014 [US3] Geometry test `tests/geometry/test_render_determinism.py`: two independent colored builds with identical inputs → identical `ShapeColor`/`ShapeMaterial` on every corresponding body (invariant 6); confirm applier is headless-safe (no crash when `ViewObject is None`).

## Phase 6: Polish & Cross-Cutting

- [x] T015 [P] Docstrings + one runnable example in `render.py` public functions (constitution DX / "definition of done" item 5); add a `docs/examples/` snippet or docstring example for `apply_render_attributes`.
- [x] T016 Run full gate on this host: `PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib uv run pytest` (unit + geometry), `uv run ruff check .`, `uv run mypy src/` — all green.
- [x] T017 Run `uv run storebro build --layout 3 --out /tmp/storebro_v1_2_0_signoff.FCStd` and a `--no-colors` variant; confirm both build; note the signoff `.FCStd` for the maintainer's GUI eyeball (constitution V).
- [x] T018 Update `CHANGELOG.md` (run through `humanizer` skill before delivery); update `specs/INDEX.md` to tick `015` and append a Register history line.

## Dependencies & Execution

- **Phase 2 (T002–T005)** blocks everything (palette + applier + exports).
- **US1 (T006–T010)** is the MVP — delivers the colored model. T006–T009 touch different module files → parallelizable after T002/T003 land. T010 after T006–T009.
- **US2 (T011–T012)** depends on US1 (build kwargs exist). 
- **US3 (T013–T014)** depends on US1; independent of US2.
- **Polish (T015–T018)** last.

## Parallel example (after T002+T003)

```
T006 [US1] hull.py    ─┐
T007 [US1] deck.py     ├─ different files, run in parallel
T008 [US1] interior.py │
T009 [US1] propulsion.py ┘
```

## Implementation strategy

MVP = Phase 2 + US1 (a default `storebro build` produces a colored model). US2 adds the opt-out; US3 hardens determinism/invariance. Ship incrementally; each phase is independently testable.
