# Implementation Plan: Hull Surface Curvature v2

**Branch**: `master` (direct-push) | **Date**: 2026-06-02 | **Spec**: [spec.md](./spec.md)

## Summary

Make the hull read smooth by densifying the `Ruled=True` loft, not by B-spline interpolation (spike-falsified). Two production constants change in `src/storebro/hull.py`: `STATION_COUNT_MAX` 21 → 81 and `DEFAULT_STATION_COUNT` 9 → 31. `Ruled=True` is kept (it is exact: 0% overshoot, manifold, STL-exportable at every density — spike-confirmed at n=21/31/51/81 with face counts 163/243/403/643). The quarter-circle bilge arc stays off (sharp chine): re-spiked at the new density, its B-rep is valid but the mesh tessellates non-watertight and breaks STL (the spec 009 failure, re-confirmed), so per the user's pre-authorization it re-defers to the sharp chine. The `bilge_radius` parameter, the `PENTAGON_WITH_ARC` machinery, and the `uses_bilge_arc` hook are retained as forward-compat hooks but `uses_bilge_arc` continues to return `False`.

## Technical Context

- **Language**: Python 3.11+ / FreeCAD 1.1+ PartDesign API.
- **Files touched**: `src/storebro/hull.py` (2 constants + docstrings on `uses_bilge_arc`/`uses_b_spline_loft`/`_apply_loft_and_mirror` to cite the spike evidence), `src/storebro/__init__.py` (version), `pyproject.toml` (version), tests.
- **Testing**: pytest unit (range validation, defaults) + geometry (`requires_freecad`: manifold + 0% overshoot + monotone face count + STL across densities + back-compat n=9 + build time). ruff + mypy --strict.
- **Reproducibility / manifold / fidelity**: all preserved by construction (`Ruled=True`).

## Constitution Check

| Principle | Compliance |
|---|---|
| I. Parametric | PASS — smoothness is `station_count`-driven; no magic numbers added (two named constants change value). |
| II. Reproducibility | PASS — `Ruled=True` piecewise-linear loft is deterministic; denser default still byte-identical per fixed input. |
| III. FreeCAD-idiomatic | PASS — same `AdditiveLoft`+`Mirrored` stack; B-spline raw-surface route explicitly rejected for violating this principle. |
| IV. Reference fidelity | PASS — beam/draft within ±1% (0% overshoot, spike-confirmed); denser default is a faithfulness improvement. |
| V. Test-gated | PASS — geometry tests assert manifold/overshoot/face-count/STL; ran on FreeCAD 1.1.1. |
| VI. OSS / semver | PASS — denser default changes the default output → MINOR bump (1.3.0 → 1.4.0); `station_count=9` is the back-compat escape hatch. |
| VII. FreeCAD version discipline | PASS — no new API surface. |

**Gate: PASS.**

## Build sequence

1. `hull.py`: `STATION_COUNT_MAX = 81`, `DEFAULT_STATION_COUNT = 31`.
2. `hull.py`: refresh the `uses_bilge_arc` / `uses_b_spline_loft` / `_apply_loft_and_mirror` docstrings to cite the spec 018 spike (B-spline overshoot ≥12%, bilge non-watertight) as the standing reason both stay off. No behavior change there.
3. Tests: update range tests (cap 21 → 81), default test (9 → 31), version test; add geometry tests for manifold + overshoot + monotone face count + STL across {3,9,31,81} + back-compat n=9.
4. `__init__.py` + `pyproject.toml`: 1.3.0 → 1.4.0; version-consistency test.
5. Verify: full suite on FreeCAD 1.1.1, ruff, mypy.

## Complexity Tracking

No violations. (The spike work that de-risked the scope is documented in the register history, not here.)
