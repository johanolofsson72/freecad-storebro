# Implementation Plan: Deck Hardware Detailing

**Branch**: `master` (solo, direct-push) | **Date**: 2026-06-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/022-deck-hardware-detailing/spec.md`

## Summary

Detail the five spec 010 deck-hardware placeholders in `src/storebro/deck.py` to a contoured, foundry-faithful level, all as **additive PartDesign bodies seated on sampled geometry** — the hull and deck plate are never booleaned. Five refinements, each promoted to its full scope after the elicitation decision:

1. **Rubrail** — rounded moulded outboard face (`Ruled=True` AdditiveLoft of a Sketcher-arc section), with a **manifold-or-fallback** chamfered profile; plus a separate **chrome insert** strip body running the rubrail length.
2. **Bow pulpit** — bent tube via `PartDesign::AdditivePipe` along an arc-filleted path (spec 020 swept-rail idiom), plus a **torus weld-bead** body at each joint; manifold-or-fallback to the spec 010 straight `_pd_circle_pad` cylinders.
3. **Lifelines** — **true catenary** (`a = span²/8·sag`, `z = a·cosh(x/a) − a`) sampled into an AdditivePipe path; manifold-or-fallback to the straight tube.
4. **Cleats** — tapered base (`Ruled=True` AdditiveLoft, bottom footprint > top) + curved horns (AdditivePipe arc) whose neck-posts **penetrate the base** so the fuse merges to a single solid.
5. **Anchor locker** — recessed cavity via blind `PartDesign::Pocket` on the locker body only, plus a separate **lid** body seated over the cavity.

All new shape-controlling fields are added **additively + defaulted + validated** to the five existing parameter dataclasses; the chrome insert gets a render role in `render.py`. No public API removed.

## Technical Context

**Language/Version**: Python 3.11 (FreeCAD 1.1.1 bundled interpreter)

**Primary Dependencies**: FreeCAD 1.1.1 (`Part`, `Sketcher`, `PartDesign`); existing `deck.py` helpers (`_pd_make_datum_xy/yz/xz`, `_pd_circle_pad`, `_pd_close_loop_constraints`, `_pd_get_origin_plane`, `_sheer_samples_mm`, `_interp_outer_y_at`, `_resolve_deck_top_z_at`); `render.py` `PALETTE` / `_ROLE_RULES`.

**Storage**: N/A (geometry built in-memory, exported via spec 002 writers)

**Testing**: pytest (unit + `requires_freecad` geometry tier); `uv run pytest`, `ruff`, `mypy --strict`

**Target Platform**: FreeCAD 1.1+ on macOS/Linux

**Project Type**: Parametric CAD library (`storebro`)

**Performance Goals**: human-scale build (seconds); no new global density knob — sweeps use ≤ 12 path points

**Constraints**: every produced/modified body `Solids == 1 && isValid()`; hull + deck plate byte-identical with vs without hardware; STL watertight

**Scale/Scope**: single module (`deck.py`) + one render-role addition (`render.py`); ~5 builders extended, 5 dataclasses extended, 1 new role

## Constitution Check

*GATE: must pass before Phase 0. Re-check after Phase 1.*

- **I. Parametric** — PASS. Every new dimension (fillet radius, chamfer width, insert thickness/height/inset, bend radius, weld-bead radius, sag depth, base taper, horn curvature, cavity depth/inset, lid thickness/presence) is a named, defaulted, validated dataclass field. No magic numbers in builder bodies.
- **II. Reproducible** — PASS. Pure geometry from parameters; no timestamps/random/env paths. Catenary + fillet are deterministic closed-form.
- **III. FreeCAD-idiomatic** — PASS. All construction uses `PartDesign` (AdditiveLoft, AdditivePipe, Pad, Pocket, Revolution for the torus bead) + `Sketcher` + `Part` B-rep primitives. No raw mesh. Matches the existing deck builders.
- **IV. Reference-faithful** — PASS. Contours approximate the Alternativ3 / storebro reference set within ±1% on principal dimensions; fine contour is visual-only per the spec's "foundry-faithful" definition.
- **V. Test-gated** — PASS. Unit tests for every new param + validation; geometry tests assert `Solids==1`/`isValid()`, fallback behaviour, hull/deck invariance, render roles.
- **VI. Public OSS / VII. Version-disciplined** — PASS. Additive MINOR (new public fields, no removals); `__version__` 1.7.0 → 1.8.0.

**No violations. No complexity-tracking entries required.**

## Project Structure

### Documentation (this feature)

```text
specs/022-deck-hardware-detailing/
├── spec.md
├── spec.allium
├── plan.md            # this file
├── research.md        # spike results (de-risk evidence)
├── data-model.md      # the 5 extended dataclasses + new bodies
├── quickstart.md      # how to build + eyeball the refined hardware
├── checklists/requirements.md
└── tasks.md           # /speckit-tasks output
```

### Source Code

```text
src/storebro/
├── deck.py            # extend _build_rubrail, _build_bow_pulpit,
│                      #   _build_lifelines, _build_cleats, _build_anchor_locker
│                      #   + the 5 parameter dataclasses; add a _pd_additive_pipe
│                      #   + _pd_revolve_torus helper if it reduces duplication
└── render.py          # add Deck_RubrailChromeInsert (+ weld-bead) → chrome role

tests/
├── unit/              # param validation + role-resolution tests (no FreeCAD)
└── geometry/          # requires_freecad: manifold, fallback, invariance, roles
```

## Phase 0: Research (spike-driven)

See [research.md](./research.md). A FreeCAD 1.1.1 spike (`/tmp/spike_022.py`) proved all six refined constructions manifold-safe (`Solids==1 && isValid()`):

| Construction | Verdict | Note |
|---|---|---|
| Rounded rubrail loft (`Ruled=True`) | ✅ | arc section → closed solid |
| Swept bent pulpit tube (AdditivePipe) | ✅ | filleted wire spine |
| Torus weld bead | ✅ | separate body, chrome role |
| Catenary lifeline (`a=L²/8·sag`) | ✅ | exact 25 mm mid dip at default |
| Contoured cleat | ✅ | **horns must penetrate base** to fuse to 1 solid |
| Locker cavity + lid | ✅ | Pocket on locker only; lid separate |

No NEEDS CLARIFICATION remain. The only construction subtlety (cleat horn must overlap the base) is captured as a build rule.

## Phase 1: Design & Contracts

- **data-model.md** — the five extended dataclasses with every new field, default, range, and validation message; the new bodies (`ChromeInsert`, weld-bead torus, `LockerLid`) and their render roles.
- **contracts/** — the public CLI/library surface is unchanged in shape (same `build_deck(..., parameters_hardware=...)`); only additive fields. `contracts/hardware-params.md` records the new fields as the library contract delta.
- **quickstart.md** — `storebro build` + open the deck in FreeCAD; what each refinement should look like vs the reference.

## Implementation sequence

1. **render.py** — add the chrome-insert role rule (`Deck_RubrailChromeInsert`, `Deck_Pulpit*WeldBead*` → chrome) so the bodies colour correctly. Lid reuses the existing teak role.
2. **deck.py dataclasses** — extend `RubrailParameters`, `BowPulpitParameters`, `LifelineParameters`, `CleatParameters`, `AnchorLockerParameters` with the new fields + `__post_init__` validation (raise `DeckParameterError`).
3. **deck.py helpers** — add `_pd_additive_pipe(...)` (factoring the spec 020 sweep) and `_pd_revolve_torus(...)` for weld beads, if they cut duplication.
4. **_build_rubrail** — rounded arc section + chamfer fallback gate; chrome insert body.
5. **_build_bow_pulpit** — AdditivePipe bent path + weld-bead bodies + straight fallback.
6. **_build_lifelines** — catenary AdditivePipe path + straight fallback.
7. **_build_cleats** — tapered AdditiveLoft base + curved AdditivePipe horns (overlapping the base).
8. **_build_anchor_locker** — Pocket cavity + separate lid body.
9. **Tests** — unit (params/validation/roles) + geometry (manifold/fallback/invariance/roles).
10. **Version** — bump `__init__.py` 1.7.0 → 1.8.0 + `test_version_consistency`.

## Complexity Tracking

No constitution violations; table omitted.
