# Implementation Plan: Interior Layout Expansion

**Branch**: `025-interior-layout-expansion` | **Date**: 2026-06-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/025-interior-layout-expansion/spec.md`

## Summary

Widen the interior model along four independent axes, all in `src/storebro/interior.py` (+ the Alternativ5 fixture): a `salon_galley` compartment type (settee+table + galley counter), furniture dispatched by compartment TYPE for every layout (drop the `_FURNISHED_LAYOUTS` layout-name gate), four more types (`aft_cabin`, `dinette`, `engine_room`, `wet_locker`), and off-centre placement (drop the `position.y == 0` constraint, bound transversely by `beam_max/2`). Furniture stays `Part::Feature` B-rep solids (the spec 012 idiom), each furnished compartment a `Part::Compound`; new geometry is analytic Part primitives (boxes/cuts/fuses) — spec 024 proved this class byte-reproducible, so no spike is needed. Canonical Alternativ1–4 + DS build byte-identically; only Alternativ5 changes (its fixture compartment switches `salon` → `salon_galley`).

## Technical Context

**Language/Version**: Python 3.11+ (FreeCAD 1.1 bundled Python)
**Primary Dependencies**: FreeCAD 1.1+ (`Part`), PyYAML (fixtures), stdlib. No new deps.
**Storage**: bundled YAML fixtures (`src/storebro/fixtures/`).
**Testing**: `pytest` (unit: type set, parameter dataclasses, asymmetric/envelope validators — no FreeCAD; geometry: `requires_freecad`), `ruff`, `mypy --strict`.
**Target Platform**: FreeCAD 1.1+ macOS/Linux.
**Project Type**: Single library (`src/storebro/`).
**Performance Goals**: human-scale (seconds); no lofts, so no per-build cost spike.
**Constraints**: byte-identical output (constitution II); furniture single valid solids; galley manifold guard (`Solids==1`); Part B-rep idiom (constitution III); canonical layouts byte-identical except Alt5.
**Scale/Scope**: one module (`interior.py`, ~1605 LOC) + one fixture (`Alternativ5.yaml`). Net additions: 5 new compartment types, ~2 new furniture builders (engine_room, wet_locker), ~2 new param dataclasses, the gate drop, the symmetry-constraint drop + transverse validator, and the `offset_y` threading into existing builders.

## Constitution Check

| Principle | Status | Compliance |
|---|---|---|
| I. Parametric Everything | ✅ | New fittings' dimensions are named params with defaults (`EngineRoomParameters`, `WetLockerParameters` + reuse). No magic numbers in builders. |
| II. Reproducibility (NON-NEGOTIABLE) | ✅ | All new geometry is analytic Part primitives (the spec 024 class proven byte-reproducible). Canonical layouts byte-identical (offset_y=0 path unchanged); Alt5 changes deterministically. A determinism test guards every new layout. |
| III. FreeCAD-Idiomatic | ✅ | Furniture stays `Part::Feature` B-rep (spec 012 idiom); compartments `Part::Compound`. No raw mesh. |
| IV. Reference Fidelity | ✅ | Alt5 gains its galley (more reference-faithful); the ±1% hull/interior fidelity bar is unaffected. |
| V. Test-Gated | ✅ | New unit (type set, params, validators) + geometry (Alt5 galley, custom furnishing, new types, asymmetric, determinism, canonical-byte-identity) tests. ruff + mypy gate. |
| VI. Public OSS / SemVer | ✅ | Additive public surface (new types accepted in YAML, new param dataclasses with defaults). MINOR bump 1.11.0 → 1.12.0. No breaking change. |
| VII. FreeCAD Version Discipline | ✅ | No new FreeCAD-version-specific API. |

**Result: PASS** (no violations; Complexity Tracking not required).

## Project Structure

```text
specs/025-interior-layout-expansion/
├── plan.md research.md data-model.md quickstart.md contracts/python-api.md
├── spec.md spec.allium tasks.md

src/storebro/
├── interior.py          # THE feature — types, dispatch, new builders, gate drop, transverse validator, offset_y
└── fixtures/Alternativ5.yaml  # the combined compartment: type salon -> salon_galley
                                # __init__.py / pyproject.toml: __version__ 1.11.0 -> 1.12.0

tests/
├── unit/
│   ├── test_interior_compartment_types.py   # NEW — type set + new-type params + furnish-by-type gate (no FreeCAD)
│   └── test_interior_asymmetric_validation.py # NEW — y!=0 accepted; transverse bound rejection
└── geometry/
    ├── test_interior_alt5_galley.py          # NEW — Alt5 salon_galley has settee+table+galley
    ├── test_interior_custom_furnished.py     # NEW — custom layout furnished by type
    ├── test_interior_new_types.py            # NEW — aft_cabin/dinette/engine_room/wet_locker furnished
    ├── test_interior_asymmetric_geometry.py  # NEW — off-centre compartment + furniture
    ├── test_interior_expansion_determinism.py # NEW — v1==v2 for custom/asymmetric/Alt5
    └── test_interior_canonical_byte_identity.py # NEW — Alt1-4 + DS unchanged
```

**Structure Decision**: Single library, one module touched in place — the same shape as spec 012/013/024 (interior detailing). The Alternativ5 fixture is the only data change.

## Build Sequence (one task — no stops between steps)

1. **Compartment-type set** — extend `_COMPARTMENT_TYPES` with `aft_cabin`, `dinette`, `engine_room`, `wet_locker`, `salon_galley`. Define `_FURNISHABLE_TYPES` (all of them) so the dispatch and the furnish-gate share one source of truth.
2. **Drop the symmetry constraint** — remove the `position.y != 0` reject in `_parse_compartment_entry`; add the transverse bound to `_validate_compartment_in_envelope`: `abs(y) + width/2 <= beam_max/2` (metre-space, parametric — matches the existing validator idiom).
3. **Drop the layout-name furnishing gate** — replace `furnished = layout_name in _FURNISHED_LAYOUTS` with per-compartment dispatch: a compartment whose type is furnishable gets furniture in ANY layout. The furniture-fit validation loop runs over every furnishable compartment regardless of layout name.
4. **New furniture params** — `EngineRoomParameters` (block-like solid dims), `WetLockerParameters` (locker + shelf dims); add to `FurnitureParameters` with defaults.
5. **Thread `offset_y`** — every furniture builder centres on `offset_y = spec.position.y * _M_TO_MM` instead of hardcoded `0`. Canonical layouts (`y=0`) → byte-identical; off-centre layouts shift transversely.
6. **New builders + dispatch** — `aft_cabin` → `_build_berth`; `dinette` → `_build_salon_furniture`; `engine_room` → new `_build_engine_room_fitting` (engine-block box); `wet_locker` → new `_build_wet_locker` (locker box + shelves); `salon_galley` → `_build_salon_furniture` + `_build_galley_counter` (both, fused into the compound). Extend the furniture-fit validator (`_validate_furniture_envelope`) to the new types.
7. **Alternativ5 fixture** — change the combined compartment from `type: salon` to `type: salon_galley`.
8. **Version bump** 1.11.0 → 1.12.0 (`__init__.py` + `pyproject.toml`) + version-consistency test.
9. **Tests** (unit + geometry) per the structure above; `pytest`/`ruff`/`mypy --strict`.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| `offset_y` threading breaks canonical byte-identity | Canonical layouts have `y=0` → `offset_y=0` → identical coordinates. A canonical-byte-identity geometry test (Alt1–4 + DS volume + digest) guards it. |
| salon_galley galley counter goes non-manifold | The spec 012 galley manifold guard (`Solids==1`, manifold-or-box fallback) is reused verbatim. |
| New-type fitting taller than its compartment | `_validate_furniture_envelope` extended to the new types — rejects before geometry. |
| Off-centre compartment pierces the hull side | `abs(y)+width/2 <= beam_max/2` transverse validator (FR-007). |
| engine_room interior fitting collides with the propulsion engine | They are separate modules built into separate bodies; the interior engine_room fitting is representative and lives in the interior compound — no boolean interaction. Documented in research.md. |

## Phase 2 note

`/speckit-tasks` expands this into dependency-ordered tasks (type set + validators [unit-testable first], then gate drop + offset_y + builders + fixture, then tests, then version). `/speckit.analyze` runs between tasks and implement.
