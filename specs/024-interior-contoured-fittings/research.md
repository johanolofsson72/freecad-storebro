# Phase 0 Research — Interior Contoured Fittings

The risk is constitution II: spec 022 proved arc lofts are non-reproducible
under cumulative FreeCAD state. So every contour op was spiked for BOTH manifold
validity AND byte-reproducibility before any code.

## Decision 1 — fillets/cuts/fuses on Part::Feature furniture

- **Decision**: Contour with `Part.makeFillet`/`makeSphere`/`makeCylinder`/
  `fuse`/`cut` on the existing Part::Feature furniture bodies.
- **Rationale**: The interior module is Part::Feature B-rep (spec 004/012), so
  Part-workbench ops are idiomatic (constitution III). Spike `/tmp/spike_024.py`:
  a vertical-edge-filleted box is `Solids==1` valid, and its volume is
  **byte-identical across 4 fresh builds** (`104519291.886` ×4) — `makeFillet`
  on a box is reproducible, unlike the spec 022 arc loft.
- **Alternatives**: PartDesign fillets (rejected — the furniture is Part::Feature,
  not PartDesign; mixing is non-idiomatic for this module).

## Decision 2 — fabric detail: cut-sphere buttons + fused piping welt + cut folds

- **Decision**: Tufting buttons = a grid of shallow `makeSphere` cuts on the
  cushion top; piping = a thin rounded frame (`outer.cut(inner)`) fused on the
  top perimeter; fold creases = shallow `makeBox` groove cuts.
- **Rationale**: Spike `/tmp/spike_024fab.py`: a cushion with rounded edges + a
  2×4 button grid + piping welt + 2 fold grooves is `Solids==1`, valid, closed,
  and **byte-reproducible** (`128533629.9` ×4). Analytic primitives → no
  tessellation-state dependence.
- **Alternatives**: raised button discs (rejected — tufting is dimpled, not
  raised); swept piping cord (rejected — a fused frame is simpler + reproducible).

## Decision 3 — contoured toilet + faucet, galley fascia, curved bulkhead

- **Toilet**: `makeBox` pedestal + `makeCylinder` bowl `fuse` + vertical-edge
  fillet → `Solids==1` valid (spike probe 2).
- **Faucet**: stem + spout cylinders (spike probe 3) — a small fitting on the
  sink; two pieces in the head compound (acceptable; each valid).
- **Bulkhead**: `makeBox` wall, `cut` a doorway box `fuse`d with a horizontal
  half-cylinder arch (rounded top) → `Solids==1` valid (spike probe 4); vertical
  edges filleted.
- **Galley fascia**: a thin rounded panel fused on the worktop forward face;
  the spec 012 sink/stove `Solids==1` manifold guard is preserved.

## Manifold-or-fallback gate

Each contoured piece is checked `Solids==1 && isValid()`; on failure the piece
reverts to its spec 012/013 box. The gate is deterministic (geometry-only), so
it never introduces non-reproducibility.

## Summary

All contour + fabric ops are manifold-safe AND byte-reproducible. No NEEDS
CLARIFICATION remain.
