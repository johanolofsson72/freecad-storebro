# Implementation Plan: Interior Contoured Fittings

**Branch**: `master` (solo, direct-push) | **Date**: 2026-06-03 | **Spec**: [spec.md](./spec.md)

## Summary

Contour the specs 012/013 furniture (currently `Part.makeBox` slabs) using
`Part` B-rep ops on the existing Part::Feature bodies — the interior idiom. Five
groups, each behind a `contoured` flag (default on) with a manifold-or-fallback
gate to the spec 012/013 box:

1. **Cushions** (berth sub-cushions + settee) — rounded box (`makeFillet`) +
   **tufting buttons** (cut-sphere grid) + **piping welt** (fused rounded frame)
   + **fold creases** (cut grooves). Spiked: `Solids==1`, byte-reproducible.
2. **Berth seams** — split the cushion slab into `cushion_segments` rounded
   sub-cushions separated by seam gaps.
3. **Toilet + faucet** — rounded pedestal fused with a bowl cylinder; a faucet
   (stem + spout cylinders) on the sink.
4. **Galley fascia** — rounded worktop edges + a forward fascia panel (the
   spec 012 sink/stove `Solids==1` guard preserved).
5. **Curved bulkheads** — filleted vertical edges + a rounded-top doorway cut
   where the compartment is tall enough.

A spike (`/tmp/spike_024*.py`) proved every op manifold AND **byte-reproducible**
(filleted/cut/fused volumes identical across builds — no spec 022 arc-loft
trouble), so constitution II holds and the furniture-determinism tests stay green.

## Technical Context

**Language/Version**: Python 3.11 (FreeCAD 1.1.1)
**Primary Dependencies**: FreeCAD `Part` (`makeBox`/`makeFillet`/`makeSphere`/`makeCylinder`/`fuse`/`cut`); `interior.py` furniture builders + `_box`.
**Testing**: pytest; ruff; mypy --strict
**Constraints**: every contoured piece `Solids==1 && isValid()` or deterministic box fallback; `contoured=False` byte-identical to specs 012/013; reproducible.
**Scale/Scope**: `interior.py` furniture builders + 5 parameter dataclasses.

## Constitution Check

- **I. Parametric** — PASS. Every contour dimension is a named, defaulted, validated field.
- **II. Reproducible** — PASS. All ops analytic + deterministic (spiked: identical volumes across builds). This is the key gate, learned from spec 022.
- **III. FreeCAD-idiomatic** — PASS. `Part` B-rep on Part::Feature furniture (spec 004/012 idiom); no raw mesh.
- **IV. Reference-faithful** — PASS. Silhouette-grade contour within ±1% on principal dims.
- **V. Test-gated** — PASS. Unit (params/validation) + geometry (manifold, fallback, determinism, back-compat).
- **VI/VII** — PASS. Additive MINOR; `__version__` 1.9.0 → 1.10.0.

## Phase 0: Research

See [research.md](./research.md). Spikes proved rounded boxes, cut-sphere
tufting buttons, fused piping welt, cut fold grooves, the pedestal+bowl toilet,
the faucet, and the rounded-top doorway bulkhead all stay `Solids==1` valid AND
byte-reproducible across builds.

## Phase 1: Design

- **data-model.md** — the five furniture dataclasses' new fields.
- **contracts/** — additive fields only; no removals.

## Implementation sequence

1. `interior.py` helpers: `_rounded_box`, `_cushion` (rounded + buttons + piping
   + folds), `_manifold_or_box` gate.
2. Extend `BerthParameters`/`SalonParameters`/`HeadParameters`/`GalleyParameters`/
   `BulkheadParameters` with contour + fabric fields + validation.
3. Refit `_build_berth` (segmented contoured cushions), `_build_salon_furniture`
   (contoured settee), `_build_head_fittings` (toilet+bowl+faucet),
   `_build_galley_counter` (edges+fascia), `_build_bulkhead` (rounded + doorway).
4. Tests: unit (params) + geometry (manifold/fallback/determinism/back-compat/STL).
5. Version 1.9.0 → 1.10.0.

## Complexity Tracking
No constitution violations; table omitted.
