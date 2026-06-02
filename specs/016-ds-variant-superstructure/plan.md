# Implementation Plan: DS-Variant Superstructure (enclosed deck saloon)

**Branch**: `master` (direct-push per spec-register rule) | **Date**: 2026-06-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/016-ds-variant-superstructure/spec.md`

## Summary

Add a second canonical topsides silhouette — the Storebro DS (deck saloon / *styrhytt*) enclosed wheelhouse — selectable on `build_deck` via a new `superstructure_variant: Literal["standard", "ds"] = "standard"` keyword and on the CLI via `--superstructure {standard,ds}`. The default `"standard"` path is byte-identical to the current open-flybridge superstructure (spec 008). When `"ds"` is selected, the builder skips the cabin-trunk/windshield/hardtop/pillars chain and instead builds a single enclosed `Deckhouse` body — a tall, long `PartDesign::AdditiveLoft` (filled solid, raked front + tapered sides + flat roof top-face) seated on the sampled deck-plate top via the existing `_resolve_deck_top_z_at`, with blind `PartDesign::Pocket` window recesses mirroring the spec 011 `_cut_cabin_windows` approach. Deck plate, railings, and all spec 010 hardware are shared verbatim. The hull (spec 007) is reused read-only and never booleaned.

**Technical approach** (from research.md): the deckhouse reuses the proven `_build_cabin_trunk` two-trapezoid loft idiom rather than inventing new geometry — a deckhouse is a cabin trunk grown to wheelhouse height/length, so the same Ruled=True `AdditiveLoft` produces a manifold filled solid (`Solids == 1`, the spec 009 guard), and the same blind-recess windows avoid the specs 009/011 non-manifold trap. The `Deck` aggregate's four open-flybridge slots become `Optional` (None in DS mode); two additive fields (`superstructure_variant: str`, `deckhouse: Deckhouse | None`) carry the variant identity.

## Technical Context

**Language/Version**: Python 3.11+ (matches FreeCAD 1.1's bundled Python 3.11.14)

**Primary Dependencies**: FreeCAD 1.1+ Python API (`Part`, `Sketcher`, `PartDesign`); `storebro.hull` (Hull type), `storebro.render` (spec 015 attributes), `storebro._freecad_check` (version gate). No new third-party deps.

**Storage**: N/A (geometry artifacts: `.FCStd` / STEP / STL / BREP via `storebro.export`).

**Testing**: `pytest` — unit (`tests/unit/`, no FreeCAD) + geometry (`tests/geometry/`, marker `requires_freecad`); `ruff`; `mypy --strict`.

**Target Platform**: Cross-platform library (CI: Ubuntu + macOS × Python 3.11 + 3.12); geometry runtime FreeCAD 1.1+.

**Project Type**: Library + CLI (single project, src-layout `src/storebro/`).

**Performance Goals**: Human-scale geometry build (seconds). One additional loft + N pockets is negligible vs the existing six-body deck build.

**Constraints**: Parametric (no magic numbers in bodies — constitution I); reproducible/byte-identical (constitution II); FreeCAD-idiomatic PartDesign, no raw mesh (constitution III); reference-faithful to `storo34_side_lines.png` within ±1% (constitution IV); the deckhouse solid MUST be `Solids == 1` / `isValid()` (spec 009 manifold guard); full rollback on mid-build failure; back-compat — standard variant unchanged.

**Scale/Scope**: One module touched (`deck.py`) + `cli.py` + `__init__.py` re-exports. One new entity (`Deckhouse`), one new param composite (`DeckhouseParameters` + `DsWindowParameters`), one new enum-like literal selector. Light track.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance |
|---|---|
| **I. Parametric Everything** | PASS — every deckhouse dimension is a `DeckhouseParameters` field with a reference-derived default; no literals in the builder body (X/Z derive from sampled deck geometry + params). |
| **II. Reproducibility** | PASS — pure geometry from params + read-only hull sampling; no timestamps, no env paths. Standard variant output is unchanged (byte-identical). DS output is deterministic for fixed inputs. |
| **III. FreeCAD-Idiomatic** | PASS — `PartDesign::Body` + `Sketcher::SketchObject` + `AdditiveLoft` + `Pocket`, reusing the spec 008/011 idiom. No `Mesh.Mesh`, no vertex-by-vertex. Document stays GUI-editable. |
| **IV. Reference Fidelity** | PASS — defaults measured from `docs/references/storo34_side_lines.png` at the canonical LOA; ±1% target on principal dims; canonical standard variant untouched (new variant is additive, does not replace the default). |
| **V. Test-Gated Releases** | PASS — unit validation tests + geometry tests (manifold, seating, variant-field population, back-compat) + ruff + mypy --strict; manual GUI eyeball is the maintainer pre-tag step. |
| **VI. Public OSS by Default** | PASS — additive public surface (new keyword + dataclasses + wrapper, Optional-ization of existing slots is backward-compatible for readers) → **MINOR** bump. No breaking change. |
| **VII. FreeCAD Version Discipline** | PASS — no new FreeCAD API surface beyond what specs 008/011 already use on 1.1+; the shared `_ensure_freecad_supported()` gate applies. |

**Gate result: PASS — no violations, Complexity Tracking not required.**

## Project Structure

### Documentation (this feature)

```text
specs/016-ds-variant-superstructure/
├── plan.md              # This file
├── research.md          # Phase 0 — design decisions + reference measurements
├── data-model.md        # Phase 1 — DeckhouseParameters, DsWindowParameters, Deckhouse, Deck deltas
├── quickstart.md        # Phase 1 — how to build the DS variant (lib + CLI)
├── contracts/
│   └── deck-build-api.md # Phase 1 — build_deck / CLI contract for the variant
├── spec.md
├── spec.allium
└── checklists/requirements.md
```

### Source Code (repository root)

```text
src/storebro/
├── deck.py        # MODIFIED — add DsWindowParameters, DeckhouseParameters, Deckhouse wrapper;
│                  #   Optional-ize cabin_trunk/windshield/hardtop/hardtop_pillars on Deck;
│                  #   add superstructure_variant + deckhouse fields; add _build_deckhouse +
│                  #   _cut_deckhouse_windows + _validate_cross_hull_deckhouse; branch build_deck
│                  #   on superstructure_variant; extend __all__.
├── cli.py         # MODIFIED — add --superstructure {standard,ds}; thread into build_deck.
├── __init__.py    # MODIFIED — re-export DeckhouseParameters, DsWindowParameters, Deckhouse.
└── render.py      # UNCHANGED — role_for_label already maps "Deckhouse"/"Deck_Deckhouse" labels;
                   #   verify the deckhouse body label resolves to the white superstructure role.

tests/
├── unit/
│   ├── test_deckhouse_params.py      # NEW — DeckhouseParameters + DsWindowParameters validation.
│   ├── test_deck_variant_selector.py # NEW — selector default, contradiction rejection, field population (mocked).
│   └── test_cli_superstructure_flag.py # NEW — --superstructure parsing + default + bad value.
└── geometry/
    ├── test_deckhouse_build.py        # NEW — manifold (Solids==1/isValid), seating, dims ±1%, STL export.
    └── test_deck_variant_backcompat.py # NEW — standard variant bodies unchanged; DS field population.
```

**Structure Decision**: Single-project src-layout (constitution Module Layout). All superstructure geometry lives in `deck.py` per the flat-module-per-body-part rule; composition (variant selection wiring) is in `build_deck` + `cli.py`, never split into a new module. The DS variant is a branch inside the existing `deck.py` builder, not a sibling module — it shares the deck plate, hardware, glazing helpers, rollback, and render path.

## Build Sequence (DS branch inside build_deck)

1. Resolve `superstructure_variant` (default `"standard"`). Validate the contradiction rule: `variant == "ds"` with an explicit `parameters_superstructure` → `DeckParameterError` (FR-014), before any FreeCAD call.
2. Resolve `parameters_deckhouse` (default `DeckhouseParameters()`), validated in `__post_init__`.
3. `_validate_cross_hull_deckhouse(hull, dh)` — length fits LOA, width+walkways fits beam (FR-012), before construction.
4. Build deck plate (shared, unchanged).
5. **DS branch**: `_build_deckhouse(hull, deck_plate, dh, target_doc, added)` → trapezoid loft solid; then `_cut_deckhouse_windows(deckhouse, dh.windows, target_doc, added)` → blind pockets; `_assert_solid_manifold(deckhouse.body, "deckhouse")`. Skip cabin trunk / windshield / hardtop / pillars.
   **Standard branch**: existing six-body chain, untouched.
6. Build railings (shared) + hardware (rubrail, bow pulpit, anchor locker, cleats, lifelines) — shared in both branches. (Lifelines depend on railing posts, not on the deckhouse.)
7. `recompute()` + manifold guards.
8. Render attributes over the per-variant body list (deckhouse white, glass translucent if any — none this spec; windows are recesses).
9. Assemble `Deck(...)` with `superstructure_variant`, `deckhouse` (or None), and the four open-flybridge slots None in DS mode.
10. On ANY exception: `_rollback(target_doc, added)` + re-raise as today.

## Complexity Tracking

No constitution violations. Section intentionally empty.
