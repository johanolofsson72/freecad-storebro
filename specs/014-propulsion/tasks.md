# Tasks: Propulsion — Engine Bay, Engine, Shaft, Propeller & Rudder

**Input**: Design documents from `specs/014-propulsion/`

**Prerequisites**: plan.md, spec.md, spec.allium, research.md, data-model.md, contracts/python-api.md

**Tests**: REQUIRED — constitution V (test-gated releases) + spec.md Success Criteria. This is a non-interactive library (no UI), so the `specs.md` *destructive browser test* phases map to **destructive parameter-validation tests** (the 6 attack categories applied to the public API: garbage values, NaN/inf, boundary, wrong order/ordering invariants, skipped/None inputs, extreme magnitudes). Functional coverage = ≥1 test per implemented builder + the aggregate.

> **Verification note:** if FreeCAD is not importable on the implementation host, the `requires_freecad` geometry tier is WRITTEN but PENDING execution on a FreeCAD 1.1+ host (per CLAUDE.md missing-FreeCAD fallback). The geometry run can be done with `PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib` per the spec 010–013 closure note. Unit tier + ruff + mypy MUST be green regardless.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable (different file, no dependency on an incomplete task)
- **[Story]**: US1 (single-screw train), US2 (twin-screw), US3 (CLI + export)
- All paths relative to repo root.

---

## Phase 1: Setup

- [x] T001 Bump version: set `version = "1.1.0"` in `pyproject.toml` and `__version__ = "1.1.0"` in `src/storebro/__init__.py` — FR-014.
- [x] T002 Update `tests/unit/test_version_consistency.py` expectation to `1.1.0` (asserts `storebro.__version__` equals the `pyproject.toml` version string).
- [x] T003 Create `src/storebro/propulsion.py` skeleton: module docstring (coordinate convention, scope), imports (`dataclasses`, `contextlib`, `typing.Any`, lazy `FreeCAD`/`Part`/`Sketcher` access inside builders), and the `_freecad_check.ensure_supported_freecad()` lazy guard call site, mirroring `deck.py`'s module head.

## Phase 2: Foundational (BLOCKING — all stories depend on these)

- [x] T004 In `src/storebro/propulsion.py`, add the two exception classes per contracts: `PropulsionParameterError(ValueError)` and `PropulsionConstructionError(RuntimeError)` (mirror `HullParameterError`/`HullConstructionError`).
- [x] T005 In `src/storebro/propulsion.py`, add the five frozen component parameter dataclasses with `__post_init__` validation per data-model §1: `EngineBedParameters`, `EngineParameters`, `ShaftParameters`, `PropellerParameters`, `RudderParameters`. Each raises `PropulsionParameterError` naming the offending value + valid range.
- [x] T006 In `src/storebro/propulsion.py`, add the `PropulsionParameters` composite (data-model §1) with `field(default_factory=...)` for the five sub-dataclasses, the layout fields (`engine_count=2`, `engine_offset_y_mm=400.0`, `rudder_count: int | None = None`), and `__post_init__` enforcing the cross-invariants: `EngineCountSupported`, `RudderCountSupported`, `SingleScrewIsCentred`, `TwinScrewIsOffset`, `ShaftExitForwardOfEngineStation`.
- [x] T007 In `src/storebro/propulsion.py`, add the five frozen result wrapper dataclasses per data-model §"Output wrapper dataclasses": `EngineBed`, `EngineBlock`, `Shaft`, `Propeller`, `Rudder` (with the metadata fields the tests assert).
- [x] T008 In `src/storebro/propulsion.py`, add the `Propulsion` aggregate dataclass (data-model §Aggregate): document, resolved parameters, the five body lists, `hull_modified: bool`, `build_duration_seconds: float`.
- [x] T009 In `src/storebro/propulsion.py`, add the two hull-sampling helpers `_hull_bottom_z_at(hull, x_mm)` (min Z of hull `Shape.Vertexes` near X) and `_hull_half_beam_at(hull, x_mm)` (max |Y| near X), mirroring `hull._hull_outer_y_and_freeboard_at` (research R4).
- [x] T010 In `src/storebro/propulsion.py`, add the PartDesign micro-helpers needed (reuse the spec 008/010 idiom): `_pd_origin_plane`, `_pd_make_yz_datum` (with a rotation arg for the shaft tilt), `_add_box_pad`, `_add_circular_pad`, `_pd_close_loop`. Keep them module-local (no cross-module private import).
- [x] T011 Update `src/storebro/__init__.py` (imports + `__all__`, alphabetical) to export the public names per contracts: `build_propulsion`, `Propulsion`, `PropulsionParameters`, `EngineBedParameters`, `EngineParameters`, `ShaftParameters`, `PropellerParameters`, `RudderParameters`, `EngineBed`, `EngineBlock`, `Shaft`, `Propeller`, `Rudder`, `PropulsionParameterError`, `PropulsionConstructionError`.
- [x] T012 [P] Unit tests for each component dataclass validation branch: `tests/unit/test_engine_bed_parameters.py`, `test_engine_parameters.py`, `test_shaft_parameters.py` (angle bounds 0/30, exit ≥0), `test_propeller_parameters.py` (hub<disc, blade 2–6), `test_rudder_parameters.py`. Mirror `tests/unit/test_pillar_parameters.py`.
- [x] T013 [P] Unit test `tests/unit/test_propulsion_parameters.py` for the composite: default_factory independence, the five cross-invariants (incl. single-screw-must-be-centred, twin-must-be-offset, exit-forward-of-engine), and `rudder_count=None → engine_count` resolution.

## Phase 3: User Story 1 — A complete single-screw propulsion train (P1) 🎯 MVP

**Goal**: `build_propulsion(hull, deck, parameters=PropulsionParameters(engine_count=1, engine_offset_y_mm=0))` produces one bed, engine, shaft, propeller, rudder, correctly seated.

**Independent test**: `build_propulsion(build_hull(), engine_count=1)` → 1 of each component; shaft down-and-aft; prop aft of exit; rudder aft of prop; running gear below waterline; engine inside hull envelope; each body a single manifold.

- [x] T014 [US1] In `src/storebro/propulsion.py`, implement `_build_engine_bed(hull, params, target_doc, added, *, is_port, offset_y)` — box `Pad` seated above the sampled keel at `engine.station_x_mm`, offset_y applied; returns `EngineBed`.
- [x] T015 [US1] In `src/storebro/propulsion.py`, implement `_build_engine(hull, deck, params, bed, target_doc, added, *, is_port, offset_y)` — box `Pad` resting on the bed top, height-clamped below the deck-top ceiling (or hull-sheer fallback when `deck is None`); sets `rests_on_bed`, `within_hull_envelope`, `pierces_hull_shell=False`; returns `EngineBlock`.
- [x] T016 [US1] In `src/storebro/propulsion.py`, implement `_build_shaft(hull, params, engine, target_doc, added, *, is_port, offset_y)` — cylindrical `Pad` on a YZ datum rotated by `shaft.angle_deg`, from the engine coupling down-and-aft to `shaft.exit_x_mm` (exit Z from `_hull_bottom_z_at`), plus an additive stern-tube boss cylinder at the penetration; sets `forward_z_mm`/`aft_z_mm`/`exit_x_mm`/`exit_z_mm`/`has_stern_tube_boss=True`; returns `Shaft`.
- [x] T017 [US1] In `src/storebro/propulsion.py`, implement `_build_propeller(params, shaft, target_doc, added, *, is_port, offset_y)` — hub cylinder `Pad` + `blade_count` radial blade `Pad`s in one Body, placed aft of the shaft exit on the shaft axis below the waterline; sets `hub_x_mm`/`bbox_min_z_mm`/`blade_count`; returns `Propeller`.
- [x] T018 [US1] In `src/storebro/propulsion.py`, implement `_build_rudder(params, propeller, target_doc, added, *, is_port, offset_y)` — foil-plate blade `Pad` (chord×span, thickness) + stock cylinder, aft of the propeller below the waterline; sets `x_mm`/`bbox_min_z_mm`; returns `Rudder`.
- [x] T019 [US1] In `src/storebro/propulsion.py`, implement `build_propulsion(hull, deck=None, parameters=None, *, document=None, name="Propulsion")`: resolve params (incl. `rudder_count`), run the build-context validation (offset-past-topsides, exit-aft-of-engine, exit-below-waterline), build the single-train sequence (bed→engine→shaft→propeller→rudder) appending to `added`, assert the per-body manifold guard (`Solids==1`, `isValid()`), set `hull_modified=False`, and wrap in `Propulsion`. Rollback pattern: pass `PropulsionParameterError` through, wrap others as `PropulsionConstructionError` after reverse `removeObject`.
- [x] T020 [P] [US1] Geometry test `tests/geometry/test_propulsion_single_screw.py` (marker `requires_freecad`): `engine_count=1` → exactly 1 of each component; counts match.
- [x] T021 [P] [US1] Geometry test `tests/geometry/test_propulsion_shaft_geometry.py`: `forward_z_mm > aft_z_mm`, `exit_z_mm <= 0`, `has_stern_tube_boss`.
- [x] T022 [P] [US1] Geometry test `tests/geometry/test_propulsion_running_gear_order.py`: `propeller.hub_x_mm < shaft.exit_x_mm`, `rudder.x_mm < propeller.hub_x_mm`, both `bbox_min_z_mm < 0`.
- [x] T023 [P] [US1] Geometry test `tests/geometry/test_propulsion_engine_envelope.py`: `within_hull_envelope` True, `pierces_hull_shell` False, engine bbox inboard of sampled half-beam.
- [x] T024 [P] [US1] Geometry test `tests/geometry/test_propulsion_manifold.py`: every produced body `Shape.Solids == 1` and `isValid()`.
- [x] T025 [P] [US1] Geometry test `tests/geometry/test_propulsion_hull_unmodified.py`: hull `Shape.Solids` count + volume unchanged before/after `build_propulsion`; `propulsion.hull_modified is False`.

## Phase 4: User Story 2 — Twin-screw configuration (P2)

**Goal**: `engine_count=2` produces port + starboard trains mirrored about Y=0, offset outboard, with `rudder_count` rudders.

**Independent test**: `build_propulsion(build_hull())` (default twin) → 2 beds/engines/shafts/props; port at +Y, starboard at −Y mirror; rudder count == config.

- [x] T026 [US2] In `src/storebro/propulsion.py`, extend `build_propulsion` to loop the per-train sequence over the resolved train set: 1 centreline train for `engine_count=1`; 2 trains (port `+offset_y`, starboard `−offset_y`) for `engine_count=2`. Build `rudder_count` rudders (one per screw, or a single centreline rudder when `rudder_count=1` on a twin).
- [x] T027 [P] [US2] Geometry test `tests/geometry/test_propulsion_default_call.py`: default (twin) → 2 of each running-gear component; `len(rudders) == rudder_count`.
- [x] T028 [P] [US2] Geometry test `tests/geometry/test_propulsion_twin_symmetric.py`: port count == starboard count; the starboard train's bodies are the +Y train mirrored to −Y (Y-centroids equal magnitude, opposite sign).

## Phase 5: User Story 3 — CLI and export composition (P3)

**Goal**: `storebro build` includes propulsion by default (with flags); bodies flow into all export formats.

**Independent test**: `storebro build --layout Alternativ3 --out boat.FCStd` → propulsion bodies in the document; `--no-propulsion` omits them; `--engine-count 1` builds single-screw.

- [x] T029 [US3] In `src/storebro/cli.py`, add `--engine-count {1,2}` (default 2) and `--no-propulsion` (store_true) flags to the `build` subparser; import `build_propulsion`/`PropulsionParameters`.
- [x] T030 [US3] In `src/storebro/cli.py` `_run_build`, after `build_interior`, call `build_propulsion(hull, deck, parameters=PropulsionParameters(engine_count=args.engine_count))` on the same document unless `args.no_propulsion`.
- [x] T031 [P] [US3] Unit test `tests/unit/test_cli_build.py` (extend): `--engine-count` parsed to {1,2}, `--no-propulsion` parsed; argument wiring asserted via a monkeypatched `build_propulsion` (no FreeCAD) — confirm it is/ isn't called per flags and receives the right `engine_count`.
- [x] T032 [P] [US3] Geometry test `tests/geometry/test_propulsion_cli_export.py`: CLI build to `.FCStd` then `.step` → propulsion bodies present in the document tree and in the STEP export.

## Phase 6: Polish & Cross-Cutting

- [x] T033 [P] Geometry test `tests/geometry/test_propulsion_determinism.py`: two builds with identical params → byte-identical export (mirror `test_deck_hardware_determinism.py`).
- [x] T034 [P] Geometry test `tests/geometry/test_propulsion_rollback.py`: inject a mid-build failure (monkeypatch one `_build_*` to raise) → document restored to pre-call object set; `PropulsionConstructionError` raised.
- [x] T035 [P] Unit test `tests/unit/test_propulsion_destructive_validation.py`: the 6 attack categories against the public API — garbage/negative/zero dims, NaN/inf (document current behavior; non-finite hardening is a known module-wide deferral), boundary (angle 0 and 30, blade 2 and 6, engine_count 0/3 rejected), ordering (exit ≥ engine station rejected), None/skipped (deck omitted works), extreme magnitudes (offset past topside rejected).
- [x] T036 [P] Unit test `tests/unit/test_propulsion_public_docstrings.py`: every public name has a one-line docstring + the API matches contracts/python-api.md (mirror `test_deck_public_docstrings.py`).
- [x] T037 [P] Unit test `tests/unit/test_propulsion_back_compat.py`: importing `storebro` still exposes all pre-1.1.0 names; `build_hull`/`build_deck`/`build_interior` signatures unchanged.
- [x] T038 [US1] Geometry test `tests/geometry/test_propulsion_visual_signoff.py`: build the composed model (hull+deck+interior+propulsion), export `tests/fixtures/signoff/storebro_v1_1_0_signoff.FCStd` (gitignored), record SHA-256 — for the maintainer's FreeCAD GUI eyeball (constitution V).
- [x] T039 Run `uv run pytest -m "not requires_freecad"`, `uv run ruff check src/ tests/`, `uv run mypy --strict src/` — all green. Then the `requires_freecad` tier on a FreeCAD host (or document PENDING per the verification note).
- [x] T040 Update `CHANGELOG.md` with the v1.1.0 propulsion entry (run the text through the `humanizer` skill before delivery).

---

## Dependencies & Execution Order

- **Phase 1 (Setup)** → **Phase 2 (Foundational)** block everything.
- **US1 (Phase 3)** is the MVP and must complete before US2 (twin extends US1's per-train builders) and before US3 (CLI composes the builder).
- **US2 (Phase 4)** depends on US1's `build_propulsion` train loop.
- **US3 (Phase 5)** depends on US1 (a working `build_propulsion`); independent of US2 (works for either engine count).
- **Phase 6 (Polish)** after the stories.

## Parallel Opportunities

- T012 + T013 (unit param tests) in parallel after Phase 2 dataclasses exist.
- Within US1: T020–T025 (geometry tests) parallel once T019 lands.
- T027 + T028 parallel after T026.
- T033–T037 parallel in polish.

## MVP Scope

**US1 only** (Phases 1–3) delivers a complete, correct single-screw installation — independently valuable and shippable. US2 (twin) and US3 (CLI) are incremental.
