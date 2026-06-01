# Phase 0 Research: Propulsion Module

All Technical Context items were resolved from the existing codebase conventions (hull/deck modules) and the `/clarify` session. No `NEEDS CLARIFICATION` markers remained after `/specify` + `/clarify`. The decisions below record the load-bearing choices.

## Decision 1 — New module vs. extend an existing one

- **Decision**: Create `src/storebro/propulsion.py` as a new flat module.
- **Rationale**: The constitution's "Module Layout (flat-module-per-body-part)" pairs each body group with its own module (`hull`, `deck`, `interior`). Propulsion is a distinct body group with its own parameter namespace and its own seating logic (samples the hull *bottom* / keel depth, not the deck top). Folding it into `deck.py` would bloat an already-large module and couple unrelated concerns.
- **Alternatives considered**: (a) extend `deck.py` — rejected (unrelated concern, import-graph noise); (b) extend `hull.py` — rejected (hull owns the shell only; propulsion is additive equipment).

## Decision 2 — Hull penetration: additive boss vs. boolean cut

- **Decision**: Model the shaft penetration as an **additive stern-tube boss** body; never apply a boolean to the hull solid (FR-007, `/clarify` Q3).
- **Rationale**: Specs 009 and 011 both recorded that boolean cuts on the dense-station hull loft produce non-manifold tessellation that breaks STL export. An additive boss is manifold by construction and keeps the hull's `Solids == 1` guarantee intact. A real through-hull cavity is explicitly deferred (`PropulsionBundle.functional_through_hull_shaft_log_cavity`).
- **Alternatives considered**: `Part.Cut` of a cylinder through the hull bottom — rejected (the exact failure mode specs 009/011 hit).

## Decision 3 — Geometry construction technique per component

- **Decision**:
  - Engine bed + engine block → `PartDesign::Pad` of a rectangle sketch (box-like solids), mirroring the spec 010 anchor-locker builder.
  - Shaft + stern-tube boss + rudder stock → cylindrical `Pad` of a circle sketch on a tilted YZ-offset datum (the `_add_circular_pad` idiom from spec 010), tilted by `shaft.angle_deg` via the datum `AttachmentOffset` rotation.
  - Propeller → hub `Pad` (cylinder) + `blade_count` blade `Pad`s arranged radially (representative flat-ish blades), unioned within one Body.
  - Rudder blade → `Pad` of a chord×span rectangle (representative foil plate), thickness via Pad length.
- **Rationale**: Every component reduces to sketch + Pad (or a small set of Pads in one Body), which is the proven, deterministic, GUI-editable idiom already used across specs 006/008/010. No `AdditiveLoft` Ruled=False (the spec 007/009 overshoot risk) is needed here.
- **Alternatives considered**: `PartDesign::Revolution` for the propeller hub — viable but Pad is simpler and sufficient at representative fidelity; airfoil-accurate blades via lofted aerofoil sections — deferred (`PropellerBody.airfoil_accurate_blade_geometry`).

## Decision 4 — Hull-geometry sampling for seating

- **Decision**: Add two private helpers in `propulsion.py`: `_hull_bottom_z_at(hull, x_mm)` (min Z of hull shape vertices near X = keel depth) and `_hull_half_beam_at(hull, x_mm)` (max |Y| of hull shape vertices near X). Both read `hull.body.Shape.Vertexes`, mirroring `hull._hull_outer_y_and_freeboard_at` and `deck._resolve_deck_top_z_at`.
- **Rationale**: Seating on *actual* sampled geometry is FR-003 and the established pattern. Writing module-local helpers (rather than importing the privates from hull/deck) keeps the import graph clean and the helpers tailored to the bottom/keel sampling propulsion needs.
- **Alternatives considered**: import `hull._hull_outer_y_and_freeboard_at` — usable for the half-beam check but does not give keel depth; analytical estimate from `HullParameters` — rejected (FR-003 requires actual geometry, and the stem-rake/keel-taper from specs 007/009 makes analytics drift).

## Decision 5 — Engine-height ceiling when `deck is None`

- **Decision**: `build_propulsion(hull, deck=None)` is allowed; when no deck is supplied, the engine-height clearance ceiling falls back to the hull sheer Z at the engine station (sampled from the hull shape). When a `Deck` is supplied, use the deck-plate top Z.
- **Rationale**: Keeps the module usable standalone (hull-only) while preferring the more accurate deck ceiling when available. Documented as an Assumption in spec.md.
- **Alternatives considered**: require a deck — rejected (over-constrains the API; the engine fits under the sheer regardless).

## Decision 6 — Default configuration & component defaults

- **Decision** (from `/clarify`): `engine_count=2` (twin) default; `rudder_count` defaults to `engine_count`; `engine_offset_y_mm=400`; `shaft.angle_deg=10`; `propeller.blade_count=3`. Single-screw is centreline (`engine_offset_y_mm=0`).
- **Rationale**: Historically faithful RC34 twin-diesel layout; 3-blade prop and ~10° shaft angle are typical vintage inboard values; an outboard engine offset clears the centreline keel.
- **Alternatives considered**: single-screw default — rejected at `/clarify` (twin is the iconic RC34).

## Decision 7 — CLI integration surface

- **Decision**: `build_propulsion` is called in `cli.py:_run_build` after `build_interior`, on the same document. Two new optional flags: `--engine-count {1,2}` (default = parameter default, 2) and `--no-propulsion` (skip the step).
- **Rationale**: FR-011 requires composition; bodies in the shared document flow into every export format with no registration step (confirmed: `export_fcstd(document)` includes all bodies). The flags give the user the one meaningful layout choice plus an opt-out without bloating the CLI.
- **Alternatives considered**: no flags (always twin) — rejected (engine_count is the one user-facing choice worth exposing); a full `--shaft-angle` etc. flag set — rejected (YAGNI; Python callers override via parameters).

## Decision 8 — Version bump magnitude

- **Decision**: MINOR, 1.0.7 → 1.1.0.
- **Rationale**: Constitution VI governs the public API by semver; a brand-new public module + new CLI flags is a material additive expansion → MINOR. The v1.1+ roadmap (register) explicitly slates propulsion as the v1.1 opener.
- **Alternatives considered**: PATCH — rejected (PATCH is for clarifications/fixes, not a new module).
