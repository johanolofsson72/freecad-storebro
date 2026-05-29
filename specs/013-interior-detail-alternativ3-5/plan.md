# Implementation Plan: Interior Detail — Alternativ3, 4 & 5

**Branch**: `master` (solo, direct-push) | **Date**: 2026-05-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/013-interior-detail-alternativ3-5/spec.md`

## Summary

Extend the spec 012 type-keyed furniture builders to Alternativ3/4/5 by widening the `_FURNISHED_LAYOUTS` gate in `interior.py` from `{Alternativ1, Alternativ2}` to all five canonical layout names. The builders, parameter dataclasses, validation, manifold guard, and rollback are reused unchanged. The per-compartment-type dispatch already handles Alt5's missing galley (no galley compartment → no galley furniture). Custom (non-canonical) YAML layouts keep boxy placeholders. The only production change is the gate constant; the bulk of the work is per-layout test coverage + repurposing spec 012's gate test. PATCH bump 1.0.6 → 1.0.7.

## Technical Context

**Language/Version**: Python 3.11+ (FreeCAD 1.1 bundled Python)

**Primary Dependencies**: existing (`Part`, `FreeCAD`, PyYAML); no new deps

**Testing**: pytest — `tests/unit/` + `tests/geometry/` (marker `requires_freecad`)

**Project Type**: Single-project Python library

**Constraints**: reproducibility (II); ±1% fidelity (IV); Part-workbench B-rep (III) — all inherited from spec 012 unchanged

**Scale/Scope**: one constant changed in `interior.py`; version bump; ~6 new geometry tests + repurpose 1 existing test. No new public API.

## Constitution Check

| Principle | Status |
|---|---|
| I. Parametric | PASS — furniture params unchanged from spec 012 |
| II. Reproducibility | PASS — shared builders; SC-004 |
| III. FreeCAD-Idiomatic | PASS — no construction change |
| IV. Reference Fidelity | PASS — defaults fit Alt3/4/5 envelopes (verified vs fixtures) |
| V. Test-Gated | PASS (planned) — pytest + ruff + mypy; signoff |
| VI. Public OSS / SemVer | PASS — no new public API; PATCH bump |
| VII. FreeCAD Version Discipline | PASS — no range change |

No violations. **Inherited verification risk** (specs 010–012): the geometry tier cannot run without FreeCAD. Spec 013 adds no new construction, only enables existing builders on three more layouts, so the incremental risk is just "do the default furniture dims fit the Alt3/4/5 envelopes" — verified against the fixtures during planning (all fit; Alt5 has no galley).

## Project Structure

```text
specs/013-interior-detail-alternativ3-5/
├── plan.md  spec.md  spec.allium  research.md  data-model.md  quickstart.md
├── contracts/python-api.md  checklists/requirements.md  tasks.md

src/storebro/
├── interior.py   # MODIFIED — _FURNISHED_LAYOUTS widened to all 5 canonical
│                 #   names (one constant)
├── __init__.py   # MODIFIED — __version__ 1.0.7 (no new exports)
└── (rest UNCHANGED)

pyproject.toml    # MODIFIED — 1.0.6 → 1.0.7

tests/
├── unit/         # MODIFIED — version test → 1.0.7
└── geometry/     # NEW requires_freecad: Alt3/Alt4/Alt5 furnished, Alt5 no-galley,
               #   default-fit, determinism; MODIFIED test_interior_gate.py
               #   (now asserts all 5 canonical furnished + custom boxy)
```

**Structure Decision**: The change is a one-constant gate widening. All furniture logic stays in `interior.py` from spec 012. No data-model or contract change beyond the gate set.

## Verification risk

FreeCAD not on host → geometry tier + GUI signoff WRITTEN but PENDING (fourth consecutive spec touching geometry). Spec 013 adds no new geometry construction, so its incremental risk is minimal — the shared builders are the same code spec 012 exercised. Unit + ruff + mypy gate locally.

## Complexity Tracking

No constitution violations — table intentionally empty.
