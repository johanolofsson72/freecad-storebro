# Implementation Plan: Windshield Crown (transverse arched top edge)

**Branch**: `master` (solo / direct-push) | **Date**: 2026-06-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/030-windshield-crown/spec.md`

## Summary

Add a parametric `crown_height` field to `WindshieldParameters` that arches the windshield's
transverse top edge upward at the centerline (Y=0), falling to the port/starboard corners. The
arch is realised by replacing the dead-flat top edge of each loft section sketch (base/mid/top in
`_build_windshield`, `src/storebro/deck.py`) with a deterministic **polyline approximation** of an
upward arc, applied uniformly across all three sections so the `Ruled=False` `AdditiveLoft` skins a
smooth fore-aft crowned cap. The bottom edge stays flat. `crown_height = 0.0` skips the new code
path entirely, reproducing the pre-030 flat-top windshield byte-identically. The spec 011 frame
opening + glass pane are untouched; the crown only adds material above the corners (which retain
the flat-top Z), so the `frame_border` margin is preserved by construction. A manifold-or-fallback
gate degrades to the flat-top slab if the crowned loft fails in FreeCAD.

## Technical Context

**Language/Version**: Python 3.11+ (matches FreeCAD 1.1 bundled Python)

**Primary Dependencies**: FreeCAD 1.1+ (`Part`, `Sketcher`, `PartDesign`) — geometry runtime

**Storage**: N/A (geometry produced into a FreeCAD document; exports via existing writers)

**Testing**: pytest; unit tests (no FreeCAD) for parameter validation; `requires_freecad` tests
for geometry assertions (FreeCAD absent on dev machine → maintainer runs them, per spec 029 pattern)

**Target Platform**: Cross-platform library (Ubuntu + macOS × Python 3.11/3.12 in CI)

**Project Type**: Library (`storebro`)

**Performance Goals**: Human-scale geometry build time; no regression vs current windshield build

**Constraints**: Byte-reproducible (constitution II) — no timestamps/env-dependent values;
FreeCAD-idiomatic PartDesign/Sketcher only (constitution III); parametric, no magic numbers
(constitution I)

**Scale/Scope**: One file (`src/storebro/deck.py`), one additive dataclass field, one helper for
the arched-top sketch; ~1 new validation block; new unit + `requires_freecad` tests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Parametric**: PASS — `crown_height` is a named parameter with a default (60.0 mm); the
  arch segment count is a named constant (no inline magic numbers in the body).
- **II. Reproducible**: PASS — the arch is a deterministic polyline (no Sketcher arc solver), no
  timestamps/random; same inputs → byte-identical output; `0.0` reproduces pre-030 exactly.
- **III. FreeCAD-idiomatic**: PASS — reuses the existing `PartDesign::Body` + `AdditiveLoft` +
  `Sketcher` flow; no raw mesh generation; the only change is the section sketch outline shape.
- **IV. Reference-faithful**: PASS — the crown matches the RC34 reference silhouette (gentle
  upward bow at centerline).
- **V. Test-gated**: PASS — unit tests for validation + `requires_freecad` geometry tests; GUI
  eyeball remains the maintainer's pre-tag step.
- **VI. Public OSS / VII. Version-disciplined**: PASS — additive MINOR change (new optional field
  with a back-compat OFF sentinel); no breaking signature change.

**No gate violations. No complexity deviations to justify.**

## Project Structure

### Documentation (this feature)

```text
specs/030-windshield-crown/
├── spec.md              # /speckit-specify + /clarify output
├── spec.allium          # /allium:elicit output (validated, 0 errors)
├── plan.md              # This file
├── research.md          # Phase 0 — the crowned-section + frame-cut spike
├── data-model.md        # Phase 1 — the WindshieldParameters field + validation
├── quickstart.md        # Phase 1 — how to build/verify a crowned windshield
├── contracts/
│   └── windshield_parameters.md   # public-API delta (the additive field)
└── tasks.md             # /speckit-tasks output
```

### Source Code (repository root)

```text
src/storebro/deck.py                          # WindshieldParameters + _build_windshield (only src file touched)
tests/unit/test_windshield_crown.py           # NEW — parameter validation (no FreeCAD)
tests/<geometry>/test_windshield_crown_geom.py # NEW — requires_freecad geometry assertions
```

(Exact test directory + reproducibility-test home confirmed in Phase 1 against the actual tests/
layout — the existing windshield/deck geometry tests dictate the location.)

## Phase 0: Research — the crowned-section + frame-cut spike

See [research.md](./research.md). Resolves: (a) polyline arc vs Sketcher arc (decided: polyline,
deterministic); (b) apply-to-all-three-sections vs top-only (decided: all three, matching vertex
topology for a robust `Ruled=False` loft); (c) frame-opening interaction (decided: opening stays
rectangular; crown only adds material above corners → margin preserved by construction); (d)
manifold-or-fallback strategy (decided: build crowned loft, validate `Solids==1` + `isValid`, else
rebuild the existing flat-top slab); (e) validity bound (`0 ≤ crown_height < top_width/2`).

## Phase 1: Design & Contracts

- [data-model.md](./data-model.md) — the single additive field, its default, its validation rules.
- [contracts/windshield_parameters.md](./contracts/windshield_parameters.md) — public-API delta.
- [quickstart.md](./quickstart.md) — build + verify steps.

Post-design constitution re-check: **PASS** (no new violations introduced by the design).
