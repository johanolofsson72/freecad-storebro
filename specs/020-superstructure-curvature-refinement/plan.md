# Implementation Plan: Superstructure Curvature Refinement

**Branch**: master | **Date**: 2026-06-02 | **Spec**: [spec.md](./spec.md)

## Summary

Three spec-008 geometry-equivalence deferrals, all spike-proven manifold-safe
without Ruled=False:
1. **Hardtop smooth curl** — `_build_hardtop` builds `curl_sections` forward
   station sketches tracing a cosine drop (dense Ruled=True), instead of the
   single-drop 3-section loft. Spike: 0mm Z-overshoot at n=3/7/13.
2. **Swept perimeter top-rail** — `_build_railings` sweeps a circular profile
   along the closed perimeter wire via `Part.Wire.makePipeShell`, with a
   fallback to the spec 010 straight per-side cylinder if the sweep fails.
   Spike: valid single solid.
3. **Crowned windshield** — `_build_windshield` arches the top via dense
   Ruled=True sections; the spec 011 frame/pane path is preserved.

## Technical Context
- Files: `deck.py` (`_build_hardtop`, `_build_railings`, `_build_windshield`;
  new section-count + crown params on `HardtopParameters`/`WindshieldParameters`/
  `RailingParameters`), tests, version.
- Manifold/reproducibility/rollback inherited from build_deck.

## Constitution Check
I parametric (section counts/crown are named params w/ defaults) · II reproducible
(dense Ruled=True + deterministic sweep) · III idiomatic (AdditiveLoft +
makePipeShell, PartDesign) · IV fidelity (smoother = closer to reference) ·
V test-gated (geometry: manifold, overshoot, swept-valid, crown) · VI MINOR ·
VII no new API. **PASS.**

## Build sequence
1. `HardtopParameters` += `curl_sections: int = 7`; `_build_hardtop` cosine curl.
2. `RailingParameters` (already has posts); `_build_railings` swept top-rail via
   makePipeShell + straight fallback.
3. `WindshieldParameters` += `crown_height: float`, `crown_sections: int = 5`;
   `_build_windshield` crowned top.
4. Tests + version 1.5.0 -> 1.6.0.
5. Verify on FreeCAD 1.1.1.

## Complexity Tracking
No violations.
