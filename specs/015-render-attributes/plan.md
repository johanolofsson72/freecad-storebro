# Implementation Plan: Render Attributes (Colors & Materials)

**Branch**: `master` (solo / direct-push) | **Date**: 2026-06-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/015-render-attributes/spec.md`

## Summary

Assign deterministic, role-keyed colors + named materials to every shape-bearing body the library produces (hull, deck, interior, propulsion) so the model reads as a real Storebro. A new `render.py` module owns a central palette (`role → RenderAttribute{rgba, material}`) and a public applier `apply_render_attributes(objects, *, enabled=True)`. Each public `build_*` grows an additive `apply_render_attributes: bool = True` kwarg that, when on, applies the palette to the top-level objects it just created. The CLI grows `--no-colors`. Attributes are stored as **custom App data properties** (`App::PropertyColor` + `App::PropertyMaterial`) on each object — empirically verified to persist headless in `Document.xml` across save/reload — with a best-effort ViewObject bridge only when a live GUI view object is present.

## Technical Context

**Language/Version**: Python 3.11+ (FreeCAD 1.1 bundled CPython 3.11.x)

**Primary Dependencies**: FreeCAD 1.1+ Python API (`App`, `Part`, `PartDesign`); no new third-party deps

**Storage**: `.FCStd` document (zip of `Document.xml` + brep); render attributes persist in `Document.xml` as object data properties

**Testing**: pytest — unit (`not requires_freecad`) for the palette + role-resolution pure logic; geometry (`requires_freecad`) for applier persistence, geometry-invariance, determinism, and CLI opt-out. **FreeCAD 1.1.1 is runnable on this host** via `PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib` (bundled CPython 3.11.14), so the geometry tier runs here — unlike specs 010–013.

**Target Platform**: macOS / Linux with FreeCAD 1.1+

**Project Type**: Python library + CLI (`storebro`)

**Performance Goals**: N/A — coloring is O(number of bodies) attribute assignment, negligible vs geometry build

**Constraints**: Reproducible/byte-identical (constitution II); headless-safe (ViewObject is `None` in console mode — verified); no geometry mutation; FreeCAD-idiomatic data properties (constitution III); additive API only (constitution VI)

**Scale/Scope**: ~25 distinct body roles across 4 modules; single new module + additive kwargs

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Parametric Everything** — PASS. Colors are named constants in a central `PALETTE` dict, not magic numbers scattered in body functions. No RGBA literal at any construction site.
- **II. Reproducibility (NON-NEGOTIABLE)** — PASS. Palette values are fixed constants; object iteration order is deterministic; RGBA→8-bit storage quantization is deterministic (same input → same stored bytes, verified). No timestamps, no randomness, no env paths. STEP/STL/BREP carry no appearance → exports stay byte-identical.
- **III. FreeCAD-Idiomatic** — PASS. Uses `App::PropertyColor` / `App::PropertyMaterial` data properties + `ViewObject.ShapeAppearance`/`Transparency` bridge. No mesh manipulation. Geometry/parametric history untouched.
- **IV. Reference Fidelity** — PASS (cosmetic only). Colors chosen to match `docs/references/` Storebro appearance; no dimensional impact.
- **V. Test-Gated Releases** — PASS. pytest + ruff + mypy --strict gates apply; geometry tier runs on this host; GUI eyeball remains the maintainer's pre-tag step.
- **VI. Public OSS by Default** — PASS. New surface is additive (new `render` module exports + `apply_render_attributes` kwarg on each `build_*`); MINOR bump 1.1.0 → 1.2.0.
- **VII. FreeCAD Version Discipline** — PASS. No new FreeCAD version constraint; data-property + ViewObject-when-present pattern works across 1.1.x.

**Result: PASS — no violations, Complexity Tracking not required.**

## Project Structure

### Documentation (this feature)

```text
specs/015-render-attributes/
├── plan.md              # This file
├── research.md          # Phase 0 output — FreeCAD color/material mechanism decision
├── data-model.md        # Phase 1 output — RenderAttribute / palette / role mapping
├── quickstart.md        # Phase 1 output — how to build a colored model + opt out
├── contracts/
│   └── render-api.md    # Phase 1 output — public API contract for render.py + kwargs
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
src/storebro/
├── render.py            # NEW — palette, RenderAttribute, role resolution, apply_render_attributes()
├── hull.py              # build_hull gains apply_render_attributes: bool = True
├── deck.py              # build_deck gains apply_render_attributes: bool = True
├── interior.py          # build_interior gains apply_render_attributes: bool = True
├── propulsion.py        # build_propulsion gains apply_render_attributes: bool = True
├── cli.py               # gains --no-colors flag; threads apply_render_attributes through builds
└── __init__.py          # exports render symbols; __version__ 1.1.0 → 1.2.0

tests/
├── unit/
│   ├── test_render_palette.py         # palette completeness, determinism, role resolution (no FreeCAD)
│   └── test_version_consistency.py    # bump to 1.2.0
└── geometry/
    ├── test_render_apply.py           # applier sets/persists data props; default neutral for unknown role
    ├── test_render_geometry_invariance.py  # volume/bbox/solids/validity unchanged
    ├── test_render_determinism.py     # two builds → identical attributes; exports byte-identical
    └── test_render_cli_opt_out.py     # --no-colors / apply_render_attributes=False → no attrs, geometry identical
```

**Structure Decision**: Single new flat module `render.py` (matches the constitution's flat-module layout) owns all cosmetic logic. Body modules stay geometry-focused and gain one additive kwarg each, delegating to `render.apply_render_attributes`. Composition stays in `cli.py` per the constitution's "composition never inside a body-part module" rule — but each `build_*` colors its own returned objects so direct library callers also get a colored model (FR-007).

## Complexity Tracking

> No constitution violations — section intentionally empty.
