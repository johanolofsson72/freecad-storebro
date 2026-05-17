# Implementation Plan: PartDesign Hull Upgrade

**Branch**: `006-partdesign-hull-upgrade` | **Date**: 2026-05-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-partdesign-hull-upgrade/spec.md`

## Summary

Rebuild the hull's internal FreeCAD feature graph using the PartDesign workbench exclusively. Replace the v0.1.0-alpha trio of `Part::Loft` + `Part::Mirroring` + `Part::MultiFuse` (which `PartDesign::Body` containers reject in FreeCAD 1.1+, causing `ValueError: Body: object is not allowed`) with a clean PartDesign feature graph: 5 `Sketcher::SketchObject` station sketches attached to 5 `PartDesign::Plane` Body-local datum planes, one `PartDesign::AdditiveLoft` that consumes the sketches in canonical order to build the half-hull, and one `PartDesign::Mirrored` that reflects the loft across the Body's XZ plane to produce the closed full-hull solid. `Body.Tip` is set to the mirror feature so `hull.body.Shape` reads the full hull.

The public `Hull` dataclass surface stays identical: same five fields, same eight named informational properties on the Body, same `HullConstructionError` exception type with the same attributes. Spec 002 / 003 / 004 / 005 consumers continue to work without source changes. The 86 currently-failing geometry tests pass on FreeCAD 1.1.1 once the implementation lands.

Technical approach: surgical replacement of two private functions in `src/storebro/hull.py`:
- `_create_station_sketch(profile, body, parent_doc)` — switches from `parent_doc.addObject("Part::Feature", ...)` to `body.newObject("Sketcher::SketchObject", ...)` with a `PartDesign::Plane` datum created first via `body.newObject("PartDesign::Plane", ...)`, both anchored to `Body.Origin.YZ_Plane` with an X-offset.
- `_apply_loft_and_mirror(body, sketches, parent_doc)` — switches from `parent_doc.addObject("Part::Loft" | "Part::Mirroring" | "Part::MultiFuse", ...)` to `body.newObject("PartDesign::AdditiveLoft", ...)` + `body.newObject("PartDesign::Mirrored", ...)`, with `Body.Tip = mirror_feature`.

All other code in `hull.py` (parameter validation, `_compute_stations`, `_resolve_document`, `_resolve_body_label`, `_bind_parameters_to_body_properties`, the `Hull` dataclass, the `build_hull` orchestration) stays unchanged. The fix is geographically tight: ~2 functions × ~40 lines each.

## Technical Context

**Language/Version**: Python 3.11+ (matches FreeCAD 1.1's bundled Python).

**Primary Dependencies**: FreeCAD 1.1+ Python API — specifically `FreeCAD`, `Part`, `Sketcher`, `PartDesign`. Standard library: `math`, `time`, `dataclasses`. No new third-party dependencies.

**Storage**: N/A — hull construction operates on FreeCAD documents in memory.

**Testing**: pytest with existing markers (`unit`, `requires_freecad`). All 86 currently-failing geometry tests live under `tests/geometry/` and use the `requires_freecad` marker. Unit tier (`tests/unit/`) is unchanged — the rebuild is FreeCAD-side only.

**Target Platform**: Cross-platform: Ubuntu, macOS (Darwin arm64 + x86_64), Windows. Tested host for this spec: macOS Darwin arm64 with FreeCAD 1.1.1 installed at `/Applications/FreeCAD.app`.

**Project Type**: Python library + console script. No new files; replaces internal implementation of `src/storebro/hull.py`.

**Performance Goals**: `build_hull()` < 30 s on a developer laptop (same as v0.1.0-alpha budget per SC-002). PartDesign overhead is expected to be modest; if measured > 39 s (30 % slip) the spec escalates to a separate optimization spec.

**Constraints**:
- Public API surface frozen (FR-005, FR-006, FR-011): no fields added/removed/renamed.
- Byte-deterministic output (FR-008): same parameters → identical `.FCStd` bytes across runs.
- FreeCAD-idiomatic (constitution III): no raw mesh manipulation, no legacy Part-workbench features inside the Body.
- Backward-compatible for all 4 downstream modules (spec 002-005): they consume `hull.body.Shape` + `hull.document` — both must continue to point at valid FreeCAD objects.
- Rollback discipline on construction failure (FR-012): no orphan sketches, datum planes, or half-built Body left in the document.

**Scale/Scope**: 1 source file modified (`src/storebro/hull.py`), 2 private functions rewritten (~80 lines total replacement), 0 new files in `src/`. Hash baselines refresh in `tests/geometry/fixtures/expected_hashes.toml` (auto-regenerated). Test surface: 86 existing tests that should turn from FAIL to PASS, plus 2-3 new tests that explicitly assert PartDesign feature types (e.g., `assert body.AdditiveLoft.TypeId == "PartDesign::AdditiveLoft"`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|---|---|---|
| **I. Parametric Everything** | PASS | `_compute_stations` continues to derive every station-profile dimension from `HullParameters`. No magic numbers introduced. The eight named Body properties remain as before. |
| **II. Reproducibility (NON-NEGOTIABLE)** | PASS | PartDesign feature recompute is deterministic at fixed parameters. SC-004 + FR-008 verified by `test_hull_determinism.py` post-implementation. Hash baselines refresh per spec 002's `refresh_hashes.py`. |
| **III. FreeCAD-Idiomatic** | **PASS (was the violation root)** | The whole point of this spec: replace legacy Part-workbench features with PartDesign equivalents. No `Mesh.Mesh` introduced. PartDesign Body remains the editable container. |
| **IV. Reference Fidelity** | PASS | `_compute_stations` profile math is preserved verbatim (FR-014 + spec.allium `ProfileFromCanonicalEquations`). LOA, beam, draft remain within ±1% of RC34 1972 reference. |
| **V. Test-Gated Releases** | PASS | 86 existing geometry tests turn green. New PartDesign-feature assertion tests added. CI matrix unchanged. |
| **VI. Public OSS by Default** | PASS | Public API frozen — no breaking changes. MIT license unchanged. v1.0.0 versions across all 5 modules align. |
| **VII. FreeCAD Version Discipline** | PASS | Supported range `>=1.1, <2.0` unchanged. The rebuild uses PartDesign features that have been stable since FreeCAD 0.19, well within the supported range. |

**Gates pass.**

## Project Structure

### Documentation (this feature)

```text
specs/006-partdesign-hull-upgrade/
├── plan.md
├── spec.md
├── spec.allium
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── python-api-preserved.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code

```text
src/storebro/
├── __init__.py             # unchanged (no public API change)
├── __main__.py             # unchanged
├── _freecad_check.py       # unchanged
├── hull.py                 # MODIFIED — _create_station_sketch + _apply_loft_and_mirror rewritten
├── export.py               # unchanged
├── deck.py                 # unchanged
├── interior.py             # unchanged
├── cli.py                  # unchanged
└── fixtures/               # unchanged

tests/
├── unit/                   # unchanged — no FreeCAD needed at unit tier
└── geometry/
    ├── test_hull_*.py      # ALREADY EXISTS — turn from FAIL to PASS
    ├── test_deck_*.py      # ALREADY EXISTS — turn from FAIL to PASS (depend on hull)
    ├── test_export_*.py    # ALREADY EXISTS — turn from FAIL to PASS (depend on hull)
    ├── test_interior_*.py  # ALREADY EXISTS — turn from FAIL to PASS (depend on hull)
    ├── test_cli_build_*.py # ALREADY EXISTS — turn from FAIL to PASS (depend on hull)
    ├── test_hull_partdesign_feature_types.py  # NEW — asserts PartDesign feature types
    └── fixtures/
        └── expected_hashes.toml  # REGENERATED via refresh_hashes.py
```

**Structure Decision**: **single src-layout Python module with targeted private-function replacement**. The fix scope is constrained to two private functions in `src/storebro/hull.py` and one new test file. No public API change, no new source files. The PartDesign feature graph is constructed via `body.newObject("PartDesign::X", name)` (the FreeCAD-idiomatic way to add features to a Body) rather than `parent_doc.addObject(...)` followed by `body.addObject(...)` (which is what broke v0.1.0-alpha).

## Complexity Tracking

> No Constitution Check violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| — | — | — |
