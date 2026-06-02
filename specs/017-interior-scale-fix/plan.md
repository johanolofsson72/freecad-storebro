# Implementation Plan: Interior Scale Fix

**Branch**: `master` (solo, direct-push — no feature branches per project workflow) | **Date**: 2026-06-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/017-interior-scale-fix/spec.md`

## Summary

The interior module emits compartment and furniture geometry by feeding metre-magnitude layout values straight into FreeCAD's millimetre-internal geometry calls, producing an interior ~1000× too small relative to the mm-scale hull. The fix introduces a single named metre→millimetre constant (mirroring `hull._MM_PER_M`) and applies it uniformly at the geometry-construction boundary in `_build_compartment` and the spec 012/013 furniture builders, so the interior nests inside the hull at true scale. Validators stay in metre-space; the public API is unchanged; scale-sensitive tests are updated to millimetres and a regression test pins the corrected magnitude.

## Technical Context

**Language/Version**: Python 3.11+ (matches FreeCAD 1.1 bundled CPython 3.11.14)

**Primary Dependencies**: FreeCAD 1.1+ (`Part` workbench), PyYAML (fixtures). No new dependencies.

**Storage**: YAML layout fixtures (`src/storebro/fixtures/Alternativ1–5.yaml`) — unchanged, authored in metres.

**Testing**: pytest (`-m requires_freecad` for the geometry tier; unit tier runs without FreeCAD), ruff, mypy --strict.

**Target Platform**: FreeCAD 1.1+ on macOS / Linux (CI: Ubuntu + macOS × Python 3.11/3.12).

**Project Type**: Single-project Python library (`src/storebro/`).

**Performance Goals**: Human-scale geometry build time (seconds); unchanged by a scale-constant multiply.

**Constraints**: Byte-identical reproducibility (constitution II); no magic numbers in geometry bodies (constitution I); FreeCAD-idiomatic `Part` solids only (constitution III).

**Scale/Scope**: One source module (`src/storebro/interior.py`) + scale-sensitive interior geometry tests. No public API change.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Parametric Everything | ✅ PASS | The fix *removes* an implicit magic convention. FR-005 mandates a single named constant (`_M_TO_MM` / reuse of the hull convention) instead of scattered literal `1000`/`1/1000` multipliers. Hardcoded metre literals in furniture builders are converted to mm but remain the same kind of in-body construction constants they already were (pre-existing; out of scope to parameterise here — tracked, not worsened). |
| II. Reproducibility (NON-NEGOTIABLE) | ✅ PASS | A uniform constant multiply introduces no nondeterminism, no timestamps, no ordering change. SC-005 asserts byte-identical repeat builds. |
| III. FreeCAD-Idiomatic | ✅ PASS | No change to construction technique — still `Part.makeBox` / `Part::Feature` / `Part::Compound` B-rep solids. Only operand magnitude changes. |
| IV. Reference Fidelity | ✅ PASS (improves) | Corrects the interior to true proportions inside the hull; brings the interior into the ±1% reference-fidelity regime it could never reach at 1000× error. |
| V. Test-Gated Releases | ✅ PASS | pytest + ruff + mypy --strict gate the change; scale-sensitive tests updated (FR-011) + regression test added (FR-012); GUI eyeball is the maintainer pre-tag step. |
| VI. Public OSS by Default | ✅ PASS | No public API change (FR-010) → PATCH bump under semver. MIT unaffected. |
| VII. FreeCAD Version Discipline | ✅ PASS | No new FreeCAD API surface; the existing supported-version gate is untouched. |

**Result**: All gates pass. No violations → Complexity Tracking section omitted.

## Project Structure

### Documentation (this feature)

```text
specs/017-interior-scale-fix/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (no new entities — scale note)
├── quickstart.md        # Phase 1 output (verification recipe)
├── checklists/
│   └── requirements.md  # Spec quality checklist (from /specify)
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
src/storebro/
└── interior.py          # ONLY production file touched (geometry construction + furniture builders)

tests/
├── unit/                # interior unit tests — metre-space / scale-agnostic → expected unchanged
└── geometry/
    ├── test_interior_berth_salon.py        # _within() helper → scale spec-derived bounds ×1000
    ├── test_interior_*furnished*.py         # verify within-envelope assertions survive at mm
    └── test_interior_scale.py (NEW)         # FR-012 regression: 2.4 m cabin → ~2400 mm BoundBox
```

**Structure Decision**: Single-project Python library. The change is confined to `src/storebro/interior.py` (the geometry-construction boundary) plus scale-sensitive tests under `tests/geometry/`. No other module reads interior geometry magnitude, so the blast radius is one module.

## Implementation approach (the fix)

1. **Introduce the constant.** Add a module-level `_M_TO_MM = 1000.0` to `interior.py`, mirroring `hull._MM_PER_M`. This is the single conversion authority (FR-005).
2. **Scale compartment geometry.** In `_build_compartment`, multiply `length`/`width`/`height` and `position.x`/`position.z` (and the derived `half_w`) by `_M_TO_MM` before `Part.makeBox` / `translate`. Leave the GUI `Length`/`Width`/`Height` property assignments as-is (already ×1000 → now consistent with geometry; FR-008 — do not double-scale).
3. **Fix furniture-to-mm.** The furniture builders currently use `_MM_TO_UNIT = 1/1000` to shrink mm params down to the broken metre boxes. After the fix, furniture parameters (already mm) are used at face value, and metre-space inputs (`spec.dimensions.*`, `spec.position.*`) and the hardcoded metre literals (insets `0.05`/`0.1`, fitting sizes `0.5`/`0.4`/`0.3`/`0.15`, settee `0.5`, table `0.04`/`0.08`, etc.) are converted to mm. Concretely: drop the `_MM_TO_UNIT` shrink from the param path; express spec-derived dimensions via `* _M_TO_MM`; restate the literal metre constants as their mm equivalents.
4. **Keep validators in metre-space.** `_validate_compartment_in_envelope`, `_aabb_intersection_volume`/`_validate_no_overlaps`, and `_validate_furniture_envelope` compare layout metres against hull-parameter metres. They must keep doing the comparison in metres — the furniture-envelope validator keeps its own metre conversion (compare furniture-mm-as-metres against compartment-metre height) rather than borrowing the geometry-path constant (FR-007).
5. **Update scale-sensitive tests + add regression.** `_within()` in `test_interior_berth_salon.py` scales the spec-derived envelope by 1000. Scan the other interior geometry tests for absolute-coordinate assertions and lift them to mm; leave positive/relative-volume assertions alone. Add `test_interior_scale.py` asserting the Alternativ1 forward cabin (2.4 m) → BoundBox XLength within ±1% of 2400 mm (FR-012), and an interior-nests-in-hull bounding-box containment check (SC-003).
6. **Bump version.** PATCH bump (`__version__`) + the version-consistency test, consistent with prior spec-only releases.

## Complexity Tracking

No constitution violations. Section intentionally empty.
