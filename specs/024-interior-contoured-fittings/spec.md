# Feature Specification: Interior Contoured Fittings

**Feature Branch**: `024-interior-contoured-fittings`

**Created**: 2026-06-03

**Status**: Draft

**Input**: User description: "Replace the boxy interior fittings with contoured shapes: cushioned settee contours, berth upholstery seams, contoured toilet + faucet, galley appliance fascia, and curved bulkheads. Cosmetic-grade refinement of specs 012/013."

## Clarifications

### Session 2026-06-03

- Q: How are the contours built, given specs 012/013 use `Part.makeBox`? → A: With `Part` B-rep operations on the existing Part::Feature furniture bodies — `makeFillet` to round box edges, `makeCylinder` + `fuse` for the toilet bowl/faucet, `cut` for a rounded doorway — matching the interior module's Part-workbench idiom (NOT PartDesign; the interior is Part::Feature B-rep by spec 004 precedent). A spike confirmed `makeFillet` on a box is byte-reproducible across builds (unlike the spec 022 arc loft), so it is safe for constitution II.
- Q: What does "berth upholstery seams" mean concretely? → A: The single cushion slab is split into `cushion_segments` sub-cushion boxes (each with rounded top edges) separated by thin seam gaps, so the berth reads as a segmented mattress.
- Q: Fabric micro-detail on cushions? → A: **Yes (user promoted from deferred).** Each cushion gets **tufting buttons** (a grid of shallow cut-sphere dimples on the top face), a **piping welt** (a thin raised rounded strip around the cushion top perimeter), and a few **fold creases** (shallow cut grooves). All are analytic Part ops (`makeSphere`/`makeCylinder`/`cut`/`fuse`) and so byte-reproducible; each carries the manifold-or-fallback gate.
- Q: What is the "galley appliance fascia"? → A: A thin contoured (rounded-edge) fascia panel added on the counter's forward face, plus rounded top edges on the worktop — the appliance-front reading.
- Q: What makes a bulkhead "curved"? → A: The bulkhead's vertical edges are filleted (rounded corners) and, when the compartment is tall enough, a rounded-top doorway opening is cut through it.
- Q: Are these contours on by default, and reproducible? → A: On by default (existing callers get contoured fittings automatically), behind a single `contoured` flag per furniture group so they can be turned off (reverting to the spec 012/013 boxes). All contour ops are deterministic; a manifold guard (`Solids == 1 && isValid()` per fillet/cut result, with a fallback to the un-contoured box) protects STL.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cushioned settee + berth contours (Priority: P1)

A restorer wants the berth and settee cushions to read as upholstery — rounded edges and segmented seams — not flat slabs.

**Why this priority**: Cushions are the largest, most-seen interior surfaces; rounding them is the highest perceptual return.

**Independent Test**: Build a furnished layout; berth cushions are segmented sub-cushions with rounded edges and visible seam gaps; the settee seat has rounded edges; every piece is a valid solid.

**Acceptance Scenarios**:

1. **Given** a furnished forward cabin, **When** built, **Then** the berth cushion is split into `cushion_segments` rounded sub-cushions separated by seam gaps, each a single valid solid.
2. **Given** a furnished salon, **When** built, **Then** the settee seat has rounded edges and is a single valid solid.
3. **Given** `contoured=False`, **When** built, **Then** the spec 012/013 plain boxes are produced (back-compat).

---

### User Story 2 - Contoured toilet + faucet (Priority: P2)

The head should read as a contoured toilet with a bowl and a faucet on the sink, not two boxes.

**Why this priority**: The head fittings are recognizable items; contouring them lifts close-up fidelity.

**Independent Test**: Build a furnished head; the toilet has a rounded pedestal + a bowl, and the sink has a faucet; each fitting is a valid solid.

**Acceptance Scenarios**:

1. **Given** a furnished head, **When** built, **Then** the toilet is a rounded pedestal fused with a bowl (single valid solid) and a faucet (stem + spout) sits on the sink.
2. **Given** `contoured=False`, **When** built, **Then** the spec 012 toilet + sink boxes are produced.

---

### User Story 3 - Galley appliance fascia (Priority: P3)

The galley counter should have an appliance fascia and rounded worktop edges.

**Why this priority**: Adds galley realism; the counter already has sink/stove recesses from spec 012.

**Independent Test**: Build a furnished galley; the worktop has rounded front-top edges and a fascia panel on the forward face; the counter stays a single valid solid (the spec 012 manifold guard).

**Acceptance Scenarios**:

1. **Given** a furnished galley, **When** built, **Then** the worktop has rounded edges and a fascia panel, and the counter is a single valid solid.
2. **Given** `contoured=False`, **When** built, **Then** the spec 012 worktop is produced.

---

### User Story 4 - Curved bulkheads (Priority: P3)

Bulkheads should have rounded corners and, where headroom allows, a rounded-top doorway.

**Why this priority**: Bulkheads frame every compartment; rounding them softens the boxy reading.

**Independent Test**: Build a furnished layout; each bulkhead has filleted vertical edges and, when tall enough, a rounded-top doorway cut; each bulkhead is a single valid solid.

**Acceptance Scenarios**:

1. **Given** a furnished compartment, **When** built, **Then** its bulkhead has rounded vertical edges and remains a single valid solid.
2. **Given** a sufficiently tall bulkhead, **When** built, **Then** a rounded-top doorway opening is cut through it, and it remains a single valid solid.
3. **Given** `contoured=False`, **When** built, **Then** the spec 012 plain bulkhead is produced.

---

### Edge Cases

- What happens when a fillet radius exceeds half a box dimension? → the radius is clamped to a safe fraction of the smallest box dimension before filleting (no degenerate fillet).
- What happens when a contour op (`makeFillet`/`fuse`/`cut`) fails or yields a non-single-solid? → a manifold-or-fallback gate reverts that piece to its spec 012/013 box (deterministic — depends only on geometry).
- What if the doorway would be wider than the bulkhead or taller than the compartment? → the doorway is skipped (the bulkhead is still rounded), no error.
- What happens to STL manifold-ness? → every contoured piece asserts `Solids == 1 && isValid()`; any piece that would break it falls back to the box.
- What about reproducibility? → all contour ops are deterministic (spiked: filleted-box volume is byte-identical across builds), so the furniture-determinism tests stay green.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Berth cushions MUST be split into `cushion_segments` rounded sub-cushions separated by thin seam gaps (upholstery seams); each sub-cushion a single valid solid.
- **FR-002**: The settee seat MUST have rounded (filleted) edges; a single valid solid.
- **FR-002a** (fabric detail): Each cushion (berth sub-cushions + settee seat) MUST gain tufting **buttons** (a grid of shallow cut-sphere dimples on the top face), a **piping welt** (a thin raised rounded strip around the top perimeter), and **fold creases** (shallow cut grooves), all behind the `contoured` flag and each carrying the manifold-or-fallback gate. All ops are analytic and byte-reproducible.
- **FR-003**: The toilet MUST be a rounded pedestal fused with a bowl (single valid solid); the sink MUST gain a faucet (stem + spout).
- **FR-004**: The galley worktop MUST gain rounded front-top edges and a forward fascia panel, while staying a single valid solid (the spec 012 manifold guard).
- **FR-005**: Bulkheads MUST have filleted vertical edges and, where the compartment is tall enough, a rounded-top doorway opening; each bulkhead a single valid solid.
- **FR-006**: All contouring MUST use `Part` B-rep ops (`makeFillet`/`makeCylinder`/`fuse`/`cut`) on the existing Part::Feature furniture, matching the interior idiom; no PartDesign, no raw mesh.
- **FR-007** (FALLBACK): Every contour MUST have a manifold-or-fallback gate — if `makeFillet`/`fuse`/`cut` fails or does not yield a single valid solid, revert that piece to its spec 012/013 box. The gate is deterministic.
- **FR-008**: Contouring MUST be on by default, behind a `contoured` flag per furniture group; `contoured=False` reproduces the spec 012/013 boxes exactly (back-compat).
- **FR-009**: All new shape-controlling fields (fillet radii, `cushion_segments`, seam gap, fascia thickness, doorway dims) MUST be added additively + defaulted + validated to the furniture parameter dataclasses.
- **FR-010**: No public API may be removed; all spec 012/013 furniture types, fields, and `build_interior` keep working unchanged.
- **FR-011** (REPRODUCIBLE): Contour ops MUST be byte-reproducible (constitution II); the furniture-determinism tests MUST stay green.

### Key Entities

- **BerthParameters**: gains `contoured`, `cushion_segments`, `seam_gap`, `cushion_fillet`, and fabric controls (`buttons_per_row`, `button_rows`, `button_radius`, `piping`, `piping_radius`, `fold_creases`).
- **SalonParameters**: gains `contoured`, `seat_fillet`, and the same fabric controls.
- **HeadParameters**: gains `contoured`, `bowl_radius`, `faucet` controls, `toilet_fillet`.
- **GalleyParameters**: gains `contoured`, `fascia_thickness`, `edge_fillet`.
- **BulkheadParameters**: gains `contoured`, `corner_fillet`, doorway controls (`doorway`, width, height).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every contoured furniture piece in a default furnished build is a single valid solid (`isValid()`), or has deterministically fallen back to its box.
- **SC-002**: STL export of a furnished interior succeeds and is watertight.
- **SC-003**: `contoured=False` reproduces the spec 012/013 furniture byte-identically.
- **SC-004**: The furniture-determinism tests stay green (contours are reproducible).
- **SC-005**: Every spec 012/013 interior test continues to pass (100% back-compat).

## Assumptions

- FreeCAD 1.1.1; `Part.makeFillet`/`makeCylinder`/`fuse`/`cut` behave as spiked.
- "Contoured" means a recognizable rounded/segmented reading at model-viewing distance, within constitution principle IV; fine upholstery detail is visual-only.
- The interior is Part::Feature B-rep (spec 004 precedent); Part-workbench ops are constitution-III-idiomatic here.
- Light track: cosmetic refinement of existing furniture, single synchronous build, no new state machine — `/tla` is expected to be skipped.
