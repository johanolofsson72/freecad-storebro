# Implementation Plan: Deck Module

**Branch**: `003-deck-module` | **Date**: 2026-05-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-deck-module/spec.md`

## Summary

Build the `storebro.deck` module. A single public `build_deck(hull, parameters=None, *, document=None, name="Deck") -> Deck` function takes a `Hull` returned by `storebro.hull.build_hull` and produces six parametric FreeCAD Bodies in the hull's document: `DeckPlate` (3D solid of thickness 25 mm), `CabinTrunk` (rounded-corner prism with the documented fillet radius), `Windshield` (inclined face raked aft), `Hardtop` (flat roof with documented overhangs), `HardtopPillars` (two mirrored aft support pillars), and `Railings` (continuous perimeter rail loop). All six mirror about the X-Z plane (FR-009); the deck plate's underside aligns with the hull's sheer line within 1 µm (SC-009). Failures mid-build roll back any Bodies already added to the document (SC-008).

Cross-module dependency: this is the project's first non-leaf module. It imports `storebro.hull` for the `Hull` type and `storebro._freecad_check` for the shared lazy version check. It MUST NOT import `storebro.export`, `storebro.interior`, or `storebro.cli` (FR-011, mirroring spec 002's amended FR-013 pattern).

Technical approach: a single `src/storebro/deck.py` module exposing the public function + return aggregate + 2 exception classes + a `DeckParameters` frozen dataclass. Each of the six Bodies is built by a private `_build_<element>(hull, parameters, target_doc) -> Body` helper. The rollback discipline is implemented by collecting added objects in a list as they're created and removing them from the document via `target_doc.removeObject(name)` if any helper raises before all six finish.

## Technical Context

**Language/Version**: Python 3.11+ (matches FreeCAD 1.1's bundled CPython).

**Primary Dependencies**: FreeCAD 1.1+ Python API (`FreeCAD`, `Part`, `Sketcher`). The deck module additionally depends on `storebro.hull` (for the `Hull` type) and `storebro._freecad_check` (shared lazy version check). No third-party Python packages.

**Storage**: N/A. The deck module operates on an in-memory FreeCAD document; `.FCStd` persistence is spec 002's responsibility.

**Testing**: `pytest` ≥ 8.x with the two markers from spec 001/002 (`unit`, `requires_freecad`). New geometry tests cover the six Bodies plus the cross-module integration (hull → deck wiring).

**Target Platform**: Ubuntu 22.04/24.04 + macOS 14+, Python 3.11/3.12, FreeCAD 1.1+. Same matrix as spec 001/002.

**Project Type**: Python library extension. Adds `storebro.deck` to the existing `src/storebro/` package; no new top-level structure.

**Performance Goals**: Default deck on default hull builds in under 45 seconds (SC-002). Combined with the 30-second hull budget, whole-boat (hull + deck) stays under 75 seconds — well inside the "human-scale seconds" wall-clock budget.

**Constraints**:
- Structural determinism for fixed `(Hull, DeckParameters)` (FR-005, SC-003).
- Reference fidelity: cabin trunk length / hardtop length / railing height match RC34 1972 ±1% (FR-003, SC-001).
- FreeCAD-idiomatic: `Part`, `Sketcher` (and v0.2.0 PartDesign upgrade target). Zero `Mesh.Mesh` in the deck module (FR-006).
- Cross-module dependency arrow: `storebro.deck` imports `storebro.hull` (allowed) and `storebro._freecad_check` (allowed, shared helper). Banned: `interior`, `export`, `cli` (FR-011).
- Document binding: deck Bodies always go into `hull.document`; cross-document deck building is rejected (FR-016).
- No logging or telemetry in v1.0 (matches spec 001 clarify Q4 and spec 002).

**Scale/Scope**: Single Python module `src/storebro/deck.py`. One public function, four public types (1 dataclass + 1 return aggregate + 2 exception classes). ~6-10 private helpers (one per sub-Body, plus a rollback helper, plus a parameter validator). Test surface: ~25-40 tests split unit (path/extension/validation/exception) vs geometry (per-Body shape checks + parametricity + rollback).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against `.specify/memory/constitution.md` v1.0.0:

| Principle | Status | Evidence |
|---|---|---|
| **I. Parametric Everything** | PASS | Every deck dimension is a named field on `DeckParameters` (FR-002, FR-008 — 14 named params). No magic numbers in spec or planned implementation. |
| **II. Reproducibility (NON-NEGOTIABLE)** | PASS | FR-005 + SC-003 require structural determinism. Same construction strategy used in spec 001 (fixed feature order, deterministic constraint application). Byte-identical bytes are spec 002's contract. |
| **III. FreeCAD-Idiomatic** | PASS | FR-006: `Part`, `Sketcher`, and v0.2.0 PartDesign target. Zero `Mesh.Mesh` in deck module. |
| **IV. Reference Fidelity** | PASS | FR-003 + SC-001 require ±1% on principal deck dimensions vs RC34 1972 reference. Defaults pinned in research.md R1. |
| **V. Test-Gated Releases** | PASS | SC-006 (per-public-surface tests, including per-sub-Body), SC-007 (≥7 invalid-input cases), SC-008 (rollback test), SC-009 (sheer alignment test). Ruff + mypy --strict CI-enforced as in spec 001/002. |
| **VI. Public OSS by Default** | PASS | MIT project. Public API: 1 function + 4 types. Semver MAJOR bump required for breaking changes. |
| **VII. FreeCAD Version Discipline** | PASS | FR-013 reuses the shared `storebro._freecad_check` helper. Range declared in `pyproject.toml`; hash baselines per FreeCAD version are spec 002's concern. |

**Gates pass. No violations to justify in Complexity Tracking.**

## Project Structure

### Documentation (this feature)

```text
specs/003-deck-module/
├── plan.md
├── spec.md
├── spec.allium
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── python-api.md
├── checklists/
│   └── requirements.md
└── tasks.md            # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

Extends the existing src-layout. The deck module is a single file unless complexity grows enough to justify a package (each sub-Body helper is internal and small, so one file is correct).

```text
src/storebro/
├── __init__.py         # Re-exports new public surface from storebro.deck
├── hull.py             # (existing — spec 001)
├── _freecad_check.py   # (existing — spec 001, reused for FR-013 version check)
├── export.py           # (existing — spec 002)
└── deck.py             # NEW: build_deck() + DeckParameters + Deck + 2 exception classes + 6 private builders

tests/
├── unit/
│   ├── test_deck_parameters.py     # DeckParameters validation, defaults, frozen behaviour
│   ├── test_deck_errors.py         # DeckParameterError / DeckConstructionError attributes
│   └── test_deck_leaf_dependencies.py  # FR-011: imports hull + _freecad_check only
└── geometry/
    ├── test_deck_default_call.py            # build_deck() smoke + 6 Bodies present
    ├── test_deck_default_dimensions.py      # SC-001: ±1% on citation-grade dims
    ├── test_deck_sheer_alignment.py         # SC-009: deck plate underside vs hull sheer
    ├── test_deck_symmetric.py               # FR-009: all 6 Bodies symmetric about centerline
    ├── test_deck_parametricity.py           # SC-004: every named param moves geometry
    ├── test_deck_determinism.py             # SC-003: structural determinism for fixed inputs
    ├── test_deck_construction_rollback.py   # SC-008: forced failure mid-build → no orphan Bodies
    ├── test_deck_document_mismatch.py       # FR-016: cross-doc rejection
    └── test_deck_visual_signoff.py          # T049-equivalent: save .FCStd for manual GUI review

docs/examples/
└── deck_quickstart.py  # Runnable example: build_hull → build_deck → export_fcstd
```

**Structure Decision**: **single src-layout Python module**. `storebro.deck` is one file, reuses spec 001/002 scaffolding (conftest, fixtures, version check). Tests follow the same unit-vs-geometry split. The deck module is the first to import other public storebro modules — the FR-013-style amended leaf-module test verifies `storebro.hull` is the only public sibling permitted.

## Complexity Tracking

> No Constitution Check violations. Section intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
