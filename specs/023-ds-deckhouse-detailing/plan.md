# Implementation Plan: DS Deckhouse Detailing

**Branch**: `master` (solo, direct-push) | **Date**: 2026-06-03 | **Spec**: [spec.md](./spec.md)

## Summary

Finish the spec 016 DS deckhouse and give the DS variant a real interior. The
deckhouse stays a **filled solid with blind recesses** (the user reviewed and
kept the closed-door reading; through-cuts deferred). Four parts:

1. **Front-window recess** on the raked front face — a `PartDesign::Pocket` on a
   **YZ datum rotated about Y by the front rake angle** (spiked: `Solids==1`,
   valid), plus a thin glass pane on the raked face. Manifold-or-skip gate.
2. **Mullions** — raised vertical `PartDesign::Pad` bosses crossing each side
   window (`mullions_per_window`), fusing into the deckhouse body.
3. **Helm door** — a tall door-shaped blind `PartDesign::Pocket` in a
   parameterized side wall.
4. **Full DS interior** — a bundled `DsSaloon.yaml` layout (enclosed helm saloon
   + galley + head + forward cabin), furnished by the spec 012/013 type-keyed
   builders plus a new `helm` furniture type, behind a `build_interior(...,
   superstructure_variant="ds")` flag using the deckhouse headroom. `"standard"`
   stays byte-identical.

All geometry is additive/blind on the deckhouse and interior bodies — the hull
and deck plate are never booleaned (FR-006); the deckhouse stays `Solids==1`
(FR-005).

## Technical Context

**Language/Version**: Python 3.11 (FreeCAD 1.1.1 bundled interpreter)

**Primary Dependencies**: FreeCAD 1.1.1 (`Part`, `Sketcher`, `PartDesign`);
`deck.py` deckhouse builders (`_build_deckhouse`, `_cut_deckhouse_windows`,
`_build_window_glass`, `_pd_*` helpers); `interior.py` layout loader + spec
012/013 furniture builders; `render.py` roles (reuse glass/superstructure/trim).

**Testing**: pytest (unit + `requires_freecad`); `uv run pytest`, ruff, mypy --strict

**Project Type**: Parametric CAD library

**Constraints**: deckhouse `Solids == 1 && isValid()`; hull + deck plate
unchanged; STL watertight; `"standard"` interior byte-identical.

**Scale/Scope**: `deck.py` (deckhouse builder + params), `interior.py` (variant
flag + `helm` builder + headroom), one new fixture `DsSaloon.yaml`.

## Constitution Check

- **I. Parametric** — PASS. Every new dimension (front window size/depth, mullion
  count/width, helm door size/position/depth, DS layout dims) is a named,
  defaulted, validated field.
- **II. Reproducible** — PASS. Pure geometry from parameters; the manifold-or-skip
  gate for the front recess is **deterministic** (a function of the geometry, not
  random) — no cumulative-state dependence (the rotated-datum cut is a clean
  rectangular pocket, unlike spec 022's arc loft).
- **III. FreeCAD-idiomatic** — PASS. PartDesign Pocket/Pad on the deckhouse body;
  interior furniture via the existing Part-workbench builders (spec 012 idiom).
- **IV. Reference-faithful** — PASS. Framed-window/door reading vs
  `docs/references/storo34_side_lines.png` within ±1% on principal dims.
- **V. Test-gated** — PASS. Unit (params/validation/variant) + geometry
  (manifold, skip-gate, NOBOOL, DS furnishing).
- **VI/VII** — PASS. Additive MINOR; `__version__` 1.8.0 → 1.9.0.

**No violations.**

## Phase 0: Research

See [research.md](./research.md). The one novel construction — the raked
front-face recess on a rotated datum — was spiked (`/tmp/spike_023.py`):
`Solids==1`, valid, first try. Mullion Pad bosses, the helm-door Pocket, and the
DS furnishing reuse proven patterns (specs 016/012/013).

## Phase 1: Design & Contracts

- **data-model.md** — `DsWindowParameters`/`DeckhouseParameters` new fields; the
  `helm` furniture type + interior `superstructure_variant`; `DsSaloon.yaml`
  compartments.
- **contracts/** — additive library surface (new fields + `build_interior`
  variant flag); no removals.
- **quickstart.md** — `storebro build --superstructure ds` + how to build the DS
  interior.

## Implementation sequence

1. `deck.py` params — `DsWindowParameters` (front_window, mullions_per_window,
   mullion_width, helm_door + door dims/side/depth) + validation.
2. `deck.py` `_cut_deckhouse_windows` (or a new helper) — add the rotated
   front-face recess + glass (skip-gate), the mullion bosses, the helm-door
   pocket. Keep `Solids==1` assertions.
3. `interior.py` — `superstructure_variant` param; DS branch loads `DsSaloon`,
   uses deckhouse headroom, furnishes (incl. `helm`); `helm` furniture builder.
4. `fixtures/DsSaloon.yaml` — the DS enclosed-saloon layout.
5. Tests — unit (params, variant, helm) + geometry (front recess/skip, mullions,
   helm door, NOBOOL, DS furnishing, STL).
6. Version 1.8.0 → 1.9.0.

## Complexity Tracking

No constitution violations; table omitted.
