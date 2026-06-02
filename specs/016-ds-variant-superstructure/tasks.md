# Tasks: DS-Variant Superstructure (enclosed deck saloon)

**Feature**: 016-ds-variant-superstructure | **Track**: light | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Tests are included (constitution V mandates pytest unit + geometry coverage). All geometry tasks are FreeCAD 1.1+ (`requires_freecad`); unit tasks need no FreeCAD.

**Single module focus**: nearly all code edits land in `src/storebro/deck.py` → those tasks are **sequential** (same file, not `[P]`). `[P]` is reserved for distinct files (separate test files, cli.py, __init__.py).

## Phase 1: Setup

- [x] T001 Confirm baseline green before edits: run `uv run pytest -m "not requires_freecad" -q`, `uv run ruff check src/storebro/deck.py src/storebro/cli.py`, `uv run mypy src/` and record the pass counts (regression baseline for SC-002).

## Phase 2: Foundational (blocking prerequisites for all stories)

- [x] T002 Add `from typing import Literal` import (if absent) and the `DsWindowParameters` frozen dataclass to `src/storebro/deck.py` (fields + `__post_init__` per data-model §1.1; raises `DeckParameterError`).
- [x] T003 Add the `DeckhouseParameters` frozen dataclass to `src/storebro/deck.py` (fields, `REFERENCE_STOREBRO_DECKHOUSE_DS` ClassVar, per-field + `TaperedSilhouette` + `RecessShallowerThanWall` cross-field validation per data-model §1.2).
- [x] T004 Add the `Deckhouse` frozen wrapper dataclass to `src/storebro/deck.py` (data-model §2.1) and extend `__all__` with `DeckhouseParameters`, `DsWindowParameters`, `Deckhouse`.
- [x] T005 Widen the `Deck` aggregate in `src/storebro/deck.py`: `cabin_trunk`/`windshield`/`hardtop`/`hardtop_pillars`/`cabin_windows` → `... | None`; append `superstructure_variant: str` and `deckhouse: Deckhouse | None` fields (data-model §3.1). Update the standard-path `Deck(...)` construction to pass `superstructure_variant="standard"`, `deckhouse=None`.
- [x] T006 [P] Re-export `DeckhouseParameters`, `DsWindowParameters`, `Deckhouse` from `src/storebro/__init__.py`.

**Checkpoint**: types compile (`uv run mypy src/`), standard build still constructs `Deck` with the two new fields. No behavior change yet.

## Phase 3: User Story 1 — Build the DS enclosed-wheelhouse silhouette (P1)

**Goal**: `build_deck(hull, superstructure_variant="ds")` returns a single manifold `Deckhouse` solid, seated on the deck, with blind windows, sharing deck plate + railings + hardware.

**Independent test**: build hull + DS deck; assert `deckhouse` manifold (`Solids==1`, `isValid()`), four open-flybridge slots None, shared items present, dims within ±1%, STL export succeeds.

### Tests (write first)

- [x] T007 [P] [US1] Unit (no FreeCAD): `tests/unit/test_deckhouse_validation.py` — (a) every `DeckhouseParameters` + `DsWindowParameters` invariant (positive dims, rake band, `forward_width<=aft_width`, `recess_depth<wall_inset`, `wall_inset==0` rejects positive recess), each asserting the `DeckParameterError` field name/range; (b) selector guards via a lightweight fake hull — `superstructure_variant="bogus"` rejected (FR-001/FR-011), `variant="ds"` + `parameters_superstructure=...` rejected as contradictory (FR-014), and `_validate_cross_hull_deckhouse` rejects length>LOA and width+walkways>beam (FR-012) — all raising `DeckParameterError` before any FreeCAD call.
- [x] T008 [P] [US1] Geometry: `tests/geometry/test_deckhouse_build.py` — DS deck builds; `deckhouse.body.Shape.Solids` count == 1 and `isValid()`; deckhouse ZMin ≈ sampled deck-plate top (seating); principal dims (length/height/fwd/aft width) within ±1% of defaults; window recess count == `count_per_side*2`; `export_stl(deckhouse.body)` succeeds.

### Implementation

- [x] T009 [US1] Add `_validate_cross_hull_deckhouse(hull, dh)` to `src/storebro/deck.py` — `dh.fwd_offset + dh.length <= hull.parameters.loa` and `dh.aft_width + 2*dh.wall_inset <= hull.parameters.beam_max`, else `DeckParameterError` (FR-012).
- [x] T010 [US1] Add `_build_deckhouse(hull, parameters, deck_plate, dh, target_doc, added)` to `src/storebro/deck.py` — two-trapezoid `PartDesign::AdditiveLoft` (Ruled=True) seated via `_resolve_deck_top_z_at`; front rake via upper forward-edge aft shift `height*tan(front_rake)`; back-compat named Body props; returns `Deckhouse` (mirrors `_build_cabin_trunk`, deck.py:1539).
- [x] T011 [US1] Add `_cut_deckhouse_windows(deckhouse, win, target_doc, added)` to `src/storebro/deck.py` — `count_per_side` blind `PartDesign::Pocket` recesses per side (mirrors `_cut_cabin_windows`, deck.py:1815); set `window_count`; followed by `_assert_solid_manifold(deckhouse.body, "deckhouse")`.
- [x] T012 [US1] Branch `build_deck` in `src/storebro/deck.py` on `superstructure_variant`: in the `"ds"` branch build deck plate → deckhouse → windows → railings → hardware (skip cabin trunk/windshield/hardtop/pillars/cabin-windows); assemble `Deck(...)` with `deckhouse` set and the four open-flybridge slots + `cabin_windows` = None. Keep the standard branch untouched.
- [x] T013 [US1] Wire render attributes for the DS branch in `src/storebro/deck.py`: include `deckhouse.body` in the `_render_targets` list; verify `render.role_for_label` resolves the `Deck_Deckhouse` label to the superstructure-white role (extend the role map in `src/storebro/render.py` only if it resolves to DEFAULT).

**Checkpoint**: US1 independently testable — DS variant builds a manifold deckhouse.

## Phase 4: User Story 2 — Standard variant remains the unchanged default (P1)

**Goal**: zero regression in the default open-flybridge path.

**Independent test**: standard build produces the six bodies with populated fields, `deckhouse is None`, `superstructure_variant=="standard"`; all pre-existing deck tests pass.

### Tests

- [x] T014 [P] [US2] Geometry: `tests/geometry/test_deck_variant_backcompat.py` — standard `build_deck(hull)` populates `cabin_trunk`/`windshield`/`hardtop`/`hardtop_pillars`/`cabin_windows`, `deckhouse is None`, `superstructure_variant=="standard"`; DS `build_deck(hull, superstructure_variant="ds")` inverts the population (four slots + cabin_windows None, deckhouse set); both share non-None `railings` + 5 hardware wrappers; assert the input `hull.body.Shape.Volume` is unchanged after the DS build (FR-018 — hull never booleaned).

### Implementation

- [x] T015 [US2] Add the pre-FreeCAD guards to `build_deck` in `src/storebro/deck.py`: reject `superstructure_variant` not in `{"standard","ds"}` and reject `variant=="ds"` + non-None `parameters_superstructure` (FR-014), both raising `DeckParameterError` before any FreeCAD call. Resolve `dh = parameters_deckhouse or DeckhouseParameters()` and run `_validate_cross_hull_deckhouse` in the DS branch only.
- [x] T016 [US2] Run the existing deck test suites (`tests/unit/test_deck_*.py`, `tests/geometry/test_deck_*.py`) and fix any that assumed the four slots are non-Optional or relied on the old `Deck` field set; preserve their original standard-path assertions (no weakening).

**Checkpoint**: US1 + US2 — both variants correct, default unchanged.

## Phase 5: User Story 3 — Select the variant from the CLI (P2)

**Goal**: `--superstructure {standard,ds}` flag on `storebro build`.

**Independent test**: `--superstructure ds` builds DS; omitted/`standard` builds standard; bad value → non-zero exit.

### Tests

- [x] T017 [P] [US3] Unit: `tests/unit/test_cli_superstructure_flag.py` — argparse accepts `standard`/`ds`, defaults to `standard`, rejects an unknown value (SystemExit / non-zero), and `_run_build` threads `superstructure_variant` into `build_deck` (mock/fake `build_deck` capturing the kwarg).

### Implementation

- [x] T018 [US3] Add `--superstructure` (`choices=["standard","ds"]`, default `"standard"`) to the `build` subparser in `src/storebro/cli.py` and thread `superstructure_variant=args.superstructure` into the `build_deck(...)` call in `_run_build`.
- [x] T019 [US3] Update the CLI flag-baseline test (the existing `test_cli_flags_v103`-style test that asserts the accepted `build` flag set) in `tests/unit/` to include `--superstructure`.

**Checkpoint**: all three stories complete.

## Phase 6: Polish & cross-cutting

- [x] T020 Bump `storebro.__version__` `1.2.1` → `1.3.0` in `src/storebro/__init__.py` and update the `test_version_consistency` expectation (MINOR — additive public API, data-model §5).
- [x] T021 [P] Add a runnable docstring example to `build_deck` and/or `DeckhouseParameters` showing `superstructure_variant="ds"` (constitution / "implemented" definition item 5: public-API example).
- [x] T022 Full verification gate: `uv run pytest` (or `-m "not requires_freecad"` if no FreeCAD host, plus the geometry suite on a FreeCAD 1.1+ host), `uv run ruff check src/ tests/`, `uv run mypy src/` all clean; confirm SC-002 (pre-existing standard tests all pass) against the T001 baseline.
- [x] T023 Build a DS signoff `.FCStd` (`storebro build --superstructure ds --out /tmp/storebro_v1_3_0_ds_signoff.FCStd`) for the maintainer GUI eyeball vs `docs/references/storo34_side_lines.png` (constitution V; SC-004).

## Dependencies & order

- **Setup (T001)** → **Foundational (T002–T006)** → **US1 (T007–T013)** → **US2 (T014–T016)** → **US3 (T017–T019)** → **Polish (T020–T023)**.
- US2 depends on US1's branch existing (T012/T015 share the `build_deck` body). US3 depends on `build_deck` accepting the kwarg (T012). So the story order is also the execution order — they are *separately testable* but not file-parallel (all touch `deck.py`).
- Within a phase, `[P]` tasks touch distinct files: T007/T008 (new test files), T014/T017 (new test files), T006/T021 (init/docstring) can run alongside their phase's deck.py work.

## Parallel execution examples

- Foundational: T006 (`__init__.py`) ∥ T002–T005 (`deck.py`) — different files.
- US1: T007 (`test_deckhouse_params.py`) ∥ T008 (`test_deckhouse_build.py`) — different test files, both before/with T009–T013.

## Implementation strategy

- **MVP = US1** (the DS deckhouse builds). US2 (back-compat) and US3 (CLI) harden and expose it.
- Light track: no `/tla` (trivial synchronous variant branch, single actor — per plan R8). No browser tests (library/CLI, no interactive UI).
