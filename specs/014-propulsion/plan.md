# Implementation Plan: Propulsion — Engine Bay, Engine, Shaft, Propeller & Rudder

**Branch**: `master` (solo, direct-push) | **Date**: 2026-06-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/014-propulsion/spec.md`

## Summary

Add a new `src/storebro/propulsion.py` module that builds a parametric inboard propulsion installation — engine bed (stringers), engine block, propeller shaft, propeller, and rudder — and composes them via `build_propulsion(hull, deck=None, ...)` into a `Propulsion` aggregate. Each component is a FreeCAD `PartDesign::Body` built from datum + sketch + Pad/Revolution/Loft features, parameterized by a frozen mm-unit dataclass with `__post_init__` validation raising `PropulsionParameterError`, seated on the ACTUAL sampled hull geometry (hull-bottom keel depth and half-beam at the relevant X stations, read from `hull.body.Shape`). Single-screw (`engine_count=1`) and twin-screw (`engine_count=2`, default) configurations are supported; the twin layout mirrors port/starboard trains about Y=0 with a parametric outboard offset, and `rudder_count` defaults to `engine_count`. The hull solid is NEVER booleaned — the shaft penetration is modeled as an additive stern-tube boss (preserves manifold integrity per the specs 009/011 lessons). The module mirrors the spec 008/010 PartDesign idiom exactly (datum planes + sketches + features, rollback discipline, manifold guard). Integrated into `cli.py`'s build composition (built by default, with `--engine-count` / `--no-propulsion` flags) so the bodies flow into all export formats automatically. MINOR bump 1.0.7 → 1.1.0 (first new public geometry module beyond the v1.0 set); additive public API only; `storebro.__version__` kept in sync with `pyproject.toml`.

## Technical Context

**Language/Version**: Python 3.11+ (matches FreeCAD 1.1 bundled Python)

**Primary Dependencies**: FreeCAD 1.1+ Python API (`Part`, `Sketch`, `PartDesign`, `FreeCAD`); no new third-party deps

**Storage**: N/A (geometry returned as in-memory FreeCAD objects; persistence is the export module's job)

**Testing**: pytest — `tests/unit/` (no FreeCAD) + `tests/geometry/` (marker `requires_freecad`)

**Target Platform**: macOS + Ubuntu × Python 3.11/3.12 (CI matrix), FreeCAD 1.1.1

**Project Type**: Single-project Python library (`src/storebro/`)

**Performance Goals**: human-scale seconds for a full `build_propulsion`; no hard latency budget (constitution priority 5)

**Constraints**: byte-identical reproducibility (constitution II); ±1% reference fidelity on principal dimensions where a reference exists, representative fidelity for machinery (constitution IV + FR-015); FreeCAD-idiomatic B-rep only, no raw mesh (constitution III); hull solid never modified (FR-007); `propulsion.py` may import only `storebro.hull`, `storebro.deck`, and `storebro._freecad_check`

**Scale/Scope**: one new module (`propulsion.py`, ~700–900 lines), one `__init__.py` edit (exports + version), one `cli.py` edit (compose + 2 flags), one `pyproject.toml` version bump; 5 per-component parameter dataclasses + 1 composite + 5 builder functions + 5 wrapper dataclasses + `Propulsion` aggregate + 2 sampling helpers; ~35 new tests

## Constitution Check

*GATE: must pass before Phase 0 and re-checked after Phase 1.*

| Principle | Gate | Status |
|---|---|---|
| I. Parametric Everything | Every propulsion dimension is a named dataclass field with a default; no magic numbers in builder bodies | PASS — all dims flow from the 5 parameter dataclasses + module `config` defaults |
| II. Reproducibility (NON-NEGOTIABLE) | No timestamps/random/env in propulsion geometry; identical inputs → identical bytes | PASS — builders are pure functions of (hull, deck, params); SC-005 + `DeterministicShapeDigest` invariant assert it |
| III. FreeCAD-Idiomatic | PartDesign bodies + sketches + Pad/Revolution/Loft; no raw mesh outside export adapters | PASS — FR-009; matches spec 008/010 idiom exactly |
| IV. Reference Fidelity | Defaults plausible for an RC34 inboard installation; representative machinery fidelity declared | PASS — FR-015 + `ReferenceFidelityWithinOnePercent` invariant; CAD-faithful machinery exempt (deferred) |
| V. Test-Gated Releases | pytest + ruff + mypy --strict green; manual FreeCAD visual signoff | PASS (planned) — SC-008 + visual signoff test mirroring `test_deck_hardware_visual_signoff.py` |
| VI. Public OSS by Default | Additive API only; MINOR bump (new module = material expansion); no breaking change | PASS — FR-013/FR-014; new module + new CLI flags, nothing removed |
| VII. FreeCAD Version Discipline | No FreeCAD version range change | PASS — no API-break shim needed; range unchanged in pyproject |

No violations. Complexity Tracking table omitted (nothing to justify).

## Project Structure

### Documentation (this feature)

```text
specs/014-propulsion/
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
├── propulsion.py    # NEW — 5 component parameter dataclasses + PropulsionParameters
│                    #   composite, PropulsionParameterError / PropulsionConstructionError,
│                    #   5 wrapper dataclasses (EngineBed, EngineBlock, Shaft, Propeller,
│                    #   Rudder), Propulsion aggregate, 5 _build_* functions, 2 hull-sampling
│                    #   helpers (_hull_bottom_z_at, _hull_half_beam_at), build_propulsion()
├── __init__.py      # MODIFIED — export new public names; bump __version__ to 1.1.0
├── cli.py           # MODIFIED — compose build_propulsion in _run_build; add
│                    #   --engine-count {1,2} and --no-propulsion flags
└── (hull.py, export.py, interior.py, deck.py — UNCHANGED)

pyproject.toml       # MODIFIED — version 1.0.7 → 1.1.0

tests/
├── unit/            # NEW — per-dataclass validation tests (no FreeCAD):
│                    #   test_engine_bed_parameters.py, test_engine_parameters.py,
│                    #   test_shaft_parameters.py, test_propeller_parameters.py,
│                    #   test_rudder_parameters.py, test_propulsion_parameters.py
│                    #   (engine_count/rudder_count/offset cross-invariants),
│                    #   test_propulsion_back_compat.py, test_propulsion_public_docstrings.py
│                    # MODIFIED — test_version_consistency.py (1.1.0),
│                    #   test_cli_build.py (propulsion flags + composition)
└── geometry/        # NEW — FreeCAD integration (marker requires_freecad):
                     #   test_propulsion_default_call.py (twin), test_propulsion_single_screw.py,
                     #   test_propulsion_twin_symmetric.py, test_propulsion_shaft_geometry.py
                     #   (down-and-aft + exit below waterline), test_propulsion_running_gear_order.py
                     #   (prop aft of exit, rudder aft of prop, both below waterline),
                     #   test_propulsion_engine_envelope.py (no hull pierce),
                     #   test_propulsion_manifold.py (solid==1 each), test_propulsion_determinism.py,
                     #   test_propulsion_rollback.py, test_propulsion_hull_unmodified.py,
                     #   test_propulsion_destructive_validation.py,
                     #   test_propulsion_visual_signoff.py
```

**Structure Decision**: New module `propulsion.py`, consistent with the constitution "Module Layout (flat-module-per-body-part)". Propulsion is a distinct body group — engine, shaft, running gear — conceptually separate from hull, deck, and interior, with its own parameter namespace and its own seating logic (hull-bottom + keel-depth sampling rather than deck-top sampling). It imports `storebro.hull` (for the `Hull` aggregate + `hull.body.Shape` sampling), optionally `storebro.deck` (for the `Deck` aggregate to derive the engine-height ceiling), and `storebro._freecad_check`. Top-level composition (hull → deck → interior → propulsion → export) stays in `cli.py`, never inside a body-part module (constitution rule).

## Build Sequence (dependency order within build_propulsion)

`build_propulsion(hull, deck=None, parameters=None)` resolves the train set (1 train for single-screw, 2 mirrored trains for twin) and, per train, builds in this order, each component appended to a shared `added` rollback list:

1. **engine bed** — sampled hull-bottom (keel) Z at the engine station; bed seated above keel, offset outboard by `engine_offset_y_mm` for the train side.
2. **engine block** — rests on the bed; height-clamped below the deck-top ceiling (or hull sheer fallback when `deck is None`); validated to stay inboard of the sampled half-beam (no hull pierce).
3. **shaft** — from the engine coupling, angled down-and-aft at `shaft.angle_deg`, to `shaft.exit_x_mm`; the exit point Z comes from the sampled hull bottom; an additive stern-tube boss wraps the penetration (hull never cut).
4. **propeller** — hub + `blade_count` blades, placed aft of the shaft exit on the shaft axis, below the waterline.
5. **rudder(s)** — `rudder_count` foil-plate + stock bodies, aft of the propeller(s), below the waterline (one per screw by default; single centreline rudder when `rudder_count=1` on a twin).

Twin builds run the per-train sequence twice (port at +Y, starboard at −Y mirror). A failure anywhere rolls back every body added so far (FR-010). After all bodies are built, a manifold guard asserts each produced solid has `Solids == 1` and `isValid()` (FR-008).

## Complexity Tracking

No constitution violations — table intentionally empty.
