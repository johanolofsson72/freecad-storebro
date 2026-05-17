# Implementation Plan: Export Module

**Branch**: `002-export-module` | **Date**: 2026-05-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-export-module/spec.md`

## Summary

Implement the four writers (`.FCStd`, STEP, STL, BREP) for `storebro.export`. Every writer produces SHA-256-identical bytes for the same input and FreeCAD version — the project's NON-NEGOTIABLE constitution II invariant verified by hash-pinned regression tests. STEP uses AP214 schema, STL uses 1 mm absolute linear chord deviation as the default tessellation, BREP and `.FCStd` use FreeCAD's native serializers (with a post-processing zip-scrub pass for `.FCStd` to strip timestamps, user/host metadata, and non-deterministic zip-entry ordering). All writers go through an atomic-rename discipline (tmp-sibling-write + `os.replace`); rename failure raises `ExportWriteError` rather than falling back to a copy+delete that would lose atomicity. Subshape ordering inside every format follows a centroid-then-`ShapeType` lex sort applied recursively into Compound children, so byte-identical reproducibility survives FreeCAD-internal element reshuffling.

Technical approach: a single `src/storebro/export.py` module exporting four functions (`export_step`, `export_stl`, `export_brep`, `export_fcstd`) plus the two public exception classes (`ExportInputError`, `ExportWriteError`) plus the `ExportArtifact` return type. Format-specific work is delegated to private helpers (`_canonicalize_step_header`, `_scrub_fcstd_zip`, `_sort_shape_recursively`, etc.) that each handle one well-defined determinism concern.

## Technical Context

**Language/Version**: Python 3.11+ (matches FreeCAD 1.1's bundled CPython, same as spec 001).

**Primary Dependencies**: FreeCAD 1.1+ Python API (`FreeCAD`, `Part`, `Mesh`, `MeshPart`). Standard library `pathlib`, `tempfile`, `hashlib`, `zipfile`, `re`, `io`. No third-party Python packages.

**Storage**: Files on the local filesystem. Atomic rename relies on POSIX `os.replace` semantics inside a single filesystem.

**Testing**: `pytest` ≥ 8.x with the two markers from spec 001 (`unit`, `requires_freecad`). New convention: SHA-256 hash baselines live in `tests/geometry/fixtures/expected_hashes.toml` keyed by `(format, freecad_version, source_hash, kwargs_hash)` so a FreeCAD-version bump is a TOML edit, not a test rewrite.

**Target Platform**: Ubuntu 22.04/24.04 + macOS 14+ (Apple Silicon + Intel). Python 3.11 + 3.12. FreeCAD 1.1+. Windows is out of scope per spec.md Assumptions.

**Project Type**: Python library extension. Adds `storebro.export` to the existing `src/storebro/` package; no new top-level structure. Same src-layout as spec 001.

**Performance Goals**: Default-hull exports complete within these wall-clock budgets on a developer laptop: STEP ≤ 5 s, STL ≤ 10 s, BREP ≤ 3 s, `.FCStd` ≤ 3 s (SC-002).

**Constraints**:
- Byte-identical SHA-256 for fixed `(source object, target path, writer kwargs, FreeCAD version)` (constitution II, FR-002, SC-001).
- LF line endings on every supported OS for text-formatted outputs (FR-016).
- STL is the only mesh emitter (FR-012, constitution III mesh-export adapter exception).
- Leaf module — `storebro.export` does NOT import any other `storebro.*` module (FR-013).
- No telemetry / no logging in v1.0 (matches spec 001 clarify Q4).

**Scale/Scope**: Single Python module `src/storebro/export.py`. Four public functions, three public types (one return aggregate + two exception classes). 6-10 private helpers. Test surface: ~30-50 tests split unit (path/extension/validation) vs geometry (actual file writes with hash assertions).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against `.specify/memory/constitution.md` v1.0.0:

| Principle | Status | Evidence |
|---|---|---|
| **I. Parametric Everything** | PASS | Every writer kwarg is a named parameter with a documented default. No magic numbers in the spec or planned implementation. |
| **II. Reproducibility (NON-NEGOTIABLE)** | PASS | This is the spec's central invariant. FR-002, FR-003, FR-004, FR-005, FR-016, FR-018, FR-019, FR-020 all reinforce it; SC-001 is the gate. Implementation strategy below pins canonical orderings, scrubs timestamps, and produces hash-pinned regression tests. |
| **III. FreeCAD-Idiomatic** | PASS | Writers delegate to FreeCAD's native `Part.export`, `Shape.exportBrep`, `Mesh.export`, and `Document.save` APIs. The STL writer is the ONLY one allowed to touch `Mesh.Mesh` (FR-012); BREP/STEP/.FCStd stay in B-rep land. |
| **IV. Reference Fidelity** | N/A | This spec produces files from arbitrary FreeCAD shapes; reference fidelity belongs to spec 001 (hull defaults). |
| **V. Test-Gated Releases** | PASS | SC-005 (unit + geometry test per writer), SC-007 (forced-failure test per writer), SC-008 (STL watertight check), hash-pinned regression baselines. Ruff + mypy --strict CI-enforced as in spec 001. |
| **VI. Public OSS by Default** | PASS | Module is MIT (project license). Public API: 4 functions + 3 types. Semver MAJOR bump required for breaking changes. |
| **VII. FreeCAD Version Discipline** | PASS | FR-014 mirrors hull spec's FR-013: lazy first-call version check, range from `pyproject.toml`. Hash baselines are pinned per FreeCAD version (FR-002 + research R6) — a version bump invalidates the baseline by design, which is acceptable provided the CHANGELOG documents it. |

**Gates pass. No violations to justify in Complexity Tracking.**

## Project Structure

### Documentation (this feature)

```text
specs/002-export-module/
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

Extends the existing src-layout from spec 001. The export module is a single file unless internal complexity grows enough to justify a package.

```text
src/storebro/
├── __init__.py          # Re-exports the new public surface from storebro.export
├── hull.py              # (existing — spec 001)
├── _freecad_check.py    # (existing — spec 001, reused for FR-014 version check)
└── export.py            # NEW: 4 writer functions + ExportArtifact + 2 exception classes + private helpers

tests/
├── unit/
│   ├── test_export_paths.py        # Path / extension / overwrite validation, ExportInputError shape
│   └── test_export_errors.py       # ExportInputError / ExportWriteError attributes + subclassing
└── geometry/
    ├── fixtures/
    │   └── expected_hashes.toml    # SHA-256 baselines keyed by (format, freecad_version, source_hash, kwargs_hash)
    ├── test_export_fcstd.py        # .FCStd writer end-to-end + hash baseline
    ├── test_export_step.py         # STEP writer end-to-end + hash baseline
    ├── test_export_stl.py          # STL writer end-to-end + hash baseline + watertight check
    ├── test_export_brep.py         # BREP writer end-to-end + hash baseline
    ├── test_export_determinism.py  # Two back-to-back writes per format → identical bytes
    ├── test_export_atomicity.py    # Forced FreeCAD failure mid-write → no partial file
    └── test_export_leaf_module.py  # FR-013 import-isolation check

docs/examples/
└── export_quickstart.py  # Runnable example: build hull, export to all four formats
```

**Structure Decision**: **single src-layout Python module**. `storebro.export` is one file. No new top-level directory. Tests follow the same unit-vs-geometry split as spec 001, plus a new `fixtures/expected_hashes.toml` for the hash baselines (TOML is human-readable and stdlib-parseable via `tomllib`).

## Complexity Tracking

> No Constitution Check violations. Section intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
