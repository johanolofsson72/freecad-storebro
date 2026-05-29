# Implementation Plan: Basic Deck Hardware

**Branch**: `master` (solo, direct-push) | **Date**: 2026-05-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/010-deck-hardware-basic/spec.md`

## Summary

Add five classes of basic deck hardware — rubrail, bow pulpit, lifelines, anchor locker, cleats — to the deck built by `storebro.deck.build_deck`. Each is a FreeCAD `PartDesign::Body` (or a `Part::Compound` of bodies), parameterized by a frozen mm-unit dataclass with `__post_init__` validation that raises `DeckParameterError`, seated on the ACTUAL sampled hull/deck geometry via the existing `_sample_hull_sheer` / `_resolve_deck_top_z_at` helpers, and built by default so existing callers receive the hardware automatically. The work directly mirrors the spec 008 superstructure idiom (datum planes + sketches + Pad/Loft features, rollback discipline, mutually-exclusive parameter handling) and implements the spec 008 deferred item `SuperstructureBundle.rubrail`. PATCH bump 1.0.3 → 1.0.4; additive public API only; `storebro.__version__` corrected to match `pyproject.toml`.

## Technical Context

**Language/Version**: Python 3.11+ (matches FreeCAD 1.1 bundled Python)

**Primary Dependencies**: FreeCAD 1.1+ Python API (`Part`, `Sketch`, `PartDesign`, `FreeCAD`); no new third-party deps

**Storage**: N/A (geometry is returned as in-memory FreeCAD objects; persistence is the export module's job)

**Testing**: pytest — `tests/unit/` (no FreeCAD) + `tests/geometry/` (marker `requires_freecad`)

**Target Platform**: macOS + Ubuntu × Python 3.11/3.12 (CI matrix), FreeCAD 1.1.1

**Project Type**: Single-project Python library (`src/storebro/`)

**Performance Goals**: human-scale seconds for a full `build_deck`; no hard latency budget (constitution priority 5)

**Constraints**: byte-identical reproducibility (constitution II); ±1% reference fidelity on principal dimensions (constitution IV); FreeCAD-idiomatic B-rep only, no raw mesh (constitution III); `deck.py` may import only `storebro.hull` and `storebro._freecad_check` (FR-020)

**Scale/Scope**: one module touched (`deck.py`, +~700 lines), one dunder fix (`__init__.py`), one version bump (`pyproject.toml`); ~5 new parameter dataclasses + 1 composite + 5 builder functions + 5 wrappers + Deck aggregate extension; ~30 new tests

## Constitution Check

*GATE: must pass before Phase 0 and re-checked after Phase 1.*

| Principle | Gate | Status |
|---|---|---|
| I. Parametric Everything | Every hardware dimension is a named dataclass field with a default; no magic numbers in builder bodies | PASS — all dims flow from the 5 parameter dataclasses + `config` defaults |
| II. Reproducibility (NON-NEGOTIABLE) | No timestamps/random/env in hardware geometry; identical inputs → identical bytes | PASS — builders are pure functions of (hull, deck, params); SC-004 + `DeterministicShapeDigest` invariant assert it |
| III. FreeCAD-Idiomatic | PartDesign bodies + sketches + Pad/Loft; no raw mesh outside export adapters | PASS — FR-002; matches spec 008 idiom exactly |
| IV. Reference Fidelity | Defaults within ±1% of Alternativ3.JPG on principal dims | PASS — FR-015 + `ReferenceFidelityWithinOnePercent` invariant; per-instance fine detail exempt |
| V. Test-Gated Releases | pytest + ruff + mypy --strict green; manual FreeCAD visual signoff | PASS (planned) — SC-008 + visual signoff test mirroring `test_deck_visual_signoff.py` |
| VI. Public OSS by Default | Additive API only; PATCH bump; no breaking change | PASS — FR-019; new dataclasses + new `parameters_hardware` kwarg, nothing removed |
| VII. FreeCAD Version Discipline | No FreeCAD version range change | PASS — no API-break shim needed; range unchanged in pyproject |

No violations. Complexity Tracking table omitted (nothing to justify).

## Project Structure

### Documentation (this feature)

```text
specs/010-deck-hardware-basic/
├── plan.md              # This file
├── spec.md              # Feature spec (+ Clarifications)
├── spec.allium          # Formal spec (elicited)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── python-api.md    # Public API contract
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
src/storebro/
├── deck.py          # MODIFIED — 5 hardware parameter dataclasses, 1 composite,
│                    #   5 wrapper dataclasses, 5 _build_* functions, Deck aggregate
│                    #   extension, build_deck() new `parameters_hardware` kwarg
├── __init__.py      # MODIFIED — export new dataclasses; bump __version__ to 1.0.4
└── (hull.py, export.py, interior.py, cli.py — UNCHANGED)

pyproject.toml       # MODIFIED — version 1.0.3 → 1.0.4

tests/
├── unit/            # NEW — per-dataclass validation tests (no FreeCAD):
│                    #   test_rubrail_parameters.py, test_bow_pulpit_parameters.py,
│                    #   test_lifeline_parameters.py, test_anchor_locker_parameters.py,
│                    #   test_cleat_parameters.py, test_deck_hardware_parameters.py
│                    # MODIFIED — test_deck_destructive_validation.py (hardware branches),
│                    #   test_deck_public_docstrings.py, test_deck_back_compat.py
└── geometry/        # NEW — FreeCAD integration (marker requires_freecad):
                     #   test_deck_hardware_default_call.py, test_deck_hardware_rubrail_sheer.py,
                     #   test_deck_hardware_symmetric.py, test_deck_hardware_determinism.py,
                     #   test_deck_hardware_rollback.py, test_deck_hardware_zero_counts.py,
                     #   test_deck_hardware_partdesign_feature_types.py,
                     #   test_deck_hardware_anchor_locker_placement.py,
                     #   test_deck_hardware_lifeline_no_posts.py,
                     #   test_deck_hardware_cleat_seating.py,
                     #   test_deck_hardware_visual_signoff.py
                     # MODIFIED — test_deck_default_call.py, test_deck_default_labels.py
                     #   (body-count assertions now include hardware)
```

**Structure Decision**: Single-project library, flat-module-per-body-part (constitution "Module Layout"). All new geometry lives in `deck.py` — it already owns the deck superstructure and the sheer/deck-top sampling helpers the hardware needs. No new module is warranted; hardware is conceptually part of the deck and shares the deck's hull/deck-plate inputs. This keeps the FR-020 import constraint trivially satisfied (no new cross-module edges).

## Build Sequence (dependency order within build_deck)

1. deck_plate → cabin_trunk → windshield → hardtop → hardtop_pillars → railings (UNCHANGED spec 008 order)
2. **rubrail** (needs deck_plate sheer sampling) — port + starboard
3. **bow_pulpit** (needs deck_plate forward geometry + cabin_trunk forward bound)
4. **anchor_locker** (needs deck_plate footprint + cabin_trunk forward bound)
5. **cleats** (needs deck_plate sheer + deck-top resolution)
6. **lifelines** (needs the railings' post stations — built LAST so railing exists)

All six new items append to the same `added` rollback list, so a failure anywhere rolls back the entire deck (FR-013).

## Complexity Tracking

No constitution violations — table intentionally empty.
