# Implementation Plan: Parametric Robustness — Non-Finite Rejection

**Branch**: `029-parametric-robustness` | **Date**: 2026-06-11 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/029-parametric-robustness/spec.md`

## Summary

Reject non-finite (`nan`/`+inf`/`-inf`) values in every geometry/dimension float field of every parameter dataclass across `hull.py`, `deck.py`, `interior.py`, and `propulsion.py`, matching the existing per-field positivity/range validation. The propulsion module already does this (`_require_positive`/`_require_non_negative` check `math.isfinite` first); this generalizes the guard to hull/deck/interior. Pure hardening — no new entities/state/API, no geometry change for valid input. Spec-only track (no `.allium`, no `/tla`).

## Technical Context

**Language/Version**: Python 3.11+.
**Primary Dependencies**: stdlib `math` (`isfinite`). No FreeCAD needed for the new guards (pure `__post_init__` checks).
**Testing**: `pytest` unit (the new guards are unit-testable without FreeCAD); `ruff`; `mypy --strict`.
**Project Type**: Single library; change is confined to the four parameter modules + their unit tests.
**Constraints**: valid inputs unchanged (FR-003, byte-identical geometry); first-violation error semantics preserved; reuse each module's existing `ParameterError` (FR-004).
**Scale/Scope**: ~30 dataclasses across 4 modules; each `__post_init__`/`_validate_*` already iterates its fields — add a finite check to each float geometry/dimension field (lengths, radii, ratios, angles, offsets).

## Constitution Check

| Principle | Status | Compliance |
|---|---|---|
| I. Parametric | ✅ | No params added/removed; only their validation is hardened. |
| II. Reproducibility (NON-NEGOTIABLE) | ✅ | Valid inputs untouched → byte-identical geometry; the guard *protects* reproducibility (a `nan` dimension would corrupt it). |
| III. FreeCAD-Idiomatic | ✅ | Pure Python validation; no FreeCAD change. |
| IV. Reference Fidelity | ✅ | No geometry change. |
| V. Test-Gated | ✅ | Every guarded dataclass gains a `nan`/`inf` unit test (FR-009). |
| VI. SemVer | ✅ | Stricter input validation is a behavior change for invalid input only → PATCH bump 1.13.1 → 1.13.2. |
| VII. FreeCAD Version Discipline | ✅ | No FreeCAD API used. |

**Result: PASS.**

## Build Sequence (one task)

The pattern per module: add a module-local `_require_finite(name, value)` helper (or fold the `math.isfinite` check into each module's existing positivity helper / `__post_init__` loop), raising that module's `ParameterError`. Then guard every float geometry/dimension field.

1. **propulsion.py** — already guarded via `_require_positive`/`_require_non_negative`; audit for any raw float field validated by a bare comparison (not via the helpers) and route it through a finite check. No regression to the existing `naca_thickness_ratio` guards.
2. **hull.py** — `_validate_hull_parameters` (+ `PortholeParameters`, `HullGlazingParameters` `__post_init__`): add `math.isfinite` rejection for `loa`, `beam_max`, `draft`, `freeboard`, sheer heights, `deadrise_amidships`, `transom_angle`, `stem_rake_angle`, `bilge_radius`, porthole diameters/recess/offsets, glazing floats — raising `HullParameterError(name, value, ...)`.
3. **deck.py** — every component dataclass `__post_init__` / `_validate_deck_parameters`: finite-guard each float (thicknesses, lengths/widths/heights, radii, rake angles, offsets) → `DeckParameterError`.
4. **interior.py** — `Position3D`/`Dimensions3D` (currently NO validation — add finite guards on x/y/z, length/width/height) + every furniture/compartment parameter dataclass `__post_init__` → the interior `ParameterError`.
5. **Tests** — every guarded dataclass's existing unit-test file gains a parametrized `nan`/`inf`/`-inf` rejection case on a representative geometry field (FR-009). Add `Position3D`/`Dimensions3D` tests if none exist.
6. **Version** 1.13.1 → 1.13.2 + version-consistency test.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Over-guarding a finite sentinel (e.g. `-1.0` auto) | The finite check only rejects `nan`/`inf`; a finite sentinel passes it and reaches existing sentinel logic (FR-006). Tests assert sentinels still accepted where they exist. |
| Double-guarding propulsion fields → regression | Propulsion helpers already finite-check; only route truly-unguarded raw-comparison floats through a finite check (FR-005). |
| NaN sneaking past `<=0` | Order the check as `not math.isfinite(value)` first (FR-002); tests cover `nan` explicitly. |
| A genuinely-unbounded float field (no positivity bound) | Still finite-guard it (a `nan`/`inf` is invalid regardless of sign), e.g. `Position3D` offsets. |

## Phase 2 note

`/speckit-tasks` expands this; `/speckit.analyze` runs before `/implement`. Spec-only track → no `/allium`, no `/tla`; the constraint is the per-dataclass `nan`/`inf` unit tests.
