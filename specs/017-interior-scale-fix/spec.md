# Feature Specification: Interior Scale Fix

**Feature Branch**: `017-interior-scale-fix`

**Created**: 2026-06-02

**Status**: Draft

**Input**: User description: "Fix the interior module's meter-magnitude geometry-construction convention so interior compartments + spec 012/013 furniture build at true mm scale inside the hull, instead of ~1000× too small."

## Overview

The interior module builds its compartment boxes and furniture pieces by passing layout values (authored in metres) straight into FreeCAD's geometry calls. FreeCAD's internal length unit is millimetres, so a 2.4 m cabin currently materialises as a 2.4 mm box — roughly 1000× smaller than the hull, which correctly converts every coordinate from metres to millimetres before building. The result is an interior that is geometrically valid but microscopic relative to the boat it is supposed to sit inside.

This is a pure scale correction. No new compartment types, no new furniture, no new layout-file fields, no new public functions or parameters, and no change to the YAML authoring units. The only behaviour that changes is the **magnitude of the geometry the module emits**: after the fix the interior shares one coordinate system with the hull and nests inside it at true scale.

The defect was discovered during the spec 012 formal-verification pass (register history entry 2026-05-29, GAP-1) and tracked as this spec.

## Clarifications

### Session 2026-06-02

No critical ambiguities detected worth formal clarification. The specification is a spec-only-track scale correction with a fully bounded scope: functional behaviour, data model (no new entities), non-functional attributes (determinism, ±1% tolerance), edge cases (validation stays in metre-space, no double-scaling of display properties, custom-layout placeholders, missing compartment types), and completion signals (six measurable success criteria plus an explicit regression test) are all resolved by the requirements as written. No question would have materially changed architecture, task decomposition, or test design.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Interior nests inside the hull at true scale (Priority: P1)

A user builds a complete boat (hull → deck → interior) for one of the canonical layouts and opens the resulting document in FreeCAD. The compartments and their furniture appear at the correct real-world size, fitting inside the hull exactly where the layout places them — not collapsed into a millimetre-sized speck near the origin.

**Why this priority**: This is the entire purpose of the spec. Without it, every interior the library produces is unusable for visual inspection, export, or downstream modelling because it is three orders of magnitude too small to relate to the hull.

**Independent Test**: Build any canonical layout on a hull and assert that a known compartment's geometry bounding box matches the layout's stated metre dimensions expressed in millimetres (e.g. a 2.4 m cabin yields a bounding-box length of ~2400 mm, not ~2.4 mm), and that the compartment's footprint falls within the hull's bounding box.

**Acceptance Scenarios**:

1. **Given** the Alternativ1 layout with a 2.4 m × 2.0 m × 1.2 m forward cabin, **When** the interior is built, **Then** that compartment's shape bounding box measures approximately 2400 mm × 2000 mm × 1200 mm.
2. **Given** a hull built at millimetre scale and an interior built on it, **When** both are present in the same document, **Then** the interior's combined bounding box lies inside the hull's bounding box (interior nests within the hull).
3. **Given** the displayed `Length` / `Width` / `Height` properties of a compartment (which already read in millimetres), **When** the fix is applied, **Then** those displayed values equal the actual geometry dimensions (the property and the shape agree).

---

### User Story 2 - Furniture sits at true scale within its compartment (Priority: P1)

For the canonical furnished layouts (Alternativ1–5), the berths, galley counters, heads fittings, salon seating/tables, and bulkheads appear at realistic sizes inside their compartments after the scale fix — a berth is roughly knee-high, a galley counter roughly waist-high — and every furniture piece stays within the bounds of the compartment that contains it.

**Why this priority**: The furniture builders were tuned to compensate for the broken compartment scale. Fixing the compartments without fixing the furniture in the same change would leave the furniture 1000× off in the other direction. Both must move together, so this is equally P1.

**Independent Test**: Build a furnished layout and assert that each furniture piece's bounding box lies within its compartment's true-scale (millimetre) envelope, and that representative furniture heights match their stated real-world sizes (e.g. a galley counter ~900 mm tall).

**Acceptance Scenarios**:

1. **Given** a furnished forward cabin, **When** the interior is built, **Then** the berth and cushion bounding boxes lie within the compartment's millimetre-scale envelope.
2. **Given** a furnished galley, **When** the interior is built, **Then** the counter's top sits at approximately its configured height (~900 mm) above the compartment floor and the worktop remains a single closed solid.
3. **Given** any furnished canonical layout, **When** the interior is built, **Then** no furniture piece extends outside the bounding box of the compartment it belongs to.

---

### User Story 3 - Existing guarantees survive the scale change (Priority: P2)

The behaviours the interior module already guarantees — input validation in metre units, compartment-overlap rejection, envelope-overflow rejection, the galley-counter manifold guard, rollback on construction failure, and byte-identical reproducibility for identical inputs — all continue to hold after the scale fix.

**Why this priority**: A scale correction must not silently regress any of the module's existing correctness guarantees. It is P2 because it is a non-regression requirement layered on top of the P1 scale change rather than new value in its own right.

**Independent Test**: Run the existing interior validation, overlap, manifold, and rollback test cases unchanged (they operate in metre-space or are scale-agnostic) and confirm they still pass; run the determinism check and confirm identical inputs still produce identical geometry.

**Acceptance Scenarios**:

1. **Given** a layout whose compartments overlap, **When** the interior is built, **Then** it is rejected with the same validation error as before the fix.
2. **Given** a layout that fits the hull envelope, **When** it is built twice with identical inputs, **Then** both builds produce identical geometry.
3. **Given** a galley with recess cutouts, **When** the counter is built, **Then** it remains a single valid solid (the manifold guard still holds at the corrected scale).

---

### Edge Cases

- **Validation stays in metre-space**: envelope-overflow, overlap, and furniture-fit validators compare layout values (metres) against hull parameters (metres). These comparisons must remain in metres; the scale conversion happens only when geometry is emitted, so validation outcomes are unchanged by this fix.
- **GUI display properties must not double-scale**: the compartment `Length` / `Width` / `Height` properties already multiply layout metres by 1000 for display. After the fix the geometry is also in millimetres — the display values must continue to equal the geometry, not be multiplied a second time.
- **Custom (non-canonical) layouts**: layouts supplied as a filesystem path keep their boxy (unfurnished) placeholders. Those boxes must scale to millimetres exactly like the canonical compartment boxes.
- **Alternativ5 has no galley**: layouts missing a compartment type simply build no furniture of that type; the scale fix must not introduce any dependency on a compartment type being present.
- **Determinism**: the conversion must be a single named constant applied uniformly, introducing no per-build variation, so reproducibility is preserved.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The interior module MUST emit compartment geometry at millimetre scale — layout dimensions and positions authored in metres MUST be converted to millimetres at the point geometry is constructed, consistent with how the hull module converts its metre parameters.
- **FR-002**: The interior module MUST emit furniture geometry (berths, cushions, galley counters and their recesses, heads fittings, salon seating and tables, bulkheads) at millimetre scale, consistent with the corrected compartment scale, so furniture and compartments share one coordinate system.
- **FR-003**: Furniture dimensions already expressed in millimetres (the furniture parameter values) MUST be used at their stated millimetre magnitude after the fix, rather than being shrunk to metre magnitude to match the previously-broken boxes.
- **FR-004**: Any fixed real-world furniture measurements embedded in the builders (insets, fitting sizes, table and pedestal sizes, etc.) MUST be expressed at millimetre scale so they remain at their intended real-world size relative to the corrected compartments.
- **FR-005**: The metre→millimetre conversion MUST be expressed through a single named constant (mirroring the hull module's existing constant) rather than scattered literal multipliers, to keep the convention explicit and reproducible.
- **FR-006**: The YAML layout-authoring units MUST remain metres — no layout fixture or schema change is permitted by this spec. Conversion to millimetres happens only inside the module's geometry construction.
- **FR-007**: Input validation (envelope overflow, compartment overlap, furniture-fit) MUST continue to operate in metre-space and produce the same accept/reject outcomes as before the fix.
- **FR-008**: The compartment GUI display properties (`Length`, `Width`, `Height`) MUST equal the actual millimetre geometry after the fix and MUST NOT be scaled a second time.
- **FR-009**: All existing correctness guarantees of the module — galley-counter manifold (single closed solid), rollback on construction failure, and byte-identical reproducibility for identical inputs — MUST continue to hold at the corrected scale.
- **FR-010**: The public API surface (function signatures, parameter dataclasses, exception classes, return types) MUST be unchanged by this fix; the change is internal to geometry construction.
- **FR-011**: Existing scale-sensitive tests MUST be updated so their absolute-coordinate assertions are expressed at millimetre scale; scale-agnostic assertions (positive-volume, relative-volume comparisons) remain unchanged.
- **FR-012**: A regression test MUST assert that a known compartment (the Alternativ1 forward cabin, 2.4 m long) produces geometry whose bounding-box length is approximately 2400 mm, guarding explicitly against a relapse to the metre-magnitude defect.

### Key Entities

This feature introduces no new entities. It corrects the geometric scale of the existing entities (compartments and furniture pieces) the interior module already produces.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A compartment authored as 2.4 m long produces geometry whose bounding-box length is within ±1% of 2400 mm (previously ~2.4 mm).
- **SC-002**: For every furnished canonical layout, 100% of furniture pieces have bounding boxes contained within their compartment's millimetre-scale envelope.
- **SC-003**: The interior's combined X-Y footprint is contained within the hull's bounding box, and its floor sits above the keel, when both are built in the same document (the interior legitimately rises above the bare hull sheer into the cabin-trunk/superstructure headroom that the envelope validator already permits, so the Z-axis is bounded below by the keel rather than above by the hull sheer).
- **SC-004**: 100% of the existing interior validation, overlap, manifold, and rollback test cases continue to pass without behavioural change.
- **SC-005**: Building the same layout twice with identical inputs produces byte-identical geometry (reproducibility preserved).
- **SC-006**: No change to the public API: every existing caller and every existing import continues to work without modification.

## Assumptions

- The hull module's metre→millimetre convention (`_MM_PER_M = 1000.0`, applied at geometry construction) is the canonical, correct reference; the interior module is being brought into line with it.
- Layout fixtures are authored in metres and remain so; no consumer relies on the interior geometry being at metre magnitude (the defect makes that geometry unusable, so there is nothing to preserve).
- The displayed compartment dimension properties were always intended to read in millimetres; the fix makes the geometry agree with them rather than the other way around.
- FreeCAD geometry tests run on a FreeCAD 1.1+ host; where FreeCAD is unavailable on the implementation host, the unit-only suite plus a documented pending geometry-tier run is acceptable per the project's missing-FreeCAD fallback.
- This is a spec-only-track change (a fix introducing no new entities or state transitions), so no formal Allium specification or TLA+ model is produced; the scale invariant is expressed as a test (FR-012) rather than a formal invariant.
