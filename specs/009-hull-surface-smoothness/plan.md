# Implementation Plan: Hull surface smoothness

**Branch**: `master` (solo direct-push; see `.claude/rules/spec-register.md`)
**Date**: 2026-05-28
**Spec**: [spec.md](./spec.md)
**Allium baseline**: [spec.allium](./spec.allium)

**Input**: Feature specification from `specs/009-hull-surface-smoothness/spec.md`

## Summary

Raise the hull station count from a hard-coded 5 to a parametric default of 9 (range [3, 21]), introduce a quarter-circle bilge arc parameter (default 0.20 m), and switch the `PartDesign::AdditiveLoft` from `Ruled=True` (piecewise-linear) to `Ruled=False` (B-spline) whenever station count ≥ 8. When station count ≥ 8 the stem station collapses to a degenerate vertex (zero forefoot); below 8 it retains the spec 007 80-mm pentagon for known-working 1:1 vertex mapping. Detect B-spline overshoot of the hull height envelope and fail fast with a descriptive `ValueError`. Preserve spec 008's `_resolve_deck_top_z_at()` pillar-seating contract. Public API extends by two additive `HullParameters` fields with defaults; no CLI flag changes. PATCH release v1.0.3.

## Technical Context

**Language/Version**: Python 3.11+ (matches FreeCAD 1.1's bundled Python)

**Primary Dependencies**: FreeCAD 1.1+ (Python API for `Part`, `Sketcher`, `PartDesign`), the existing `storebro` package surface

**Storage**: N/A — generates `.FCStd`/`.step`/`.stl`/`.brep` files; no persistent storage

**Testing**: `pytest` with `requires_freecad` marker for geometry integration tests; unit tests for parameter validation and helper functions; `ruff` (lint+format); `mypy --strict`

**Target Platform**: Ubuntu + macOS × Python 3.11 + 3.12 (4-cell CI matrix); FreeCAD 1.1+ runtime

**Project Type**: Library + CLI (single source tree under `src/storebro/`)

**Performance Goals**: Hull geometry construction ≤ 10 s on a baseline developer laptop (Apple M-series or equivalent); CI matrix completes in ≤ 30 minutes per cell

**Constraints**:
- Constitution I — parametric (every dimension is a named parameter with a default; no magic numbers in function bodies)
- Constitution II — byte-identical STEP/STL/BREP across runs and across CI matrix cells
- Constitution III — PartDesign-idiomatic (sketches + AdditiveLoft + Mirrored; no raw mesh manipulation)
- Constitution IV — silhouette within ±1 % of RC34 1972 reference on principal dimensions
- Constitution V — tests + ruff + mypy clean; visual signoff in FreeCAD GUI
- Constitution VII — supported FreeCAD version range declared in `pyproject.toml`
- v1.0.3 PATCH bump: no public API removal/rename; new fields additive with defaults
- Spec 008 pillar-seating contract — `_resolve_deck_top_z_at()` must continue to query actual hull geometry

**Scale/Scope**: One hull body per `build_hull()` call; default station count 9 (max 21); ≤ 110 PartDesign sketches per hull at max station count; ≤ 21 datum planes per hull; one `AdditiveLoft` + one `Mirrored` feature per hull

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | How this plan satisfies it |
|---|---|---|
| **I. Parametric Everything** | ✅ PASS | `station_count` and `bilge_radius` are both new named fields on `HullParameters` with defaults. Existing magic numbers in `_compute_stations()` (the half-beam tapering profile, the 80 mm forefoot constant) are either kept as documented module-level constants or driven from `HullParameters` derived flags. No new magic numbers introduced in function bodies. |
| **II. Reproducibility (NON-NEGOTIABLE)** | ✅ PASS | The new code reuses the existing spec-002 deterministic STEP/STL/BREP writers verbatim. Station order is index-driven (0 → station_count-1, deterministic). PartDesign object creation order is deterministic per-station. The bilge arc is constructed at a deterministic sketch position. No new timestamps, no new env-dependent paths. SHA-256 reproducibility verified in tests. |
| **III. FreeCAD-Idiomatic** | ✅ PASS | All new geometry uses `PartDesign::Plane`, `Sketcher::SketchObject`, `PartDesign::AdditiveLoft`, and `PartDesign::Mirrored`. The bilge arc is a `Sketcher` arc segment inside the existing station sketch, tangent-constrained to bottom and topside edges. No `Mesh.Mesh`, no raw vertex manipulation. The HullBody remains a `PartDesign::Body` with editable feature stack; `Tip` remains the mirrored feature. |
| **IV. Reference Fidelity** | ✅ PASS | Default `station_count=9` and `bilge_radius=0.20 m` are chosen to match `docs/references/Alternativ3.JPG` within ±1 % on principal dimensions. Visual signoff against the reference image is part of the implementation Definition of Done. |
| **V. Test-Gated Releases** | ✅ PASS | New tests: parameter validation (unit), station-count derivation (unit), bilge-arc geometry assertions (geometry), B-spline overshoot detection (geometry), reproducibility hashes (geometry), pillar-seating regression (geometry). All gates green before tag. Visual signoff in FreeCAD GUI on macOS Darwin arm64 + signoff `.FCStd` checked into `tests/fixtures/signoff/`. |
| **VI. Public OSS by Default** | ✅ PASS | Additive fields only; no rename, no removal; `HullParameters.__init__` signature widens but does not break existing call sites. Changes go through normal PR → `master` flow (or direct-push for this solo project per `project_workflow` memory). PATCH bump = no MAJOR signal needed. |
| **VII. FreeCAD Version Discipline** | ✅ PASS | No FreeCAD version range change. `pyproject.toml` declares FreeCAD 1.1+; spec 009 stays inside that range. `Ruled=False` AdditiveLoft is empirically verified on FreeCAD 1.1.1 (the install in the project's CI image and the user's laptop). |

**Result**: 7/7 gates green. No violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/009-hull-surface-smoothness/
├── spec.md                  # /specify output (already written)
├── spec.allium              # /allium:elicit output (already written, 0 errors)
├── plan.md                  # this file (/plan output)
├── research.md              # Phase 0 output (this command)
├── data-model.md            # Phase 1 output (this command)
├── contracts/
│   └── hull_parameters.md   # Phase 1 output — additive field contract
├── quickstart.md            # Phase 1 output (this command)
├── checklists/
│   └── requirements.md      # /specify output (already written)
└── tasks.md                 # Phase 2 output (/tasks command, not this command)
```

### Source Code (repository root)

```text
src/storebro/
├── __init__.py              # No change — re-exports HullParameters, build_hull (already present)
├── hull.py                  # PRIMARY CHANGE — see modification map below
├── deck.py                  # NO CHANGE — _resolve_deck_top_z_at() helper preserved verbatim
├── export.py                # NO CHANGE — deterministic writers reused as-is
├── cli.py                   # NO CHANGE — no new CLI flags (clarification 3)
├── interior.py              # NO CHANGE
├── _freecad_check.py        # NO CHANGE
└── fixtures/                # NO CHANGE — Alternativ1-5 YAML fixtures unaffected

tests/
├── conftest.py              # NO CHANGE
├── unit/                    # NEW unit tests for parameter validation, derived flags
│   ├── test_hull_parameters_station_count.py        # NEW
│   ├── test_hull_parameters_bilge_radius.py         # NEW
│   ├── test_hull_parameters_derived_flags.py        # NEW
│   └── test_hull_compute_stations.py                # NEW (or extend existing)
└── geometry/                # NEW + extended geometry tests
    ├── test_hull_b_spline_loft.py                   # NEW — Ruled=False geometry
    ├── test_hull_bilge_arc.py                       # NEW — quarter-circle assertions
    ├── test_hull_zero_forefoot_stem.py              # NEW — degenerate stem topology
    ├── test_hull_overshoot_detection.py             # NEW — overshoot ValueError
    ├── test_hull_reproducibility_v103.py            # NEW — SHA-256 across runs
    ├── test_hull_pillar_seating_regression.py       # EXTEND spec 008 test
    └── test_hull_silhouette_fidelity.py             # NEW — ±1% reference match

tests/fixtures/signoff/
└── storebro_v1_0_3_signoff.FCStd                    # NEW — signoff artifact
```

**Structure Decision**: Single-project, flat-module-per-body-part (per constitution Module Layout section). All changes localized to `src/storebro/hull.py`, with test additions across `tests/unit/` and `tests/geometry/`. No new modules. No new package directories. The deck module is read-only from this spec's perspective — `deck.py` is not edited, only its `_resolve_deck_top_z_at()` helper is exercised by regression tests.

### Modification map for `src/storebro/hull.py`

| Location | Change | Reason |
|---|---|---|
| `HullParameters` dataclass (L126-) | Add fields `station_count: int = 9`, `bilge_radius: float = 0.20` | spec 009 FR-001, FR-002 |
| `HullParameters.__post_init__` (validator block L195-) | Add range checks for `station_count` (3..21) and `bilge_radius` (0..min(beam/2, draft)) | spec 009 FR-003, FR-004 |
| `HullParameters` (computed properties) | Add `uses_b_spline_loft`, `uses_zero_forefoot_stem`, `uses_bilge_arc`, `max_bilge_radius_m` as `@property` or computed in `__post_init__` | spec 009 derived flags |
| `_compute_stations()` (L239-) | Replace 5-station hard-coded list with a parametric loop over `station_count`. Stem topology branches on `uses_zero_forefoot_stem`. Non-stem topology branches on `uses_bilge_arc`. Half-beam interpolation extended to N stations. | spec 009 FR-005, FR-009 |
| `_create_station_sketch()` (L419-) | Add bilge arc construction when `profile.has_bilge_arc`. Use `Sketcher.Constraint("Tangent", ...)` to enforce tangent continuity at both arc endpoints. Use `Sketcher.Constraint("Radius", ...)` to lock the arc radius. | spec 009 FR-008 + invariant `BilgeArc.TangentContinuity` + `BilgeArc.RadiusMatchesParameters` |
| `_apply_loft_and_mirror()` (L488-) | Branch on `parameters.uses_b_spline_loft`: `Ruled=False` for ≥8 stations, `Ruled=True` for <8. Update the deferred-to-v1.1 docstring comment block (L491-) to point at spec 009 closure. | spec 009 FR-006, FR-007 |
| New helper `_detect_b_spline_overshoot()` | Sample the loft Shape's bounding box at each station's X position and compare against `parameters.draft + sheer_at_X(X)`. Raise `HullConstructionError` with offending X, overshoot magnitude, and remediation hint if any sample exceeds `OVERSHOOT_TOLERANCE_MM`. Call from `build_hull()` after the loft is built but before the mirror. | spec 009 FR — DetectBSplineOvershoot rule |
| `build_hull()` (L611-) | Call `_detect_b_spline_overshoot()` when `parameters.uses_b_spline_loft`. Otherwise skip the check. | spec 009 fail-fast contract |
| Module-level constants | Add `STATION_COUNT_MIN = 3`, `STATION_COUNT_MAX = 21`, `B_SPLINE_STATION_COUNT_THRESHOLD = 8`, `OVERSHOOT_TOLERANCE_MM = 1.0`, `DEFAULT_STATION_COUNT = 9`, `DEFAULT_BILGE_RADIUS_M = 0.20` near the existing module-level constants. | Constitution I — no magic numbers in function bodies |

## Complexity Tracking

> No Constitution violations — table intentionally empty. The plan introduces additive parametric fields and a single new helper (`_detect_b_spline_overshoot`); both are direct expressions of the spec's functional requirements.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(none)_ | _(none)_ | _(none)_ |
