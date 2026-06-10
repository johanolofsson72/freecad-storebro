# Phase 0 Research: Interior Layout Expansion

All NEEDS CLARIFICATION were resolved in `/clarify` (spec.md → Clarifications). This records the design decisions that gate implementation.

## R1 — Alt5 mechanism: a `salon_galley` type (clarify Q1)

**Decision**: Add a `salon_galley` compartment type that builds the salon furniture (`_build_salon_furniture`) AND the galley counter (`_build_galley_counter`), both fused into the compartment's compound. The Alternativ5 fixture's combined compartment changes `type: salon` → `type: salon_galley`. The `salon` type stays settee+table only.

**Rationale**: An explicit type keeps the `salon` builder pure and expresses the Alt5 change in canonical fixture data (constitution IV — canonical layouts are fixture-driven). The galley counter reuses the spec 012 builder verbatim, so its manifold guard (`Solids==1`, manifold-or-box fallback) carries over unchanged. Only Alt5's fixture changes (FR-011).

**Alternatives**: A boolean flag on the salon compartment (rejected — adds a parallel furnishing axis; a type is cleaner and matches the existing type-keyed dispatch). Special-casing the Alt5 layout name (rejected — exactly the layout-name coupling FR-002 removes).

## R2 — Furnish by type, not by layout name (clarify Q2)

**Decision**: Remove the `furnished = layout_name in _FURNISHED_LAYOUTS` gate (interior.py:1549). Furniture is dispatched per compartment by its type for every layout. A compartment whose type is in `_FURNISHABLE_TYPES` is furnished; a non-furnishable type (none in v1 — all current types furnish) keeps a structural box. The furniture-fit validation loop runs over every furnishable compartment regardless of layout name.

**Rationale**: FR-002 — custom layouts must furnish like canonical ones. Dispatch-by-type is already how `_build_compartment` chooses a builder; the layout-name gate was a spec 012 scaffolding constant that is no longer needed. Canonical/DS layouts are unaffected (their compartments already use furnishable types).

**Alternatives**: Keep the gate but add custom layout names (rejected — unbounded, custom names are arbitrary). A per-call `furnish=False` opt-out (deferred — not requested; the structural-box path remains reachable only for a future non-furnishable type).

## R3 — New-type fittings (clarify Q3, FR-004)

**Decision**: Map the new types to builders:
- `aft_cabin` → `_build_berth` (reuse — an aft cabin is a berth compartment).
- `dinette` → `_build_salon_furniture` (reuse — a dinette is settee + table).
- `engine_room` → new `_build_engine_room_fitting`: a representative engine-block-like solid (a box with a stepped/raised top, analytic primitives), independent of the propulsion module.
- `wet_locker` → new `_build_wet_locker`: a locker box with one or two internal shelves (analytic boxes fused/cut).
- `salon_galley` → `_build_salon_furniture` + `_build_galley_counter` (both).

**Rationale**: Reusing berth/salon builders keeps the surface small and inherits their tested manifold behavior. engine_room/wet_locker use only analytic Part primitives (box/cut/fuse) — the spec 024 class proven byte-reproducible (no arc lofts, no Sketcher solver), so **no reproducibility spike is required** (unlike spec 021's lofts). The engine_room fitting is interior furniture, NOT the propulsion engine: separate module, separate body, no boolean interaction (the propulsion engine lives in `Propulsion_Engine` bodies; the interior fitting lives in the interior compound).

**Alternatives**: Bespoke new builders for aft_cabin/dinette (rejected — they are berths/settees; reuse is correct). Leaving engine_room structural/empty (rejected — clarify Q3 chose a representative fitting so it reads as furnished).

## R4 — Asymmetric placement + transverse bound (clarify Q4, FR-006/FR-007)

**Decision**: Remove the `position.y != 0` reject in `_parse_compartment_entry`. Add a transverse bound to `_validate_compartment_in_envelope`: reject when `abs(position.y) + width/2 > beam_max/2` (metre-space, using the hull's `beam_max` parameter). Thread `offset_y = position.y * _M_TO_MM` into every furniture builder so furniture follows the compartment transversely.

**Rationale**: Symmetry was a v1.0 simplification, not a geometric necessity. `beam_max/2` is the hull's maximum half-beam — a permissive, parametric, FreeCAD-free bound consistent with the existing metre-space validator (`_validate_compartment_in_envelope` already compares against `beam_max`). A station-specific half-beam would require sampling the hull shape; the interior validators are deliberately parametric/metre-space (spec 004/017), so `beam_max/2` is the faithful choice. Canonical layouts (`y=0`) → `offset_y=0` → byte-identical coordinates, preserving FR-011/SC-005.

**Alternatives**: Sample the hull shape for a station-specific half-beam (rejected — pulls FreeCAD into the validator, breaks the parametric metre-space discipline, and `beam_max/2` is a safe upper bound). Keep symmetry and mirror compartments (rejected — defeats the asymmetric goal).

## R5 — Backward compatibility & versioning (FR-010, FR-011)

**Decision**: `build_interior` signature unchanged. New compartment types and off-centre placement are opt-in via YAML content. New `EngineRoomParameters`/`WetLockerParameters` are appended to `FurnitureParameters` with defaults. → additive public surface → **MINOR** bump 1.11.0 → **1.12.0**. Canonical Alternativ1–4 + DS build byte-identically (offset_y=0, type set unchanged for them); Alternativ5 changes only because its fixture compartment type changes.

**Rationale**: Constitution VI semver. The `offset_y=0` path is identical to the pre-025 hardcoded `0`, so a canonical-byte-identity test (volume + digest for Alt1–4 + DS) proves no regression.

**Alternatives**: MAJOR bump (rejected — nothing removed/re-signatured). Versioned opt-in flag for asymmetry (rejected — YAML content is the natural opt-in).
