# Implementation Plan: Window & Porthole Cutouts

**Branch**: `master` (solo, direct-push) | **Date**: 2026-05-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/011-window-cutouts/spec.md`

## Summary

Add glazing geometry across two modules. In `hull.py`: cut a row of circular **porthole recesses** (blind `PartDesign::Pocket` features appended to the `HullBody` after the mirror, so they become the body Tip) into the topsides, port + starboard, above the waterline; `build_hull` grows an optional `parameters_glazing: HullGlazingParameters` kwarg, portholes on by default. In `deck.py`: cut rounded-rectangle **side-window recesses** (blind Pockets) into the cabin-trunk side walls, and rework the **windshield** into a frame (slab with a through-opening pocketed out) plus a separate thin **glass-pane** body; `build_deck` grows an optional `parameters_glazing: DeckGlazingParameters` kwarg. All cuts are blind recesses into solids (manifold by construction) except the windshield through-opening (thin slab, clean cut). Transparency/color is explicitly out of scope (spec 015). PATCH bump 1.0.4 → 1.0.5; additive API only.

## Technical Context

**Language/Version**: Python 3.11+ (FreeCAD 1.1 bundled Python)

**Primary Dependencies**: FreeCAD 1.1+ Python API (`Part`, `Sketcher`, `PartDesign`, `FreeCAD`); no new third-party deps

**Storage**: N/A (in-memory FreeCAD objects)

**Testing**: pytest — `tests/unit/` (no FreeCAD) + `tests/geometry/` (marker `requires_freecad`)

**Target Platform**: macOS + Ubuntu × Python 3.11/3.12, FreeCAD 1.1.1

**Project Type**: Single-project Python library

**Performance Goals**: human-scale seconds for a full build

**Constraints**: byte-identical reproducibility (II); ±1% fidelity (IV); FreeCAD-idiomatic PartDesign, no raw mesh (III); **post-cut manifold preservation** (FR-008, the spec 009 regression guard); `hull.py` and `deck.py` keep their existing import sets

**Scale/Scope**: 2 modules touched (`hull.py` +~250 lines, `deck.py` +~300 lines), `__init__.py` exports, version bump; ~6 new dataclasses + 2 composites + porthole/window/windshield builders; ~30 new tests

## Constitution Check

| Principle | Status |
|---|---|
| I. Parametric Everything | PASS — all glazing dims are named dataclass fields with defaults |
| II. Reproducibility | PASS — cuts are pure functions of (body, params); SC-005 + `DeterministicShapeDigest` |
| III. FreeCAD-Idiomatic | PASS — `PartDesign::Pocket` for every cut; glass pane is a PartDesign body; no raw mesh |
| IV. Reference Fidelity | PASS — defaults within ±1% (FR-014); per-instance detail exempt |
| V. Test-Gated | PASS (planned) — pytest + ruff + mypy; visual signoff |
| VI. Public OSS / SemVer | PASS — additive only, PATCH bump (FR-016) |
| VII. FreeCAD Version Discipline | PASS — no version-range change |

No violations. **Heightened-risk note** (not a violation): boolean cuts are FreeCAD-runtime-fragile; the design mitigates by using blind recesses into solids (manifold by construction) and a recess-too-deep guard, plus a post-cut solid-count/watertight assertion (FR-008). On a host without FreeCAD the geometry tier cannot execute (see plan §Verification risk).

## Project Structure

```text
specs/011-window-cutouts/
├── plan.md  spec.md  spec.allium  research.md  data-model.md  quickstart.md
├── contracts/python-api.md
├── checklists/requirements.md
└── tasks.md

src/storebro/
├── hull.py     # MODIFIED — PortholeParameters, HullGlazingParameters, Porthole
│               #   wrapper, _validate_hull_glazing, _cut_portholes, build_hull
│               #   parameters_glazing kwarg, Hull aggregate +portholes field
├── deck.py     # MODIFIED — CabinWindowParameters, WindshieldGlazingParameters,
│               #   DeckGlazingParameters; cabin-window pocket; windshield frame
│               #   + glass-pane rework; build_deck parameters_glazing kwarg;
│               #   Deck.windshield exposes frame+glass; +cabin_windows field
├── __init__.py # MODIFIED — export new dataclasses; bump __version__ to 1.0.5
└── (export/interior/cli — UNCHANGED)

pyproject.toml  # MODIFIED — 1.0.4 → 1.0.5

tests/
├── unit/   # NEW per-dataclass validation tests + version test
└── geometry/  # NEW requires_freecad: porthole manifold, window recess,
             #   windshield frame+pane, determinism, rollback, zero-count,
             #   STL-still-watertight, visual signoff; MODIFIED windshield tests
```

**Structure Decision**: Portholes are a hull concern (they cut the hull body), so they live in `hull.py`; cabin windows + windshield are deck concerns in `deck.py`. Each module keeps its own parameter-error type (`HullParameterError` / `DeckParameterError`) and rollback discipline. No new cross-module imports.

## Cut design (the risky part — documented explicitly)

- **Porthole** (hull, solid): circular `Sketcher` profile on an XZ-parallel datum (normal = global Y) positioned at the topside outer-Y for that station; `PartDesign::Pocket` with `Length = recess_depth`, cutting inboard. Appended after the Mirror feature → new body Tip. Manifold guard: `recess_depth < local half-beam` (cannot reach the far side). Above-waterline guard on `center_z`.
- **Cabin window** (deck, solid trunk): rounded-rect `Sketcher` profile on a datum at the trunk side outer-Y; blind `PartDesign::Pocket` `Length = recess_depth`. Guard: `recess_depth < trunk half-width`, opening fits the wall.
- **Windshield** (deck, thin slab): pocket a smaller rectangle THROUGH the slab (`Pocket Type=ThroughAll`) leaving `frame_border` on all sides → frame body; build a separate thin `PartDesign::Body` glass pane (Pad of the opening rectangle, `thickness = glass_thickness`) seated mid-slab. Guard: `2*frame_border < slab width/height` (positive opening).
- **Manifold assertion**: after cuts, `body.Shape.Solids` count == 1 and `body.Shape.isValid()`; raise the module's `*ConstructionError` otherwise (FR-008).

## Verification risk (carried from spec 010)

FreeCAD is not installed on the implementation host, so the `requires_freecad` geometry tier and GUI signoff are WRITTEN but PENDING execution. Boolean Pockets are more runtime-fragile than spec 010's additive bodies; the blind-recess-into-solid design minimizes that, but the geometry tier MUST run on a FreeCAD 1.1+ host before tagging v1.0.5. Unit + ruff + mypy gate locally.

## Complexity Tracking

No constitution violations — table intentionally empty.
