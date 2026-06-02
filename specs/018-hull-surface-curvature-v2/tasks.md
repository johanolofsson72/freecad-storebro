# Tasks: Hull Surface Curvature v2

**Feature**: 018 | **Track**: full | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Phase 1: Setup

- [x] T001 Record baseline: `uv run pytest -m "not requires_freecad" -q`, ruff, mypy (regression baseline).

## Phase 2: Core (US1 + US2 — dense Ruled=True smooth hull)

- [x] T002 [US1] In `src/storebro/hull.py` set `STATION_COUNT_MAX = 81` and `DEFAULT_STATION_COUNT = 31`.
- [x] T003 [US2] In `src/storebro/hull.py` refresh the docstrings of `HullParameters.uses_b_spline_loft`, `HullParameters.uses_bilge_arc`, and `_apply_loft_and_mirror` to cite the spec 018 spike (B-spline `Ruled=False` overshoots beam ≥12%; bilge arc B-rep valid but mesh non-watertight → STL fails) as the standing reason both remain off. No behavior change.

## Phase 3: Tests

- [x] T004 [P] [US2] Unit `tests/unit/`: update the `station_count` range test to `[3, 81]` (accept 81, reject 82) and the default-station-count test to 31; keep the `[3, ...]` floor.
- [x] T005 [P] [US1] Geometry `tests/geometry/test_hull_dense_smoothness.py` — for `station_count` ∈ {3, 9, 31, 81}: hull is `Solids==1` + `isValid()`; beam + draft within ±1% of params (0% overshoot, SC-002); STL export succeeds; lengthwise face count strictly increases 9 < 31 < 81 (SC-003); default build uses 31 stations.
- [x] T006 [P] [US3] Geometry `tests/geometry/test_hull_dense_smoothness.py` — `bilge_radius=0` keeps the sharp chine and builds manifold (FR-007); document (test comment + assertion) that the default hull does NOT use the bilge arc (`uses_bilge_arc is False`), the re-deferral outcome.
- [x] T007 [US1] Run the existing hull geometry suite (`tests/geometry/test_hull_*.py`) and fix any test that hard-codes the old default of 9 stations or the cap of 21; preserve the back-compat assertion that `station_count=9` reproduces the prior shape.

## Phase 4: Polish

- [x] T008 Bump `storebro.__version__` and `pyproject.toml` 1.3.0 → 1.4.0; update `test_version_consistency`.
- [x] T009 Full verification: `uv run pytest` on FreeCAD 1.1.1 (bundled PYTHONPATH) + ruff + mypy; confirm build time at n=81 < 10 s (SC-005).

## Dependencies

T001 → T002/T003 → T004–T007 → T008 → T009. T004/T005/T006 touch distinct files ([P]); T002/T003 share hull.py (sequential).

## Notes

- Light implementation (2 constants + docstrings); the risk was retired by the pre-spec FreeCAD spike. No `/tla` state machine of interest (single synchronous build) — but full track per the spec premise; TLA is skipped under the triviality gate (no concurrency, no multi-actor state), consistent with the build being one deterministic function.
