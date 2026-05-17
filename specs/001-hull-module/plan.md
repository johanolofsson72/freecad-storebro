# Implementation Plan: Hull Module

**Branch**: `001-hull-module` | **Date**: 2026-05-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-hull-module/spec.md`

## Summary

Build the parametric outer-hull module for the freecad-storebro library. Given named hull parameters (LOA, beam_max, draft, deadrise_amidships, sheer_height_aft, sheer_height_fwd, transom_angle, freeboard) — each with documented defaults matching the historical **Storebro Royal Cruiser 34 (1972 model year)** reference within ±1% — produce a fully editable FreeCAD parametric Body composed of Sketch + PartDesign features. Validation rejects geometrically impossible parameter combinations via `HullParameterError` before any FreeCAD call; FreeCAD-side construction failures are wrapped in `HullConstructionError`. Lazy first-call FreeCAD version check enforces constitution principle VII. Structural determinism is the hull module's contract — byte-identical serialization is delegated to the future export module.

Technical approach: a single public function `storebro.hull.build_hull(...)` returns a `Part::Body` constructed via a **lofted-stations strategy** — five parametric station sketches (transom, mid-aft, amidships, mid-fwd, stem) connected by a `PartDesign::AdditiveLoft` feature, all on a `Part::Body` host. The Body's `Label` and a small set of hull dimensions are exposed as FreeCAD properties so the GUI's properties panel can edit them and FreeCAD recomputes the geometry — satisfying the "editable in FreeCAD GUI" constitutional requirement.

## Technical Context

**Language/Version**: Python 3.11+ (matches FreeCAD 1.1's bundled CPython)

**Primary Dependencies**: FreeCAD 1.1+ Python API (`FreeCAD`, `Part`, `PartDesign`, `Sketcher`). No third-party Python packages for the hull module itself — keeps the dependency footprint at exactly one (FreeCAD).

**Storage**: N/A. The hull module is in-memory only; serialization to `.FCStd` is the export module's responsibility (spec 002).

**Testing**: `pytest` ≥ 8.x with two markers:
- `unit` — pure-Python tests (parameter validation, exception classes, dataclass invariants). Runnable without FreeCAD.
- `requires_freecad` — geometry property tests (volume > 0, bbox dims, topology counts, symmetry, closed-shell, parametricity). Skipped on hosts without a discoverable FreeCAD binary.

**Target Platform**: Ubuntu 22.04/24.04 + macOS 14+ (Apple Silicon and Intel). Python 3.11 + 3.12. FreeCAD 1.1+. CI matrix: 2 OS × 2 Python versions = 4 jobs per PR per constitution principle V.

**Project Type**: Python library (src-layout). PyPI distribution `freecad-storebro`, import `storebro`. No CLI in scope for this spec — that lives in spec 005.

**Performance Goals**: Default-parameter hull builds in under 30 seconds on a developer laptop (SC-002). Structural determinism is the only correctness invariant on performance (FR-005, SC-003) — no concurrency targets, no throughput targets.

**Constraints**:
- Reproducibility: for fixed input, returned Body has identical volume / bbox / topology counts to within `1e-9` relative tolerance (FR-005, SC-003).
- Reference fidelity: default LOA/beam_max/draft/freeboard match Storebro Royal Cruiser 34 (1972) specs within ±1% (FR-003, SC-001).
- FreeCAD-idiomatic: only `Part`, `PartDesign`, `Sketcher` workbenches. No `Mesh.Mesh` construction (FR-006, constitution III).
- Leaf module: `storebro.hull` MUST NOT import `storebro.deck`, `storebro.interior`, `storebro.export`, or `storebro.cli` (FR-011).
- No logging or telemetry in v1.0 (clarify Q4, Assumptions).

**Scale/Scope**: Single Python module `src/storebro/hull.py` (or `src/storebro/hull/` package if cleaner). One public function (`build_hull`) + one public dataclass (`HullParameters`) + two public exception classes (`HullParameterError`, `HullConstructionError`). ~5-10 private helpers (station-sketch builders, validator, FreeCAD-version probe). Test surface: ~20-30 tests split between `tests/unit/` and `tests/geometry/`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against `.specify/memory/constitution.md` v1.0.0:

| Principle | Status | Evidence |
|---|---|---|
| **I. Parametric Everything** | PASS | FR-002, FR-008 enumerate 8 named parameters with defaults; no magic numbers in spec; `HullParameters` dataclass holds every dimension. |
| **II. Reproducibility (NON-NEGOTIABLE)** | PASS | FR-005 + SC-003 mandate structural determinism for fixed inputs. Implementation strategy below uses fixed station-curve order, deterministic constraint application, no time-dependent values. |
| **III. FreeCAD-Idiomatic** | PASS | FR-006 + chosen lofted-stations strategy use `Part::Body`, `Sketcher::Sketch`, `PartDesign::AdditiveLoft` exclusively. Zero `Mesh.Mesh` in hull module. |
| **IV. Reference Fidelity** | PASS | FR-003 + SC-001 require ±1% on principal dimensions vs the Storebro Royal Cruiser 34 (1972) reference (LOA 10.35 m, beam 3.20 m — provided by domain expert); canonical defaults pinned in research.md and codified in `HullParameters` defaults. |
| **V. Test-Gated Releases** | PASS | SC-006 + SC-007 + the test plan (≥20 unit tests + ≥10 geometry tests) ensure every public function has at least one geometry property test and ≥5 invalid-input cases. Ruff + mypy --strict are CI-enforced. |
| **VI. Public OSS by Default** | PASS | Module is MIT-licensed (project license). All design discussions happen in this spec, plan, and the public GitHub repo. Public API surface is `build_hull` + `HullParameters` + 2 exception classes — semver MAJOR bump required to change. |
| **VII. FreeCAD Version Discipline** | PASS | FR-013 mandates a lazy first-call version check; `pyproject.toml` will declare `freecad >= 1.1, < 2.0` in the supported-versions metadata; CI matrix tests against FreeCAD 1.1.x. |

**Gates pass. No violations to justify in the Complexity Tracking section.**

## Project Structure

### Documentation (this feature)

```text
specs/001-hull-module/
├── plan.md              # This file
├── spec.md              # Feature specification (post-clarify)
├── spec.allium          # Formal spec (post-elicit)
├── research.md          # Phase 0 output (this command)
├── data-model.md        # Phase 1 output (this command)
├── quickstart.md        # Phase 1 output (this command)
├── contracts/
│   └── python-api.md    # Phase 1 output (this command)
├── checklists/
│   └── requirements.md  # Spec-quality checklist (from /speckit-specify)
└── tasks.md             # Phase 2 output (/speckit-tasks command — NOT created here)
```

### Source Code (repository root)

src-layout per constitution. The hull module is a single file unless internal complexity grows enough to justify a package.

```text
src/storebro/
├── __init__.py          # Re-exports public API: build_hull, HullParameters, exceptions, __version__
├── hull.py              # Hull builder + HullParameters + exceptions + private station builders
└── _freecad_check.py    # Internal: lazy FreeCAD version probe, cached at module load

tests/
├── unit/
│   ├── __init__.py
│   ├── test_hull_parameters.py   # Dataclass validation, range checks, defaults
│   ├── test_hull_errors.py       # HullParameterError / HullConstructionError shape + message format
│   └── test_freecad_check.py     # Version-probe behavior under monkey-patched FreeCADVersion
└── geometry/
    ├── __init__.py
    ├── conftest.py                # FreeCAD doc fixture; skip-marker for missing-FreeCAD CI
    ├── test_hull_default_dimensions.py  # SC-001: ±1% on principal dims
    ├── test_hull_determinism.py         # SC-003: structural determinism
    ├── test_hull_parametricity.py       # SC-004: every named param moves geometry
    ├── test_hull_topology.py            # FR-010: closed shell, FR-009: symmetric
    ├── test_hull_gui_editability.py     # FR-007: dimensions are FreeCAD properties
    └── test_hull_construction_errors.py # FR-015 + Edge Cases: HullConstructionError wrap

docs/
├── references/          # Existing — historical Storebro reference drawings
└── examples/
    └── hull_quickstart.py  # Runnable example (Phase 1 output)
```

**Structure Decision**: **single src-layout Python library**. The hull module is one file (`src/storebro/hull.py`) plus one internal helper (`_freecad_check.py`). Tests are split unit (no FreeCAD) vs geometry (requires FreeCAD), each in its own subdirectory with a marker. This follows the layout already described in `.specify/memory/constitution.md` and `PROJECT-BRIEF.md` — no deviation required.

## Complexity Tracking

> No Constitution Check violations. Section intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
