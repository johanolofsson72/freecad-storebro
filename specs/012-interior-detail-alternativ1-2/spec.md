# Feature Specification: Interior Detail — Alternativ1 & 2

**Feature Branch**: `012-interior-detail-alternativ1-2`

**Created**: 2026-05-29

**Status**: Draft

**Input**: User description: "Replace the boxy Alternativ1 + Alternativ2 interior placeholders with proper furniture: bulkheads, berths with cushions, galley with sink/stove/counter cutouts, heads with toilet/sink, salon with seating + table. Reference Alternativ1.JPG / Alternativ2.JPG. Keep PR scope to Alt1 + Alt2; Alt3-5 follow in spec 013 and reuse the helpers."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Furnished forward cabin & salon (Priority: P1)

A scale modeler builds the Alternativ1 interior and, instead of four grey boxes, sees a V-berth with cushions in the forward cabin and a settee with a table in the salon — the boat reads as a liveable interior.

**Why this priority**: Berths and salon seating are the largest, most recognizable furniture and exercise the core mechanic (per-compartment-type furniture builders keyed off the compartment spec). Getting them right de-risks the galley/head detail.

**Independent Test**: Build the Alternativ1 interior; confirm the `forward_cabin` compartment contains berth + cushion bodies and the `salon` compartment contains seating + a table body, each sized to fit inside the compartment envelope.

**Acceptance Scenarios**:

1. **Given** the Alternativ1 layout, **When** `build_interior` runs, **Then** the forward cabin contains a berth base plus a cushion on top, both within the compartment envelope, symmetric about the centerline.
2. **Given** the Alternativ1 layout, **When** `build_interior` runs, **Then** the salon contains a settee/seating body and a table body, both within the compartment envelope.
3. **Given** furniture parameters overriding berth height, **When** `build_interior` runs, **Then** the berth height matches the supplied value and the cushion still sits on top of the berth.

---

### User Story 2 - Galley with worktop cutouts (Priority: P2)

The same modeler looks at the galley and sees a counter/worktop with recessed cutouts for a sink and a stove — not a solid block.

**Why this priority**: The galley is the second-strongest detail and exercises the boolean-cut mechanic (sink/stove recesses). It depends only on the galley compartment, so it layers cleanly after the berths/salon.

**Independent Test**: Build the Alternativ1 interior; confirm the `galley` compartment contains a counter body with sink and stove recesses cut into its top, all within the compartment envelope, with the counter remaining a single solid.

**Acceptance Scenarios**:

1. **Given** the Alternativ1 layout, **When** `build_interior` runs, **Then** the galley contains a counter body with a sink recess and a stove recess cut into the worktop, and the counter remains a single closed solid.
2. **Given** a sink/stove recess deeper than the counter thickness, **When** parameters are validated, **Then** construction is rejected with a clear parameter error before any malformed shape is produced.
3. **Given** zero galley cutouts requested, **When** `build_interior` runs, **Then** the counter is built without recesses (no error).

---

### User Story 3 - Furnished head, bulkheads, and Alternativ2 (Priority: P3)

The modeler sees a toilet and sink in the head, bulkheads separating the compartments, and the same level of detail when switching to the Alternativ2 layout.

**Why this priority**: The head fittings are the smallest items; bulkheads are shared structure; and Alternativ2 coverage confirms the type-keyed builders generalize. This story closes the spec.

**Independent Test**: Build the Alternativ1 and Alternativ2 interiors; confirm the head contains toilet + sink bodies, bulkheads exist between compartments, and both layouts produce furnished (non-boxy) compartments.

**Acceptance Scenarios**:

1. **Given** the Alternativ1 layout, **When** `build_interior` runs, **Then** the head contains a toilet body and a sink body within the compartment envelope.
2. **Given** either Alternativ1 or Alternativ2, **When** `build_interior` runs, **Then** a thin bulkhead body separates adjacent compartments at their shared boundary.
3. **Given** the Alternativ2 layout, **When** `build_interior` runs, **Then** every compartment is furnished by the same type-keyed builders used for Alternativ1.

---

### Edge Cases

- **Furniture exceeds compartment**: a furniture piece sized larger than its compartment envelope MUST be rejected at validation (a berth longer than the cabin, a counter taller than the galley).
- **Recess too deep**: a galley sink/stove recess depth ≥ the counter thickness MUST be rejected (the spec 009/011 non-manifold lesson — blind recesses stay manifold only while shallower than the solid).
- **Zero-count furniture**: zero cushions / zero galley cutouts / a furniture piece disabled builds the rest without raising.
- **Non-Alt1/2 layouts**: building Alternativ3/4/5 in spec 012 leaves those layouts as the existing boxy placeholders (detailed furniture is gated to Alt1/Alt2 here; Alt3-5 land in spec 013). No error.
- **Manifold preservation**: each cut furniture solid (the galley counter) MUST remain a single closed manifold so STL export is unaffected.
- **Reproducibility**: identical layout + parameters produce byte-identical geometry.
- **Partial build failure**: a failure mid-furniture-build rolls the whole `build_interior` call back to its pre-call state.

## Clarifications

### Session 2026-05-29

- Q: Keep each compartment's solid placeholder box, or replace it? → A: Replace it. For furnished (Alt1/Alt2) compartments the solid placeholder box is dropped; the compartment is represented by its furniture bodies plus a thin bulkhead at the compartment's aft boundary. The compartment wrapper's `body` becomes a `Part::Compound` of its furniture + bulkhead.
- Q: Furniture construction technique? → A: `Part::Feature` B-rep solids (`Part.makeBox` + translate), matching the EXISTING interior module idiom (spec 004) rather than the PartDesign chains used for the hull/deck shells. Galley sink/stove recesses are boolean `Part.Cut` of small boxes from the counter. This is constitution-compliant — constitution III forbids raw MESH (`Mesh.Mesh`, vertex-by-vertex), not the Part workbench B-rep, which is in the allowed list. PartDesign datum+sketch+pad chains were rejected here as over-fragile for many small furniture pieces (the interior module never adopted them, by design).
- Q: Galley sink/stove cutouts — through-holes or blind recesses? → A: Blind recesses pocketed into the counter worktop (manifold by construction), consistent with the spec 011 porthole/window decision and the spec 009 non-manifold lesson. A recess depth ≥ counter thickness is rejected.
- Q: Which layouts get detailed furniture in this spec? → A: Only Alternativ1 and Alternativ2 (by layout name). Alternativ3/4/5 keep their existing boxy placeholders; spec 013 enables them by flipping the gate. The type-keyed furniture builders are written generically so spec 013 reuses them unchanged.
- Q: Furniture parameter API surface? → A: A new optional composite `FurnitureParameters` (bundling per-type sub-dataclasses: berth, galley, head, salon, bulkhead) passed via a new `parameters_furniture` keyword argument on `build_interior`. Additive; furniture on by default for Alt1/Alt2.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: For the Alternativ1 and Alternativ2 layouts, `build_interior` MUST replace each compartment's boxy placeholder with type-keyed furniture: `forward_cabin` → berth + cushion(s); `galley` → counter with sink + stove recesses; `head` → toilet + sink; `salon` → seating + table. Bulkheads MUST separate adjacent compartments.
- **FR-002**: Furniture MUST be FreeCAD-idiomatic B-rep solids — `Part::Feature` via `Part.makeBox` (matching the interior module's existing spec 004 idiom), with galley recesses via boolean `Part.Cut`. No raw mesh (`Mesh.Mesh`/vertex-by-vertex). The Part workbench B-rep is constitution-III-compliant; PartDesign chains are not required for interior furniture.
- **FR-003**: Each furniture class MUST have its own frozen parameter dataclass (mm/degree units) with `__post_init__` validation raising the interior module's existing parameter-error type, naming the offending field.
- **FR-004**: All furniture MUST be positioned relative to the ACTUAL compartment spec (its position + dimensions from the layout), so a piece always sits inside its compartment envelope.
- **FR-005**: Galley sink/stove cutouts MUST be blind recesses into the counter worktop (boolean `Part.Cut` of a shallow box from the counter top), NOT through-holes; a recess depth ≥ the counter thickness MUST be rejected before construction.
- **FR-006**: A furniture piece larger than its compartment envelope MUST be rejected at parameter/cross-compartment validation with a clear error, before any FreeCAD call where possible (after the compartment box where the envelope is needed).
- **FR-007**: After cuts, the galley counter MUST remain a single closed manifold (validated by solid count + validity), so STL export is unaffected.
- **FR-008**: Furniture MUST be built by default for Alternativ1/Alternativ2 — existing `build_interior(..., layout="Alternativ1")` callers receive the furniture automatically with RC34 1972 estimate-grade defaults.
- **FR-009**: A new optional composite `FurnitureParameters` (per-type sub-dataclasses: berth, galley, head, salon, bulkhead) MUST let callers override furniture parameters, passed via a new `parameters_furniture` keyword argument on `build_interior`; it MUST be additive and not break the existing signature. For furnished compartments the solid placeholder box is replaced — the compartment wrapper's `body` becomes a `Part::Compound` of its furniture + a thin aft bulkhead.
- **FR-010**: Zero-count furniture (zero cushions, zero galley cutouts, a piece disabled) MUST build the rest without raising.
- **FR-011**: Detailed furniture MUST be gated to Alternativ1/Alternativ2 in this spec; Alternativ3/4/5 keep their existing boxy placeholders (spec 013 extends the type-keyed helpers to them). The helpers MUST be written generically so spec 013 only flips the gate.
- **FR-012**: On any FreeCAD-side failure during furniture construction, `build_interior` MUST roll back every object it added and restore the document to its pre-call state.
- **FR-013**: Furniture geometry MUST be reproducible: identical layout + parameters → byte-identical output, no timestamps/random/env values.
- **FR-014**: Furniture principal dimensions MUST be plausible against `docs/references/Alternativ1.JPG` / `Alternativ2.JPG` within ±1% on the dimensions recorded in the defaults; per-instance fine detail (toilet contour, faucet shape) is exempt.
- **FR-015**: New furniture bodies MUST be exposed on the `build_interior` return aggregate (or on the per-compartment wrapper) so callers can access them.
- **FR-016**: The public API change MUST be additive only; `storebro.__version__` is bumped PATCH (1.0.5 → 1.0.6) and kept in sync with `pyproject.toml`.
- **FR-017**: The transparency/material/color of furniture is OUT OF SCOPE (spec 015); spec 012 delivers geometry only.

### Key Entities

- **Berth**: A sleeping platform (base) with one or more cushions on top, in a `forward_cabin`. Attributes: base height, cushion thickness, inset from compartment walls.
- **Cushion**: A thin solid on top of a berth base.
- **Galley Counter**: A worktop solid with a sink recess and a stove recess cut into its top. Attributes: counter height, thickness, sink/stove recess length/width/depth and positions.
- **Head Fittings**: A toilet body and a sink body in a `head`. Attributes: bowl/pedestal dimensions, sink dimensions, positions.
- **Salon Furniture**: A settee/seating body and a table body in a `salon`. Attributes: seat height/depth, table height/dimensions.
- **Bulkhead**: A thin partition body between adjacent compartments.
- **Furniture Composite**: The new optional parameter aggregate bundling the per-type furniture parameters.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A default `build_interior(layout="Alternativ1")` produces furnished compartments (berth+cushion, galley counter with recesses, head toilet+sink, salon seating+table) plus bulkheads, with zero new errors.
- **SC-002**: The galley counter remains a single closed manifold after the sink/stove recesses (solid count = 1, valid), and STL export of the model still succeeds.
- **SC-003**: Every new furniture dataclass rejects out-of-range / oversized / too-deep input with a clear error naming the field, verified by unit tests covering each branch.
- **SC-004**: Two consecutive builds with identical layout + parameters produce byte-identical exported geometry.
- **SC-005**: A mid-build failure in any furniture piece leaves the document in its exact pre-call state (rollback verified).
- **SC-006**: Building Alternativ2 produces the same level of furniture detail as Alternativ1; building Alternativ3/4/5 leaves them boxy (gate verified).
- **SC-007**: Existing `build_interior` callers continue to succeed; Alt1/Alt2 now receive furniture automatically.
- **SC-008**: `uv run pytest`, `ruff check`, and `mypy --strict` all pass; the model opens and visually verifies in FreeCAD against the reference images.

## Assumptions

- **Furniture fidelity**: "basic" furniture — recognizable primitive shapes (berth = box base + cushion box; toilet = pedestal box + bowl; sink = recessed box; counter = box with recesses; settee = L/box; table = top + pedestal). Contoured castings, upholstery seams, faucet hardware are out of scope.
- **Furniture construction**: PartDesign Pads (solids) + Pockets (galley recesses), matching specs 008/010/011. The existing compartment placeholder box is replaced by furniture bodies; a thin bulkhead represents the compartment boundary.
- **Galley cutouts**: blind recesses into the counter top (manifold-safe), consistent with the spec 011 porthole/window decision.
- **Gating**: detailed furniture applies only to Alternativ1/Alternativ2 in this spec (by layout name); the type-keyed builders are generic so spec 013 enables Alt3-5.
- **Materials/colors**: out of scope — spec 015 (render-attributes).
- **Reference source**: `docs/references/Alternativ1.JPG`, `Alternativ2.JPG`; estimate-grade defaults where ambiguous, refinable in later PATCH bumps.
- **Behavior change**: existing interior tests that assert exactly N boxy compartment bodies for Alt1/Alt2 will need updating; this is an expected additive change.
- **Dependency**: spec 004 (interior module + fixtures) provides the compartment specs the furniture is keyed to.
