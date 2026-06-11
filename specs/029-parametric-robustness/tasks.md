# Tasks: Parametric Robustness — Non-Finite Rejection

**Feature**: 029-parametric-robustness | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

**Scope**: `src/storebro/{hull,deck,interior,propulsion}.py` parameter validation + their unit tests (+ version). Spec-only track (hardening; no new API/entities/state; no `.allium`, no `/tla`). Guard = reject `nan`/`+inf`/`-inf` on every float geometry/dimension field (lengths, radii, ratios, angles, offsets), via each module's existing `ParameterError`. Finite sentinels stay accepted.

**OUTCOME — DONE.** Propulsion: helpers (`_require_positive`/`_require_non_negative`) already finite-check; added a `_require_finite` for the 4 relational-only floats (coupling-flange diameter, fairing ratio, root/tip pitch). Hull: positivity loop + `bilge_radius` now `not math.isfinite(...) or ...`; porthole/glazing floats guarded (finite sentinels preserved). Deck + interior: a generic `_reject_nonfinite_floats(self)` helper (using `dataclasses.fields`, skips ints/bools/strings/sub-dataclasses) inserted first into all 16 deck + 8 furniture `__post_init__`, plus new `__post_init__` on `Position3D`/`Dimensions3D`. 1002 unit pass (+123 in `test_nonfinite_rejection.py`, covering a representative float of every guarded dataclass × nan/inf/-inf + sentinel + valid-construct + module-coverage). Geometry unchanged (value-pinning geometry tests green; within-process FCStd byte-identical). ruff + mypy --strict clean. Version 1.13.1→1.13.2.

---

## Phase 1: Implementation

- [x] T001 [P] `src/storebro/propulsion.py` — audit: confirm every float geometry field is validated via `_require_positive`/`_require_non_negative` (which already finite-check) or the two `naca_thickness_ratio` `math.isfinite` guards. Route any raw-comparison float field (e.g. `ShaftParameters.angle_deg` range check, `PropulsionParameters.engine_offset_y_mm`) through a finite check too. No regression to existing guards (FR-005).
- [x] T002 `src/storebro/hull.py` — add a module finite helper (or fold into `_validate_hull_parameters`): reject non-finite on `loa`, `beam_max`, `draft`, `freeboard`, `sheer_height_aft/fwd`, `deadrise_amidships`, `transom_angle`, `stem_rake_angle`, `bilge_radius`; and in `PortholeParameters` / `HullGlazingParameters` `__post_init__` on their float fields (diameter, recess_depth, offsets, sentinels stay finite-accepted) → `HullParameterError(name, value, "finite")`.
- [x] T003 `src/storebro/deck.py` — finite-guard every float geometry field across all component dataclasses (`DeckParameters`, `CabinTrunkParameters`, `WindshieldParameters`, `HardtopParameters`, `PillarParameters`, `RailingParameters`, `RubrailParameters`, `BowPulpitParameters`, `LifelineParameters`, `AnchorLockerParameters`, `CleatParameters`, `CabinWindowParameters`, `WindshieldGlazingParameters`, `DsWindowParameters`) — thicknesses, lengths/widths/heights, radii, rake angles, offsets → `DeckParameterError`.
- [x] T004 `src/storebro/interior.py` — add finite guards to `Position3D` (x/y/z) and `Dimensions3D` (length/width/height) `__post_init__` (currently no validation), and to every furniture/compartment parameter dataclass (`BerthParameters`, `GalleyParameters`, `HeadParameters`, `SalonParameters`, `HelmParameters`, `BulkheadParameters`, `EngineRoomParameters`, `WetLockerParameters`) → the interior `ParameterError`.

## Phase 2: Tests + verification

- [x] T005 [P] For each guarded dataclass, extend its existing unit-test file (e.g. `test_hull_parameters.py`, `test_deck_parameters.py`, the propulsion test files, interior parameter tests) with a parametrized `nan`/`+inf`/`-inf` rejection case on a representative geometry float field, asserting the module's `ParameterError` names that field (FR-009/SC-003).
- [x] T006 Add `Position3D`/`Dimensions3D` non-finite tests (new cases in the interior parameter/loader test file); assert finite sentinels (e.g. porthole `-1.0` auto) still accepted (FR-006).
- [x] T007 Bump version 1.13.1 → 1.13.2 (`__init__.py` + `pyproject.toml`) + version-consistency test.
- [x] T008 Gate: `uv run pytest` (unit; the guards are FreeCAD-free) + `uv run ruff check .` + `uv run mypy src/`. Spot-check one geometry build is byte-identical to pre-029 (SC-005) if FreeCAD available; otherwise note unit-only per CLAUDE.md.

## Dependencies

- T001–T004 are independent per-module edits ([P] where they don't share a file). T005/T006 follow their module's impl.
- T007/T008 last.

## Implementation Strategy

Mirror the propulsion module's proven `_require_positive`/`math.isfinite` pattern in each module. The finite check goes FIRST in each field's validation (NaN-safe). Valid inputs are untouched, so no geometry test should change — run the existing unit suite after each module to confirm no regression.
