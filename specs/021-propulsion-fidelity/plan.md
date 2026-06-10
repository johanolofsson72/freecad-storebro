# Implementation Plan: Propulsion Fidelity (CAD-faithful machinery)

**Branch**: `021-propulsion-fidelity` | **Date**: 2026-06-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/021-propulsion-fidelity/spec.md`

## Summary

Promote the five spec 014 propulsion placeholders to CAD-faithful machinery, all changes confined to `src/storebro/propulsion.py` (plus a render-role line and an optional CLI flag): symmetric-NACA-foil propeller blades with radial twist, a NACA-foil rudder, a shaft coupling flange + a separate strut/P-bracket body, a detailed diesel engine block (sump + head/valve-cover + manifold stubs), and an additive faired shaft-log. Every detail is additive (the hull is never booleaned), each is byte-reproducible, and each is guarded by a manifold-or-fallback gate. The public `build_propulsion` signature is unchanged; new parameters are additive with defaults; with every detail flag off the output is byte-identical to spec 014.

**Technical approach (the load-bearing insight):** the spec 022 reproducibility wall (`AdditiveLoft` volume drift under cumulative OCC state) correlated with **Sketcher arcs / `Sketcher.fillet()`** — the constraint solver is the nondeterministic element. Specs 018 and 020 built dense `Ruled=True` lofts through **straight-segment / polyline** sections and were byte-reproducible (v1==v2 volume). Therefore every foil here is a **dense analytic polyline** (NACA points → `Part.LineSegment` chain, no arcs, no fillets) and every loft is `Ruled=True`. A pre-implementation spike proves this empirically (clarify Q5) before production code; any construction that still drifts flips its default to OFF (opt-in) per the spec 022 precedent.

## Technical Context

**Language/Version**: Python 3.11+ (FreeCAD 1.1 bundled Python)

**Primary Dependencies**: FreeCAD 1.1+ (`Part`, `Sketcher`, `PartDesign`), stdlib `math`/`dataclasses`. No new third-party deps.

**Storage**: N/A (geometry library; outputs `.FCStd`/STEP/STL/BREP via `export.py`)

**Testing**: `pytest` (unit: foil math + parameter dataclasses, no FreeCAD; geometry: `requires_freecad` marker, run via bundled-Python `PYTHONPATH`), `ruff`, `mypy --strict`

**Target Platform**: FreeCAD 1.1+ on macOS/Linux (CI matrix Ubuntu+macOS × Py3.11+3.12)

**Project Type**: Single library (`src/storebro/`, flat-module-per-body-part)

**Performance Goals**: Human-scale build (seconds-to-low-minutes). The propeller blade loft (≤ `blade_sections` × `blade_count` × trains sketches) is the dominant new cost; keep `blade_sections` default modest (5).

**Constraints**: Byte-identical output for identical inputs (constitution II); every body `Solids==1` + `isValid()` + STL-exportable; hull never booleaned; PartDesign-editable (constitution III).

**Scale/Scope**: One module touched (`propulsion.py`, ~1030 LOC today). Net additions: ~6 builder upgrades, 1 new builder (strut), ~3 foil-math helpers, ~25 new parameter fields with defaults, 1 new wrapper (`Strut`) + 1 aggregate list, 1 render-role line, 1 optional CLI flag.

## Constitution Check

*GATE: must pass before Phase 0 and re-checked after Phase 1.*

| Principle | Status | How this plan complies |
|---|---|---|
| I. Parametric Everything | ✅ | Every new dimension (foil thickness ratios, blade-section count, pitch law, flange/bolt sizes, strut sizes, sump/head/stub sizes) is a named dataclass field with a default + a `config`-mirrored constant in the module. No magic numbers in builder bodies. |
| II. Reproducibility (NON-NEGOTIABLE) | ✅ | Foils are analytic polylines (no Sketcher solver), lofts are `Ruled=True`; a pre-impl spike proves volume-identical across ≥3 builds incl. the spec 022 two-open-docs scenario; any drifting construction defaults OFF. With all detail off → byte-identical to spec 014. |
| III. FreeCAD-Idiomatic | ✅ | All construction via `PartDesign::Body` + `Sketcher` + `PartDesign::Pad`/`AdditiveLoft`; no raw mesh. Bodies stay parametric/editable. Foil sketches are standard `Part.LineSegment` geometry. |
| IV. Reference Fidelity | ✅ | Detail makes the running gear *more* reference-faithful (real foils, real diesel silhouette). Defaults sized to RC34 proportions; the ±1% hull/interior bar is unaffected (propulsion is not in the ±1% principal-dimension set). |
| V. Test-Gated | ✅ | New unit tests (foil math, params) + geometry tests (foil section shape, twist, manifold, determinism, fallback, hull-unchanged, placeholder-equivalence, STL). `pytest`+`ruff`+`mypy --strict` gate. GUI eyeball is the maintainer's pre-tag step. |
| VI. Public OSS / SemVer | ✅ | Additive public surface only (new fields with defaults, new `Strut` type, new wrapper fields) → MINOR bump 1.10.0 → 1.11.0. No breaking change. |
| VII. FreeCAD Version Discipline | ✅ | No FreeCAD-version-specific API beyond the spec 014 set already in use. Supported range unchanged. |

**Result: PASS** (no violations; Complexity Tracking not required).

## Project Structure

### Documentation (this feature)

```text
specs/021-propulsion-fidelity/
├── plan.md              # This file
├── research.md          # Phase 0 — foil math, loft reproducibility, fused vs separate topology
├── data-model.md        # Phase 1 — parameter fields, wrappers, aggregate, validation
├── contracts/
│   └── python-api.md     # Phase 1 — public Python/CLI surface delta
├── quickstart.md        # Phase 1 — how to build + verify the detailed train
├── spec.md
├── spec.allium
└── tasks.md             # Phase 2 — /speckit-tasks output (not this command)
```

### Source Code (repository root)

```text
src/storebro/
├── propulsion.py        # THE feature — foil helpers, detailed builders, Strut, fallback gates
├── render.py            # +1 role rule: "Propulsion_Strut" -> bronze
├── cli.py               # optional: --no-propulsion-detail master off-switch
└── __init__.py          # export new Strut type; __version__ 1.10.0 -> 1.11.0

tests/
├── unit/
│   ├── test_propulsion_foil_math.py     # NEW — NACA half-thickness + section polyline (no FreeCAD)
│   └── test_propulsion_detail_params.py # NEW — new param fields, defaults, validation
└── geometry/
    ├── test_propulsion_propeller_foil.py   # NEW — foil section, twist, manifold, fallback
    ├── test_propulsion_rudder_foil.py      # NEW — symmetric NACA section, manifold
    ├── test_propulsion_shaft_detail.py     # NEW — coupling flange + fairing fused; strut separate body
    ├── test_propulsion_engine_detail.py    # NEW — sump/head/stubs, envelope guard, fused
    ├── test_propulsion_detail_determinism.py # NEW — v1==v2 volume for every detailed body + STL
    └── test_propulsion_placeholder_equiv.py  # NEW — all-detail-off == spec 014 build
```

**Structure Decision**: Single library, flat-module-per-body-part (constitution Module Layout). The entire feature lives in `propulsion.py`; `render.py`/`cli.py`/`__init__.py` get one-line touches. This mirrors spec 022 (deck hardware detailing) and spec 024 (interior contoured fittings), which detailed a single module in place.

## Build Sequence (the one task — no stops between steps)

0. **Reproducibility + manifold spike** (`/tmp/spike_021_*.py`, FreeCAD) — BLOCKING GATE. Build each detailed construction (NACA-polyline rudder Pad; stacked-foil `Ruled=True` propeller blade loft; coupling-flange + bolt-boss + fairing fused shaft; strut separate body; sump/head/stub fused engine) ≥3× in fresh docs AND in the two-open-docs scenario; assert `Shape.Volume` byte-identical, `Solids==1`, `isValid()`, STL export OK. Record results in research.md. Any drifting construction → its default flag flips to OFF.
1. **Foil math helpers** (pure Python): `_naca_symmetric_half_thickness(x_over_c, t)` (closed-TE 4-digit), `_naca_section_polyline(chord, t, n_points)` → ordered closed (u,v) loop. Unit-tested without FreeCAD.
2. **Parameter dataclass additions + validation** on `EngineParameters`/`ShaftParameters`/`PropellerParameters`/`RudderParameters` + module `config` constants. Unit-tested.
3. **Rudder NACA foil builder** — replace the flat plate: closed NACA polyline sketch (chord along X, thickness along Y) Pad over span, fuse stock; `naca_foil` flag; manifold-or-fallback to spec 014 plate.
4. **Propeller airfoil blade builder** — replace `_blade_corners` rectangle: per-blade `AdditiveLoft` (Ruled=True) through `blade_sections` foil polylines, each scaled by chord-taper and rotated by the pitch law (root→tip twist), fused with the hub; `airfoil_blades` flag; manifold-or-fallback to spec 014 flat blade. (Default per spike result.)
5. **Coupling flange + shaft-log fairing** — additive Pads fused into the existing shaft `PartDesign::Body`: a coaxial collar disc + a ring of bolt-head bosses at the forward end; a faired (stepped/tapered) coaxial boss at the exit station. `coupling_flange` / `shaft_log_fairing` flags; fairing optional (omit on failure), coupling fused.
6. **Strut / P-bracket** — NEW separate `PartDesign::Body` (`Propulsion_Strut`): a bearing barrel around the shaft mid-run fused with an arm reaching up to the hull bottom; new `Strut` wrapper + `struts: list[Strut]` on `Propulsion`; `strut_bearing` flag; omit-on-failure (optional support).
7. **Detailed engine block** — additive Pads fused into the engine body: narrower sump below, head/valve-cover above, `manifold_stub_count` side stubs; `detailed` flag; re-check the within-envelope guard against the *detailed* top Z; manifold-or-fallback to the spec 014 box.
8. **Manifold-or-fallback wiring** — a `_detail_or_fallback` helper that wraps each detailed builder, validates `Solids==1`+`isValid()`, and on failure rebuilds the spec 014 placeholder (core parts) or drops the body (optional supports). Per-body, per spec 014 rollback discipline.
9. **Render role** — add `("Propulsion_Strut", "bronze")` to `render._ROLE_RULES`; thread the strut bodies into the `build_propulsion` render-target list.
10. **Wrapper/aggregate fields** — add applied-flags to `Propeller`/`Rudder`/`Shaft`/`EngineBlock`; add `Strut` + `Propulsion.struts`.
11. **CLI (optional)** — `--no-propulsion-detail` builds a `PropulsionParameters` with all detail flags off (reproduces spec 014). Keeps the default CLI path on-by-default.
12. **Tests** (unit + geometry) per the structure above; run `pytest`/`ruff`/`mypy --strict`.
13. **Version bump** 1.10.0 → 1.11.0 (`__init__.py` + `pyproject.toml`) + version-consistency test.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Propeller blade loft drifts in volume (spec 022 wall) | Polyline-only sections (no arcs), `Ruled=True`, spike-gated; default flips to opt-in if it still drifts. Fallback to spec 014 flat blade always keeps a valid solid. |
| Foil polyline self-intersects at fine TE → invalid solid | Closed-TE NACA formula (`-0.1036`), minimum section thickness floor, manifold-or-fallback gate. |
| Detailed engine head pierces the clearance ceiling | Envelope guard re-checks the detailed top Z; defaults sized so head fits under the deck plate; guard raises `PropulsionParameterError` before FreeCAD if a custom value would pierce. |
| Strut can't fuse into the tilted shaft → non-manifold | Strut is a SEPARATE body (clarify Q3); barrel+arm fuse within that one body; omit-on-failure if even that fails. |
| Sump drops below the keel | Validate `block_bottom - sump_drop >= keel_z`; default sump_drop (120) < bed height (200) → sump bottom stays above keel. |
| New dataclass fields break existing positional construction | All new fields appended AFTER existing ones with defaults; existing tests construct by keyword → back-compat (data-model.md §Compatibility). |

## Phase 2 note

`/speckit-tasks` will expand this Build Sequence into dependency-ordered tasks (spike first as a hard gate, then foil math + params [parallelizable unit work], then the five geometry builders, then fallback wiring, wrappers, render, CLI, tests, version). `/speckit.analyze` runs between tasks and implement.
