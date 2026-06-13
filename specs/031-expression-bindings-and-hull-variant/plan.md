# Implementation Plan: Expression Bindings + Hard-Chine Hull Variant

**Branch**: `master` (solo / direct-push) | **Date**: 2026-06-13 | **Spec**: [spec.md](./spec.md)

**Input**: `specs/031-expression-bindings-and-hull-variant/spec.md`

## Summary

Two items, per the 2026-06-13 user scope decision:

- **Item 1 — hard-chine hull variant (IMPLEMENT):** add `hull_variant: Literal["standard",
  "hard_chine"] = "standard"` as a `build_hull` keyword (mirroring `build_deck`'s
  `superstructure_variant`). `"standard"` is byte-identical to today's hull. `"hard_chine"` reshapes
  the 5-vertex `PENTAGON_LEGACY` station — the v1 chine vertex is pushed outboard (toward the
  topside half-beam) and up (shallower chine depth) — flattening the bottom and sharpening the chine,
  while keeping vertex count = 5 so the dense `Ruled=True` `AdditiveLoft` stays vertex-compatible.
  A manifold-or-fallback gate rebuilds the standard hull (and sets `variant_applied=False`) if the
  hard-chine loft is not a single valid solid. The `Hull` wrapper records `hull_variant` +
  `variant_applied`. Threaded through the CLI as `--hull-variant`.

- **Item 2 — expression bindings (SPIKE-DEFER):** documented in research.md, tracked as a `deferred`
  Allium item; **no `setExpression` code ships.** FreeCAD is unavailable to verify byte-reproducibility
  into `Document.xml` (spec 028 surface).

## Technical Context

**Language/Version**: Python 3.11+ · **Primary Dependencies**: FreeCAD 1.1+ (`Part`, `Sketcher`,
`PartDesign`) · **Storage**: N/A · **Testing**: pytest; unit (no FreeCAD) for variant validation +
default-preservation + CLI wiring; `requires_freecad` for geometry (manifold, variant-differs,
reproducible) run by the maintainer · **Project Type**: library (`storebro`) · **Performance**:
no regression vs current hull build · **Constraints**: byte-reproducible (constitution II);
FreeCAD-idiomatic station-loft (constitution III); parametric, no magic numbers (constitution I).

**Scale/Scope**: `src/storebro/hull.py` (variant branch + `_StationProfile.chine_z_factor` +
`build_hull` keyword + fallback + `Hull` fields) and `src/storebro/cli.py` (`--hull-variant`).
New unit + `requires_freecad` tests.

## Constitution Check

*GATE: pass before Phase 0; re-check after Phase 1.*

- **I. Parametric**: PASS — variant reshaping via named ratio constants
  (`_HARD_CHINE_*`); `chine_z_factor` becomes a named profile field (replaces a hardcoded `0.6`).
- **II. Reproducible**: PASS — analytic station vertices, `Ruled=True`, no Sketcher solver, no
  timestamps; `"standard"` path untouched → byte-identical; same variant twice → identical.
- **III. FreeCAD-idiomatic**: PASS — reuses the existing station-loft + mirror flow; only vertex
  positions change. **Item 2 (expression bindings, the other editability lever) is deferred** — not
  a violation, an explicitly deferred enhancement.
- **IV. Reference-faithful**: PASS — hard-chine is an alternative authentic Storebro topside form,
  opt-in; the reference round-ish default is unchanged.
- **V. Test-gated**: PASS — unit (variant validation) + `requires_freecad` geometry; GUI eyeball is
  the maintainer's pre-tag step.
- **VI/VII. OSS / version-disciplined**: PASS — additive MINOR (new optional keyword +
  back-compat default + additive `Hull` fields); no breaking signature change.

**No gate violations. No complexity deviations.**

## Project Structure

```text
specs/031-expression-bindings-and-hull-variant/
├── spec.md          # /specify + /clarify
├── spec.allium      # /allium:elicit (0 errors; deferred + open-question for item 2)
├── plan.md          # this file
├── research.md      # Phase 0 — hard-chine reshaping + the DEFERRED expression-bindings design
├── data-model.md    # Phase 1 — the variant knob, chine_z_factor, Hull fields, validation
├── quickstart.md    # Phase 1 — build/verify a hard-chine hull
├── contracts/
│   └── build_hull.md  # public-API delta (the additive keyword + Hull fields)
└── tasks.md         # /speckit-tasks
```

Source touched: `src/storebro/hull.py`, `src/storebro/cli.py`. Tests:
`tests/unit/test_hull_variant.py` (new), `tests/geometry/test_hull_variant_geom.py` (new,
`requires_freecad`), plus CLI unit coverage.

## Phase 0: Research

See [research.md](./research.md). Resolves: (a) hard-chine reshaping = move v1 outboard+up via named
factors on the existing pentagon (loft-safe, 5 vertices); (b) `chine_z_factor` additive profile
field (default 0.6 → byte-identical standard); (c) keyword placement on `build_hull` (mirror
`superstructure_variant`); (d) manifold-or-fallback structure (rebuild standard stations on
non-manifold, `variant_applied=False`); (e) SC-002 metric = amidships chine_beam_ratio; (f) the
**deferred** expression-bindings design + why it can't be verified here.

## Phase 1: Design & Contracts

- [data-model.md](./data-model.md) — variant keyword, `chine_z_factor`, `Hull.hull_variant` /
  `Hull.variant_applied`, validation.
- [contracts/build_hull.md](./contracts/build_hull.md) — public-API delta.
- [quickstart.md](./quickstart.md) — build + verify.

Post-design constitution re-check: **PASS**.
