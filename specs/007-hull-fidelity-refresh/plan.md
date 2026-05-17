# Implementation Plan: Hull Fidelity Refresh

**Branch**: `007-hull-fidelity-refresh` | **Date**: 2026-05-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-hull-fidelity-refresh/spec.md`

## Summary

Refresh the v1.0.0 hull so it looks like an actual Storebro RC34 1972 instead of a paper-origami wedge. Five parameter-default changes + 1 new field + 4 structural changes to the construction pipeline:

**Parameter defaults** (`HullParameters` in `src/storebro/hull.py:125-165`):
| Field | v1.0.0 | v1.0.1 | Reason |
|---|---|---|---|
| `draft` | 0.95 | **1.10** | storebropassion.de actual |
| `sheer_height_aft` | 0.85 | **0.95** | matches reference freeboard aft |
| `sheer_height_fwd` | 1.30 | **1.16** | matches reference freeboard fwd; sheer rise drops 450→210mm |
| `deadrise_amidships` | 16.0 | **8.0** | semi-displacement, not planing |
| `transom_angle` | 12.0 | **5.0** | near-vertical transom |
| `stem_rake_angle` (**NEW**) | – | **6.0** | additive field with default; range [0, 30] |

**Structural changes** (`_compute_stations`, `_create_station_sketch`, `_create_datum_plane`, `_apply_loft_and_mirror`):
1. **Stem station becomes blunt**: `_StationProfile(is_terminal=True, ...)` → finite half-beam-at-stem ~40mm (so the half-section is ~80mm wide). The `_create_station_sketch` stem branch produces a closed rectangle instead of a `Part.Point`.
2. **Stem datum tilts forward**: `_create_datum_plane` adds a Y-axis rotation by `stem_rake_angle` degrees ONLY for the stem station. Other datums stay parallel to YZ.
3. **Non-stem sketches use quarter-circle bilge arc**: `_create_station_sketch` for non-stem profiles replaces the keel→bottom-outer line segment with a `Part.ArcOfCircle`. Other 4 line segments unchanged.
4. **AdditiveLoft switches to Ruled=False with auto-fall-back**: `_apply_loft_and_mirror` builds the loft with `Ruled=False`; after recompute, if the loft's shape is invalid (volume ≤ 0 OR not closed OR bbox X-length ≤ 0), delete the loft, recreate with `Ruled=True`, recompute, log a warning via `logging.warning(...)`.

**One new Body property**: `body.addProperty("App::PropertyAngle", "StemRakeAngle", "Hull", ...)` added in `_bind_parameters_to_body_properties`.

Total scope: 1 source file (`src/storebro/hull.py`), 6 private functions touched (4 modified, 2 unchanged), ~80 net new lines. Public API frozen at v1.0.0 except for the additive `stem_rake_angle` field.

## Technical Context

**Language/Version**: Python 3.11+ (matches FreeCAD 1.1's bundled Python).

**Primary Dependencies**: FreeCAD 1.1+ Python API — `FreeCAD`, `Part`, `Sketcher`, `PartDesign`. Standard library: `math`, `time`, `logging`, `dataclasses`. No new third-party dependencies.

**Storage**: N/A.

**Testing**: pytest with existing markers (`unit`, `requires_freecad`). All 96 currently-passing geometry tests must continue passing on the new shape (hash baselines re-seed in polish phase).

**Target Platform**: Cross-platform; tested on macOS Darwin arm64 with FreeCAD 1.1.1.

**Project Type**: Python library + console script. No new files in `src/`.

**Performance Goals**: `build_hull()` < 30s (same as v1.0.0).

**Constraints**:
- PATCH-level semver: `Hull` dataclass / 8 v1.0.0 named properties / exception attribute shapes frozen.
- One additive field on `HullParameters` (with default) is allowed under PATCH per constitution VI.
- Hash baselines re-seed (`tests/geometry/fixtures/expected_hashes.toml`).
- Visual signoff regenerated.

**Scale/Scope**: 1 file modified, 4 functions rewritten, ~80 LOC net new, 3-5 new tests, 1 new Body property. Hash baselines auto-refresh.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|---|---|---|
| **I. Parametric Everything** | PASS | 9 named parameters total. `stem_rake_angle` becomes a 9th named field with default. No magic numbers introduced beyond the documented `bilge_radius = half_beam_at_bottom × 0.5` and `blunt_stem_half_width = 80mm` constants. |
| **II. Reproducibility (NON-NEGOTIABLE)** | PASS | Determinism preserved. Hash baselines re-seed via spec 002's `refresh_hashes.py` (planned in polish phase, same pattern as spec 006). |
| **III. FreeCAD-Idiomatic** | PASS | Switches loft from Ruled=True (piecewise-linear, less idiomatic for hulls) to Ruled=False (B-spline, the FreeCAD-idiomatic smooth surface). Adds quarter-circle bilge arc via `Part.ArcOfCircle` (Sketcher-native primitive). No raw mesh. |
| **IV. Reference Fidelity** | PASS — STRENGTHENED | The whole point of this spec. Principal dimensions match storebropassion.de within ±1% (LOA, beam), silhouette heights within ±5% (freeboards, height-above-WL). |
| **V. Test-Gated Releases** | PASS | All 96 geometry tests preserved. New silhouette-dimension tests added (FR-010). Hash baselines re-seed (constitution VII allows). Manual visual signoff per the standing PR-description requirement. |
| **VI. Public OSS by Default** | PASS | PATCH-level bump (v1.0.0 → v1.0.1). `Hull` dataclass / `HullParameters` field set additive only / exception attributes unchanged. |
| **VII. FreeCAD Version Discipline** | PASS | Supported range `>=1.1, <2.0` unchanged. `PartDesign::AdditiveLoft` with `Ruled=False`, `Part.ArcOfCircle`, and `Placement.Rotation` all available in 1.1+. |

**Gates pass.**

## Project Structure

### Documentation (this feature)

```text
specs/007-hull-fidelity-refresh/
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
├── hull.py                 # MODIFIED — 4 private functions + HullParameters defaults + new stem_rake_angle field
├── export.py               # unchanged
├── deck.py                 # unchanged
├── interior.py             # unchanged
├── cli.py                  # unchanged
└── fixtures/               # unchanged

tests/
├── unit/                   # MAY add test_hull_parameters_stem_rake.py for the new field validation
└── geometry/
    ├── test_hull_*.py            # all existing pass on the new shape (with hash refresh)
    ├── test_hull_partdesign_feature_types.py   # MAY tweak to assert StemRakeAngle property exists
    ├── test_hull_bspline_loft.py # NEW — asserts AdditiveLoft.Ruled == False for canonical defaults
    ├── test_hull_silhouette.py   # NEW — asserts bounding-box dimensions match reference within ±5%
    └── fixtures/
        └── expected_hashes.toml  # REGENERATED via refresh_hashes.py
```

**Structure Decision**: **single src-layout Python module with targeted private-function modifications**. Spec 007's fix scope is constrained to `src/storebro/hull.py` plus a hash-baselines refresh. No public API change beyond the additive `stem_rake_angle` field. Three new test files validate the spec's specific contracts (B-spline loft mode, silhouette dimensions, optional PartDesign-feature-type tweak).

## Complexity Tracking

> No Constitution Check violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| — | — | — |
