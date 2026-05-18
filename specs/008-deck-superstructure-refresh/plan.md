# Implementation Plan: Deck Superstructure Refresh

**Branch**: `008-deck-superstructure-refresh` | **Date**: 2026-05-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-deck-superstructure-refresh/spec.md`

## Summary

Replace the v1.0.1 boxy placeholder superstructure with a parametric, FreeCAD-idiomatic PartDesign reshape matching the Storebro RC34 1972 reference (`docs/references/Alternativ3.JPG`). Fixes the v1.0.1 hardtop-pillar regression where pillars sit at the analytical sheer Z while the actual hull sheer drifted (after spec 007's stem rake + parameter refresh) — visible as pillars piercing the hull into the cabin.

**Two intertwined deliverables:**

1. **Reshape** — five superstructure components get a new parametric geometry that matches the reference silhouette within ±1% (constitution principle IV):
   - Cabin trunk: trapezoidal+tapered prism (forward-narrower, aft-wider, tapered into the cockpit) replacing the current rectangular `Part.makePlane` extrusion.
   - Windshield: PartDesign `AdditiveLoft` between port-edge and starboard-edge B-spline curves replacing the flat 4-vertex face.
   - Hardtop: PartDesign `AdditivePipe`/`AdditiveLoft` with aft taper and a downward-curling leading edge replacing the flat `Part.makePlane` slab.
   - Pillars: PartDesign `Pad` from a circular sketch on a deck-plate-anchored datum, count default 2 per side (4 total), inboard offset 80 mm from sheer.
   - Railings: PartDesign `AdditivePipe` (true sweep) with a parameterized post count and a top-rail diameter.

2. **Re-architect** — all six sub-builders move from `Part::Feature` + raw `Part.makeXxx` calls to `PartDesign::Body` + sketches + features (constitution principle III, matching spec 006's pattern). The deck plate top Z is sourced from the *actual* deck-plate body's bounding box / sheer wire — not re-derived from `hp.sheer_height_aft/fwd` analytically — so the pillar seating tracks the hull's truth, not its prediction.

**New parameter dataclasses** (six total, one composite):

| Dataclass | Fields (count) | Purpose |
|---|---|---|
| `CabinTrunkParameters` | 7 | length, forward_width, aft_width, height, forward_rake_angle, aft_rake_angle, wall_inset |
| `WindshieldParameters` | 7 | base_z, top_z, rake_angle_base, rake_angle_top, base_width, top_width, thickness |
| `HardtopParameters` | 7 | length, forward_width, aft_width, thickness, height_above_deck, leading_edge_curl_depth, leading_edge_curl_length |
| `PillarParameters` | 5 | count_per_side, diameter, forward_x, aft_x, inboard_offset_from_sheer |
| `RailingParameters` | 7 | post_count_per_side, post_diameter, top_rail_diameter, height_above_deck, forward_x, aft_x, inboard_offset_from_sheer |
| `DeckSuperstructureParameters` | 5 | composite (one of each above) |

The legacy flat `DeckParameters` dataclass (14 fields, all on one struct) is **kept for back-compat** but is now a *delegating shim* that maps its 14 fields onto the six new dataclasses via a `to_superstructure_parameters()` helper. `build_deck()`'s public signature stays compatible per FR-024: callers passing `DeckParameters` or nothing continue to work; new callers may pass `DeckSuperstructureParameters` directly via a new `parameters_superstructure` kwarg.

**Scope:**

- 1 source file modified (`src/storebro/deck.py`, currently 869 LOC).
- 6 private builder functions rewritten (deck plate, cabin trunk, windshield, hardtop, pillars, railings).
- 1 new private helper (`_resolve_deck_top_z_at(deck_plate, x)`) that reads the actual deck-plate top Z from the recomputed body, replacing the analytical `hp.sheer_height_aft + t * (...)` formula at lines 462–463 and 531/586/627/680/732.
- 5 new public parameter dataclasses + 1 composite + 1 delegating shim on the existing `DeckParameters`.
- All existing public-API names (`build_deck`, `DeckParameters`, `Deck`, `DeckParameterError`, `DeckConstructionError`) and signatures preserved. Back-compat fields on the legacy dataclass remain working.
- ~400 LOC net new (~250 reshape + ~150 dataclasses + ~50 deletions for old box geometry).
- ~25 new tests (unit: 6 dataclass validation suites + 1 delegating shim; geometry: 6 silhouette + 1 pillar-seating invariant + 1 byte-identical reproducibility + 1 layout-invariance + cross-product fixtures).

**Semver bump**: PATCH (v1.0.1 → v1.0.2). Additive new dataclasses + kwarg + the same return type. No breaking changes.

## Technical Context

**Language/Version**: Python 3.11+ (matches FreeCAD 1.1's bundled Python).

**Primary Dependencies**: FreeCAD 1.1+ Python API — `FreeCAD`, `Part`, `Sketcher`, `PartDesign`. Standard library: `math`, `dataclasses`, `typing`, `contextlib`. No new third-party dependencies.

**Storage**: N/A — pure in-memory FreeCAD document construction.

**Testing**: pytest with existing markers (`unit`, `requires_freecad`). All 344 currently-passing tests must continue to pass (with hash baselines refreshed for the deck-touched files, same pattern as specs 006 and 007 used `refresh_hashes.py`).

**Target Platform**: Cross-platform; tested on macOS Darwin arm64 with FreeCAD 1.1.1 (the established signoff platform from v1.0.0 + v1.0.1).

**Project Type**: Python library + console script. No new files in `src/` — the entire reshape lives in `src/storebro/deck.py`.

**Performance Goals**: `build_deck()` < 15s on the canonical hull (current v1.0.1 builds in ~3s; PartDesign sketches + loft features add overhead but stay well under the 30s hull budget).

**Constraints**:

- PATCH-level semver: `build_deck()` signature stable, `DeckParameters` shape stable (14 fields + new `__post_init__` shim), `Deck` return type stable.
- New parameter dataclasses are *additive* — they expand the public surface without removing anything.
- Hash baselines refresh required for every `Deck_*` body's expected_hashes.toml entry (same as spec 007 hull refresh).
- Visual signoff regenerated against `Alternativ3.JPG`.
- Constitution III: zero `Part.makeCylinder` / `Part.makeCompound` / `Part.makePlane` calls in the final code path for any superstructure body. Only `PartDesign::Body` + sketches + features.

**Scale/Scope**: 1 file modified (`src/storebro/deck.py`), ~400 LOC net new, 6 private builder functions rewritten, 5 new public dataclasses + 1 composite + 1 shim, ~25 new tests, hash baselines refresh.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|---|---|---|
| **I. Parametric Everything** | PASS | Every dimension becomes a named field on one of 5 sub-dataclasses. Sole "magic numbers" allowed: the per-body internal constants documented in FR (e.g., `slab_thickness = 0.05` survives as a default field, not a hidden constant). All `_MM_PER_M` and explicit ratios stay parametric. |
| **II. Reproducibility (NON-NEGOTIABLE)** | PASS | Same FCStd-document determinism preserved via spec 002's structural-determinism scrub. Two consecutive `build_deck()` calls with identical inputs produce identical SHA-256 digests (SC-005). Hash baselines refresh follows spec 006/007 pattern. |
| **III. FreeCAD-Idiomatic** | PASS — STRENGTHENED | This is one of the main deliverables. The v1.0.1 deck.py uses `Part::Feature` + `Part.makeCylinder`/`makeCompound`/`makePlane`/`Sweep` everywhere — a partial violation of principle III. Spec 008 migrates ALL six builders to `PartDesign::Body` + `Sketcher::Sketch` + `PartDesign::Pad`/`AdditiveLoft`/`AdditivePipe`/`Mirrored`, matching the spec 006 hull pattern. After this spec, the project has zero raw `Part.make*` solids outside the mesh-export adapter (constitution III's named exception). |
| **IV. Reference Fidelity** | PASS — STRENGTHENED | The other main deliverable. Defaults derived from `Alternativ3.JPG` at LOA=10360 mm. Principal-dimension fidelity bar ≤ ±1% (SC-001, SC-007). Constitution IV applies to the WHOLE boat now (hull from spec 007 + superstructure from spec 008). |
| **V. Test-Gated Releases** | PASS | ~25 new tests cover all 32 FR + 8 edge cases. Geometry tests include the pillar-seating invariant (SC-002), reference fidelity (SC-001), byte-identical reproducibility (SC-005), layout invariance (SC-006). All 344 currently-passing tests stay green with hash refresh. Visual signoff line in PR description per the standing requirement. |
| **VI. Public OSS by Default** | PASS | PATCH-level bump (v1.0.1 → v1.0.2). All v1.0.0 public names preserved; 5 new additive dataclasses + 1 new kwarg + 1 composite type. Legacy `DeckParameters` continues to work via delegating shim. No removed or renamed surface. |
| **VII. FreeCAD Version Discipline** | PASS | Supported range `>=1.1, <2.0` unchanged. `PartDesign::AdditiveLoft`, `PartDesign::AdditivePipe`, `PartDesign::Pad`, `PartDesign::Mirrored`, `Sketcher::Sketch` with `Part.BSplineCurve` interpolation all available in 1.1+. The B-spline interpolation API for the windshield edge curves is the same one spec 006/007 used. |

**Gates pass — no Complexity Tracking entries required.**

## Project Structure

### Documentation (this feature)

```text
specs/008-deck-superstructure-refresh/
├── plan.md
├── spec.md
├── spec.allium
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── python-api-additive.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code

```text
src/storebro/
├── __init__.py             # MAY add 5 new dataclass re-exports + DeckSuperstructureParameters
├── __main__.py             # unchanged
├── _freecad_check.py       # unchanged
├── hull.py                 # unchanged (v1.0.1 hull stays as is)
├── export.py               # unchanged
├── deck.py                 # MODIFIED — 6 builders rewritten to PartDesign Bodies + 5 new dataclasses + 1 composite + 1 shim
├── interior.py             # unchanged
├── cli.py                  # unchanged (storebro build still composes hull + deck + interior + export)
└── fixtures/               # unchanged

tests/
├── unit/
│   ├── test_deck_parameters.py                 # MODIFIED — keep existing tests, add new file?
│   ├── test_cabin_trunk_parameters.py          # NEW — per-field + cross-field validation
│   ├── test_windshield_parameters.py           # NEW
│   ├── test_hardtop_parameters.py              # NEW
│   ├── test_pillar_parameters.py               # NEW
│   ├── test_railing_parameters.py              # NEW
│   ├── test_deck_superstructure_parameters.py  # NEW — composite + delegating shim from DeckParameters
│   └── test_deck_back_compat.py                # NEW — asserts legacy DeckParameters still constructs Deck
└── geometry/
    ├── test_deck_*.py                          # all existing pass on the new shape (with hash refresh)
    ├── test_deck_partdesign_feature_types.py   # NEW — asserts every sub-body is PartDesign::Body, no Part::Feature
    ├── test_deck_pillar_seating.py             # NEW — pillars sit on deck plate top within 1 mm for layouts 1..5
    ├── test_deck_silhouette.py                 # NEW — bounding-box principal dimensions match reference ±1%
    ├── test_deck_reproducibility.py            # MODIFIED — extend existing reproducibility test to all 5 layouts
    ├── test_deck_layout_invariance.py          # NEW — layout 1..5 produce identical superstructure shape digests
    └── fixtures/
        └── expected_hashes.toml                # REGENERATED via spec 002's refresh_hashes.py for Deck_* bodies
```

**Structure Decision**: **single src-layout Python module with a deep rewrite of one file plus additive type expansion**. The reshape is confined to `src/storebro/deck.py` — no new modules, no module renames. The new parameter dataclasses live next to the existing `DeckParameters` in the same file (matching the existing pattern where `Deck`, `DeckPlate`, `CabinTrunk`, etc. all live in `deck.py`). Six new unit-test files (one per dataclass + composite + back-compat) mirror the existing per-file test pattern. Five new geometry-test files target the new FRs (PartDesign idiom, pillar seating, silhouette, layout invariance, byte determinism) — existing geometry tests stay valid with hash refresh.

## Complexity Tracking

> No Constitution Check violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| — | — | — |
