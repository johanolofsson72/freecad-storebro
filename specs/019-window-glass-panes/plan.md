# Implementation Plan: Window Glass Panes

**Branch**: master | **Date**: 2026-06-02 | **Spec**: [spec.md](./spec.md)

## Summary

Add translucent glass-pane bodies in the existing blind recesses: portholes
(`hull.py`), cabin-trunk side windows + DS deckhouse side windows (`deck.py`).
Each pane is a thin **additive** PartDesign/Part body (circular disc for
portholes, rectangular slab for windows) seated at the recess, never a boolean
on the host solid — so the host hull/trunk/deckhouse stay single manifold solids
by construction. Panes resolve to the spec 015 `glass` palette role (reuse the
windshield-glass pattern). On by default, per-call opt-out. Rounded corners
deferred (fillet non-watertight risk, spec 018).

## Technical Context

- Files: `hull.py` (porthole glass + `HullGlazingParameters.glass_panes` flag +
  `PortholeGlass` wrapper), `deck.py` (cabin-window + deckhouse-window glass +
  flags + wrappers), `render.py` (role rules for the new glass body names),
  `__init__.py` (re-exports), tests.
- Placement reuses the existing recess math: portholes — XZ datum at the outer
  hull surface, disc of porthole radius inset by recess_depth; windows — the
  same per-station X/Z/outer-Y the recess pockets already compute, a slab inset
  into the recess.
- Manifold/reproducibility/rollback: inherited — panes are additive bodies added
  to the host's `added` rollback list; the host solids are never touched.

## Constitution Check

I parametric (pane thickness/inset are named params) · II reproducible (additive,
deterministic) · III idiomatic (PartDesign bodies, mirrors windshield glass) ·
IV fidelity (panes sit in the reference recesses) · V test-gated (geometry tests:
pane count, single-solid, host-unchanged, glass role) · VI semver MINOR (additive)
· VII no new FreeCAD API. **PASS.**

## Build sequence

1. `hull.py`: `_build_porthole_glass(...)` builds one disc per porthole recess;
   `HullGlazingParameters` gains `glass_panes: bool = True` + `glass_thickness`;
   `Porthole`/glazing result exposes the panes; names `Hull_PortholeGlass*`.
2. `deck.py`: `_build_cabin_window_glass(...)` + `_build_deckhouse_window_glass(...)`
   build one slab per recess; glazing params gain `glass_panes`/`glass_thickness`;
   wrappers expose panes; names `Deck_CabinWindowGlass*` / `Deck_DeckhouseWindowGlass*`.
3. `render.py`: add role rules `Hull_PortholeGlass`/`Deck_CabinWindowGlass`/
   `Deck_DeckhouseWindowGlass` → `glass`; include panes in render targets.
4. Tests + version bump 1.4.0 → 1.5.0.
5. Verify on FreeCAD 1.1.1.

## Complexity Tracking
No violations.
