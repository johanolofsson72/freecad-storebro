# Phase 0 Research: Interior Detail — Alternativ1 & 2

All "NEEDS CLARIFICATION" resolved in `/clarify` (spec.md → Clarifications). Construction decisions, grounded in `interior.py` (spec 004).

## R1 — Why Part::Feature B-rep, not PartDesign

The interior module (spec 004) builds every compartment as a `Part::Feature` via `Part.makeBox`. That is a B-rep solid from the Part workbench — explicitly allowed by constitution III (which forbids raw MESH: `Mesh.Mesh`, vertex-by-vertex, not the Part workbench). Furniture is many small axis-aligned boxes; `Part.makeBox` + `translate` is trivial, robust, and reproducible, whereas a PartDesign datum+sketch+pad chain per piece is fragile (especially blind, with no FreeCAD on the host) and the interior module never adopted it. Decision: furniture is `Part::Feature` B-rep, matching the module. Galley recesses use boolean `Part.Cut`.

## R2 — Per-type furniture builders (dispatch on compartment_type)

`build_interior` dispatches on `CompartmentSpec.compartment_type`:
- `forward_cabin` → `_build_berth` (base box + cushion box(es))
- `galley` → `_build_galley_counter` (worktop box with sink + stove `Part.Cut` recesses)
- `head` → `_build_head_fittings` (toilet box + sink box)
- `salon` → `_build_salon_furniture` (settee box + table)
Plus `_build_bulkhead` (thin box at the aft boundary) for every furnished compartment.

Each piece is positioned relative to the compartment's `position` (forward-bottom-center) + `dimensions`, so it always lands inside the envelope. The compartment wrapper's `body` becomes a `Part::Compound` of its pieces.

## R3 — Galley recess (the only boolean)

The counter is `Part.makeBox(length, width, counter_thickness)` placed at `counter_height`. Sink + stove recesses are `Part.makeBox` tools (depth `recess_depth < counter_thickness`) positioned on the top face and removed via `counter.cut(tool)`. A blind recess into a solid box is manifold by construction; a post-cut assertion (`len(Solids) == 1 and isValid()`) is the spec 009/011 regression guard. Guard: `recess_depth < counter_thickness` (else reject).

## R4 — Gating to Alt1/Alt2

`build_interior` checks `layout_spec.layout_name in {"Alternativ1", "Alternativ2"}`. When true, the per-type furniture builders run; otherwise the existing `_build_compartment` boxy placeholder is used (Alt3-5 unchanged). Spec 013 widens the set. The builders themselves are layout-agnostic (keyed only by type + envelope), so spec 013 reuses them verbatim.

## R5 — Parameter API

New frozen dataclasses `BerthParameters`, `GalleyParameters`, `HeadParameters`, `SalonParameters`, `BulkheadParameters`, bundled in `FurnitureParameters` (all `field(default_factory=...)`). `build_interior` gains `parameters_furniture: FurnitureParameters | None = None`; `None` → defaults (furniture on for Alt1/Alt2). Validation in each `__post_init__` raising `InteriorParameterError` (the module's existing error type). Cross-compartment envelope checks (furniture larger than compartment) run in `build_interior` where the compartment dims are known.

## R6 — Default dimensions (RC34 1972, estimate-grade)

| Item | Field | Default (mm) |
|---|---|---|
| Berth | base_height / cushion_thickness / cushion_count / wall_inset | 350 / 100 / 1 / 50 |
| Galley | counter_height / counter_thickness / sink_depth / stove_depth | 900 / 40 / 30 / 20 |
| Head | toilet_height / sink_height | 400 / 800 |
| Salon | seat_height / table_height | 400 / 650 |
| Bulkhead | thickness | 25 |

Estimate-grade, refinable in later PATCH bumps (specs 007–011 posture).

## R7 — Version bump

`pyproject.toml` 1.0.5 → 1.0.6 and `storebro.__version__` → 1.0.6 (the spec 010 version-consistency test guards the match).
