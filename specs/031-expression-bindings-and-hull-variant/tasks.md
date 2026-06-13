# Tasks: Expression Bindings + Hard-Chine Hull Variant

**Feature**: `specs/031-expression-bindings-and-hull-variant` | **Track**: full | **Spec**: [spec.md](./spec.md)

Item 1 (hard-chine hull variant) is the implemented P1 story. Item 2 (expression bindings) is
spike-deferred (documentation only — no code). Source: `src/storebro/hull.py`, `src/storebro/cli.py`.
FreeCAD absent → unit tests here; `requires_freecad` geometry tests for the maintainer.

## Phase 1: Setup

- [ ] T001 Re-read the anchors in `src/storebro/hull.py`: `_StationProfile`,
  `_create_pentagon_legacy_station_sketch` (the `0.6` literal at line ~675), `_compute_stations`,
  `build_hull` (station loop ~1299, `_apply_loft_and_mirror`, `_assert_hull_manifold`), the `Hull`
  dataclass, `_is_single_valid_solid`; and the `--superstructure` wiring in `src/storebro/cli.py`.

## Phase 2: Foundational

- [ ] T002 Add named constants `_HARD_CHINE_BEAM_BLEND = 0.5` and `_HARD_CHINE_CHINE_Z_FACTOR = 0.35`
  near the other hull module constants in `src/storebro/hull.py` (no magic numbers — constitution I).
- [ ] T003 Add `chine_z_factor: float = 0.6` as an additive field on `_StationProfile`
  (`src/storebro/hull.py`); update `_create_pentagon_legacy_station_sketch` (and the unused
  `_create_pentagon_with_arc_station_sketch` for consistency) to use
  `-keel_depth_mm * profile.chine_z_factor` instead of the literal `0.6`. Default 0.6 → standard
  byte-identical.

## Phase 3: User Story 1 — Hard-chine hull variant (P1)

**Goal**: `hull_variant="hard_chine"` builds a hull with a pronounced single hard chine; `"standard"`
is byte-identical to pre-031; manifold-or-fallback; variant recorded on `Hull`; CLI flag.

**Independent test**: build standard vs hard_chine on the same params → standard byte-identical to
pre-031, hard_chine a single solid with amidships chine_beam_ratio measurably higher; unknown variant
raises `HullParameterError`; two hard_chine builds in one process byte-identical.

### Variant geometry

- [ ] T004 [US1] Add `hull_variant: str = "standard"` param to `_compute_stations`
  (`src/storebro/hull.py`); for `hull_variant == "hard_chine"`, build each **non-stem**
  `PENTAGON_LEGACY` station with `half_beam_at_bottom' = bottom + (top - bottom) *
  _HARD_CHINE_BEAM_BLEND` and `chine_z_factor = _HARD_CHINE_CHINE_Z_FACTOR`. Stem/thin-stem
  unchanged; `"standard"` path unchanged.
- [ ] T005 [US1] Add the `hull_variant: Literal["standard","hard_chine"] = "standard"` keyword to
  `build_hull` (`src/storebro/hull.py`); validate it in the pre-FreeCAD path — immediately after the
  `_validate_hull_parameters(resolved_params)` call (~line 1275), before the FreeCAD `try` block —
  raising `HullParameterError("hull_variant", value, "standard|hard_chine")` so the unit test
  (T009) can assert it without FreeCAD. Thread it into the station build.
- [ ] T006 [US1] Implement the manifold-or-fallback in `build_hull` (`src/storebro/hull.py`): factor
  the station→loft→mirror build so it runs twice; build the requested variant; if
  `hull_variant=="hard_chine"` and `not _is_single_valid_solid(body.Shape)`, remove the variant
  station/loft/mirror objects from the doc + rollback list, reset `body.Tip`, rebuild `"standard"`,
  and set `variant_applied=False`. Keep the existing porthole cut + `_assert_hull_manifold` after.
- [ ] T007 [US1] Add `hull_variant: str = "standard"` and `variant_applied: bool = True` additive
  fields to the `Hull` dataclass (`src/storebro/hull.py`) and populate them in the `return Hull(...)`.

### CLI

- [ ] T008 [US1] Add `--hull-variant {standard,hard_chine}` (default `standard`) to `storebro build`
  in `src/storebro/cli.py`, pass it to `build_hull(hull_variant=...)`, and reflect it in
  `info`/JSON output consistently with `--superstructure`.

### Tests — unit (no FreeCAD)

- [ ] T009 [P] [US1] Create `tests/unit/test_hull_variant.py`: `build_hull` default keyword is
  `"standard"`; unknown variant → `HullParameterError` (param name `hull_variant`) raised before
  FreeCAD (assert via the no-FreeCAD path / mark appropriately); `Hull` exposes `hull_variant` +
  `variant_applied`; `_compute_stations(params, "hard_chine")` amidships chine_beam_ratio
  (`half_beam_at_bottom/half_beam_at_top`) > the `"standard"` ratio by the expected margin;
  `_compute_stations(params, "standard")` profiles equal the no-arg profiles (default preserved);
  `chine_z_factor` defaults to 0.6.
- [ ] T010 [P] [US1] Add CLI unit coverage in the existing CLI test module(s) (`tests/unit/test_cli_*`)
  for `--hull-variant` parsing (valid values, default, invalid value rejected), mirroring the
  `--superstructure` tests.

### Tests — geometry (requires_freecad, maintainer runs)

- [ ] T011 [P] [US1] Create `tests/geometry/test_hull_variant_geom.py` (`@pytest.mark.requires_freecad`):
  (a) standard build is a single valid solid and matches a pinned pre-031 baseline (volume/reproducibility);
  (b) hard_chine build is a single valid solid (`Solids==1`, `isValid()`); (c) hard_chine volume/shape
  differs from standard and its amidships cross-section chine sits more outboard; (d) two hard_chine
  builds in one process are byte-identical (volume within tol); (e) `hull.variant_applied is True` on
  a successful hard_chine build; (f) `hull.hull_variant` round-trips.

## Phase 4: Deferred item (documentation only — no code)

- [ ] T012 Confirm `spec.allium` carries `deferred HullBody.expression_bindings` + the expression
  `open question`, and `research.md §D6` records the design + deferral reason. **No `setExpression`
  code is written.** (Item 2 closure = documented + surfaced; verified during commit.)

## Phase 5: Polish & cross-cutting

- [ ] T013 Audit existing hull-dependent `requires_freecad` baselines for any that would break if a
  test passed `hull_variant` — none should, since the default is unchanged; confirm
  `test_hull_reproducibility_v103` and deck/interior/export tests still target the standard hull.
- [ ] T014 Bump version `1.14.0 → 1.15.0` (additive MINOR) in `pyproject.toml`, `src/storebro/__init__.py`,
  and `tests/unit/test_version_consistency.py`; add a humanized CHANGELOG entry (windshield-crown
  style) noting the opt-in hard-chine variant + the deferred expression bindings.
- [ ] T015 Run gates: `uv run pytest -m "not requires_freecad"`, `uv run ruff check src/ tests/`,
  `uv run mypy src/`; fix failures. Run the humanizer over CHANGELOG/commit text before delivery.

## Dependencies

- T001 → T002 → T003 → (T004 → T005 → T006 → T007) → T008 → tests (T009–T011) → T012 → T013 → T014 → T015.
- T009, T010, T011 are mutually parallel `[P]` (distinct files).

## Implementation strategy (MVP)

MVP = US1 (T001–T011): the variant knob, reshaping, fallback, `Hull` bookkeeping, CLI, and tests.
T012 closes the deferred item as documentation. T013–T015 are release hygiene. Item 2 ships no code.
