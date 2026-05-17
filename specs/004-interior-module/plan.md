# Implementation Plan: Interior Module

**Branch**: `004-interior-module` | **Date**: 2026-05-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-interior-module/spec.md`

## Summary

Build `storebro.interior`. A single public `build_interior(hull, deck, layout="Alternativ3", *, document=None, name=None) -> Interior` function takes the hull (spec 001) and the deck (spec 003) from the same FreeCAD document, loads one of five canonical YAML fixtures shipped inside the package (`Alternativ1.yaml` through `Alternativ5.yaml`) OR a caller-supplied YAML path, validates the layout against a documented schema (`schema_version: 1`), and produces one parametric FreeCAD `Part::Feature` per compartment in the same document. Validation rejects out-of-envelope, overlapping, asymmetric, or schema-violating layouts before any FreeCAD call; FreeCAD-side failures mid-build roll back any partial compartments (matching spec 003's discipline).

Cross-module: this is the project's first spec to depend on TWO sibling public modules. `storebro.interior` imports `storebro.hull` (Hull type), `storebro.deck` (Deck type), and `storebro._freecad_check` (shared lazy version probe). It does NOT import `storebro.export` or `storebro.cli` (FR-011).

Technical approach: a single `src/storebro/interior.py` module plus `src/storebro/fixtures/Alternativ{1..5}.yaml`. The YAML loader uses `PyYAML` (a third-party dependency, added to `pyproject.toml`). Loader + validator + builder run in sequence; per-compartment construction uses `Part.makeBox` translated to the YAML-specified `position` with `dimensions`, then validated against the hull's bounding box and against the running tally of previous compartments for overlap before each is added to the document.

## Technical Context

**Language/Version**: Python 3.11+ (matches FreeCAD 1.1's bundled CPython).

**Primary Dependencies**: FreeCAD 1.1+ Python API (`FreeCAD`, `Part`). `PyYAML ≥ 6.0` is added for YAML fixture loading — the first third-party dependency in the project. Internal dependencies: `storebro.hull`, `storebro.deck`, `storebro._freecad_check`.

**Storage**: YAML fixtures shipped inside the package via `importlib.resources` (no filesystem path needed for canonical layouts). User-supplied custom layouts come from arbitrary filesystem paths.

**Testing**: pytest with the established `unit` and `requires_freecad` markers. Geometry tests skip cleanly without FreeCAD.

**Target Platform**: Ubuntu 22.04/24.04 + macOS 14+, Python 3.11/3.12, FreeCAD 1.1+. Same matrix.

**Project Type**: Python library extension. Adds `storebro.interior` to the existing package + ships data fixtures.

**Performance Goals**: Default-layout interior on default hull + deck builds in under 60 seconds (SC-002). Whole-boat budget: 30 s (hull) + 45 s (deck) + 60 s (interior) = 135 s. Acceptable per "human-scale seconds" guidance.

**Constraints**:
- Structural determinism for fixed `(Hull, Deck, layout)` tuples (FR-005, SC-003).
- Reference fidelity: ±5% on principal compartment dimensions vs RC34 1972 cutaways (FR-003, SC-001). Looser than spec 001/003's ±1% because cutaway interior measurements are less precise than hull plans.
- FreeCAD-idiomatic: `Part`, `Sketcher`. No `Mesh.Mesh` (FR-006).
- Cross-module: imports allowed → `hull`, `deck`, `_freecad_check`. Banned → `export`, `cli` (FR-011).
- Schema-versioned YAML: `schema_version: 1` required (FR-021, clarify Q2).
- All compartments are axis-aligned boxes, symmetric about centerline (FR-009, clarify Q3).
- No logging or telemetry in v1.0.

**Scale/Scope**: Single Python module `src/storebro/interior.py` plus 5 YAML fixture files. One public function + four public types (DeckParameters-style frozen dataclass for `Interior` aggregate + 2 exception classes + the `Compartment` wrapper). ~10-12 private helpers (schema validator, YAML loader, envelope validator, overlap detector, per-compartment-type builders, rollback). Test surface: ~40-60 tests split unit vs geometry, including 5 canonical-layout integration tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against `.specify/memory/constitution.md` v1.0.0:

| Principle | Status | Evidence |
|---|---|---|
| **I. Parametric Everything** | PASS | Every compartment dim is a named field in the YAML schema (FR-002, FR-020). The fixtures themselves are data, not code (constitution-mandated separation). |
| **II. Reproducibility (NON-NEGOTIABLE)** | PASS | FR-005 + SC-003 require structural determinism. Fixed YAML → fixed geometry → fixed byte output (the latter via spec 002). |
| **III. FreeCAD-Idiomatic** | PASS | FR-006: `Part::Feature` per compartment via `Part.makeBox`. Zero `Mesh.Mesh`. |
| **IV. Reference Fidelity** | PASS | FR-003: ±5% on principal compartment dimensions vs RC34 1972 cutaways. Per-layout values pinned in research.md R1. |
| **V. Test-Gated Releases** | PASS | SC-006 (one geometry test per canonical layout + per compartment type), SC-007 (≥10 invalid-input cases — the highest bar in the project), SC-008 (rollback test), SC-009 (envelope-fit test). Ruff + mypy CI-enforced. |
| **VI. Public OSS by Default** | PASS | MIT project. Public API: 1 function + 4 types. Adding `PyYAML` is a documented dependency choice. |
| **VII. FreeCAD Version Discipline** | PASS | FR-013 reuses shared `_freecad_check` helper. Range stays in `pyproject.toml`. |

**Gates pass. No violations to justify in Complexity Tracking.**

## Project Structure

### Documentation (this feature)

```text
specs/004-interior-module/
├── plan.md
├── spec.md
├── spec.allium
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── python-api.md
├── fixtures/                       # Reference / draft fixtures during plan phase
│   └── (planned per layout — moved to src/storebro/fixtures/ during /implement)
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

Extends the existing src-layout. The interior module ships data fixtures inside the package directory.

```text
src/storebro/
├── __init__.py            # Adds build_interior + Interior + DeckParameters etc. to re-exports
├── hull.py                # (spec 001)
├── _freecad_check.py      # (spec 001 shared helper)
├── export.py              # (spec 002)
├── deck.py                # (spec 003)
├── interior.py            # NEW: build_interior() + InteriorParameters + Interior + 2 exception classes + private helpers
└── fixtures/
    ├── __init__.py        # Empty marker for importlib.resources
    ├── Alternativ1.yaml   # NEW: canonical Storebro RC34 1972 layout variants
    ├── Alternativ2.yaml
    ├── Alternativ3.yaml
    ├── Alternativ4.yaml
    └── Alternativ5.yaml

tests/
├── unit/
│   ├── test_interior_layout_loader.py    # YAML loader + schema validation
│   ├── test_interior_errors.py           # 2 exception classes
│   ├── test_interior_envelope_validator.py # Out-of-envelope rejection
│   ├── test_interior_overlap_detector.py # Compartment overlap detection
│   └── test_interior_leaf_dependencies.py # FR-011: imports hull + deck only
└── geometry/
    ├── test_interior_default_call.py     # Smoke test for Alternativ3 default
    ├── test_interior_all_five_layouts.py # SC-006: each canonical layout
    ├── test_interior_determinism.py      # SC-003 structural determinism
    ├── test_interior_envelope_fit.py     # SC-009 geometric containment
    ├── test_interior_construction_rollback.py # SC-008 partial-failure rollback
    └── test_interior_visual_signoff.py   # Whole-boat .FCStd for manual GUI review

docs/examples/
└── interior_quickstart.py
```

**Structure Decision**: **single src-layout Python module + package-internal YAML fixtures**. `importlib.resources.files("storebro.fixtures")` locates the fixtures portably (works from installed wheel AND from a `pip install -e .` editable install). The `src/storebro/fixtures/__init__.py` marker is required so importlib recognizes the directory as a sub-package.

## Complexity Tracking

> No Constitution Check violations. Section intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
