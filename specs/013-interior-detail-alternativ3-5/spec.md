# Feature Specification: Interior Detail — Alternativ3, 4 & 5

**Feature Branch**: `013-interior-detail-alternativ3-5`

**Created**: 2026-05-29

**Status**: Draft

**Input**: User description: "Same furniture treatment for Alternativ3, 4, 5 as spec 012 did for Alt1/Alt2. Reuse the spec 012 type-keyed helpers — extend the gate. Alt5 has no galley compartment."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Furnished Alternativ3 & 4 (Priority: P1)

A scale modeler builds the Alternativ3 or Alternativ4 interior and sees the same furniture detail (berth+cushion, galley counter with recesses, toilet+sink, settee+table, bulkheads) that Alternativ1/2 already produce — every canonical four-compartment layout is now furnished, not boxy.

**Why this priority**: Alt3 and Alt4 share the four-compartment structure with Alt1/2, so they exercise the existing spec 012 builders directly via a gate extension. This is the bulk of the spec.

**Independent Test**: Build the Alternativ3 and Alternativ4 interiors; confirm every compartment is furnished by the spec 012 type-keyed builders and fits within its (different) compartment envelope.

**Acceptance Scenarios**:

1. **Given** the Alternativ3 layout, **When** `build_interior` runs, **Then** each compartment is furnished (forward_cabin→berth+cushion, galley→counter with recesses, head→toilet+sink, salon→settee+table) plus a bulkhead, all within the compartment envelopes.
2. **Given** the Alternativ4 layout (a smaller galley than Alt1/2), **When** `build_interior` runs, **Then** the galley counter + recesses fit within the smaller galley envelope and the counter stays a single solid.
3. **Given** default furniture parameters, **When** Alt3/Alt4 build, **Then** no envelope-overflow error occurs (defaults fit every Alt3/Alt4 compartment).

---

### User Story 2 - Alternativ5 with no galley (Priority: P2)

The modeler builds Alternativ5 (a day-cruiser variant with an integrated galley and no separate galley compartment) and sees the forward cabin, head, and salon furnished — with no galley furniture, and no error from the missing compartment type.

**Why this priority**: Alt5 is the edge case that confirms the per-compartment dispatch degrades gracefully when a layout omits a compartment type. It depends only on the gate extension being type-driven, not layout-shape-driven.

**Independent Test**: Build the Alternativ5 interior; confirm forward_cabin, head, and salon are furnished, no galley furniture is produced, and the build succeeds.

**Acceptance Scenarios**:

1. **Given** the Alternativ5 layout (3 compartments, no galley), **When** `build_interior` runs, **Then** the forward cabin, head, and salon are furnished and no galley counter is built, with no error.
2. **Given** Alternativ5, **When** `build_interior` runs, **Then** every present compartment carries a bulkhead.

---

### Edge Cases

- **Missing compartment type** (Alt5 has no galley): the per-type dispatch builds furniture only for the compartment types present; an absent type produces no furniture and no error.
- **Smaller compartments** (Alt4 galley): default furniture is sized relative to the compartment dimensions, so it fits the smaller envelopes; if a caller's override is too large for a specific compartment, it is rejected by the existing envelope guard.
- **Reproducibility / rollback / manifold**: identical to spec 012 — these properties are inherited from the shared builders and must continue to hold for the new layouts.
- **Gate completeness**: after this spec, all five canonical layouts are furnished; the spec 012 "Alt3-5 stay boxy" behavior is intentionally replaced.

## Clarifications

### Session 2026-05-29

- Q: After enabling all five canonical layouts, should furniture also apply to CUSTOM (non-canonical YAML path) layouts? → A: No — furniture is gated to the five canonical layout names (Alternativ1–5). Custom layouts keep boxy placeholders (their compartment dimensions are unconstrained, so default furniture may not fit; a custom-layout furniture mode is a possible future spec). The gate widens from `{Alt1, Alt2}` to all five canonical names.
- Q: What happens to spec 012's `test_interior_gate.py` (which asserted Alt3/4/5 stay boxy)? → A: It is repurposed — the assertion flips to "all five canonical layouts are furnished", and a new assertion confirms a custom (non-canonical) layout stays boxy. The old "Alt3-5 boxy" expectation is intentionally removed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `build_interior` MUST furnish the Alternativ3, Alternativ4, and Alternativ5 layouts using the same type-keyed furniture builders introduced in spec 012 (berth, galley counter, head fittings, salon furniture, bulkheads). The furnished-layout gate widens from `{Alternativ1, Alternativ2}` to all five canonical layout names; custom (non-canonical) YAML layouts keep boxy placeholders.
- **FR-002**: The per-compartment-type dispatch MUST build furniture only for the compartment types present in a layout; a layout missing a type (Alternativ5 has no galley) MUST build the remaining furniture without error.
- **FR-003**: Default furniture parameters MUST fit within every Alternativ3/4/5 compartment envelope (no envelope-overflow error on a default build); furniture is sized relative to the compartment dimensions.
- **FR-004**: The galley counter MUST remain a single closed manifold for the Alternativ3/4 (smaller) galleys, so STL export is unaffected (inherited spec 012 guard).
- **FR-005**: All spec 012 properties — reproducibility, rollback on partial failure, FreeCAD-idiomatic Part::Feature B-rep construction, validation — MUST continue to hold for the new layouts (the builders are shared, unchanged).
- **FR-006**: No new public parameter types are required; callers MAY override furniture for Alt3/4/5 via the existing `parameters_furniture` argument. The change is a gate extension, additive and behavior-extending.
- **FR-007**: The version MUST be bumped PATCH (1.0.6 → 1.0.7) and `storebro.__version__` kept in sync with `pyproject.toml`.
- **FR-008**: The interior-to-hull scale issue (spec 017) is NOT addressed here; Alt3/4/5 furniture is built at the same convention as Alt1/2 for consistency.
- **FR-009**: Furniture transparency/material/color remains OUT OF SCOPE (spec 015).

### Key Entities

No new entities. This spec reuses the spec 012 furniture entities (Berth, Cushion, Galley Counter, Head Fittings, Salon Furniture, Bulkhead) and the `FurnitureParameters` composite, extending only the set of layouts they apply to.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A default `build_interior(layout="Alternativ3")` and `build_interior(layout="Alternativ4")` furnish all four compartments with zero errors.
- **SC-002**: A default `build_interior(layout="Alternativ5")` furnishes the three present compartments (forward cabin, head, salon), builds no galley furniture, and raises no error.
- **SC-003**: The Alternativ3/4 galley counter remains a single closed manifold (solid count = 1, valid).
- **SC-004**: Two consecutive builds of any of Alt3/4/5 with identical parameters produce byte-identical geometry.
- **SC-005**: A mid-build failure on Alt3/4/5 rolls the document back to its pre-call state.
- **SC-006**: All five canonical layouts are furnished after this spec; none remain boxy by default.
- **SC-007**: `uv run pytest`, `ruff check`, and `mypy --strict` all pass; the model opens and visually verifies in FreeCAD against the reference images for Alt3/4/5.

## Assumptions

- **Reuse over rebuild**: spec 013 changes the layout gate and adds per-layout coverage; the furniture builders themselves are unchanged from spec 012.
- **Default fit**: the spec 012 default furniture dimensions, sized relative to compartment dimensions, fit every Alt3/4/5 compartment (verified against the fixtures during planning).
- **Alt5 integrated galley**: Alt5's salon is described as containing an integrated galley; modeling that integrated galley as part of the salon furniture is out of scope — Alt5 simply has no galley compartment and therefore no galley counter.
- **Scale**: the interior-to-hull scale fix is deferred to spec 017; Alt3/4/5 furniture uses the same convention as Alt1/2.
- **Materials/colors**: out of scope — spec 015.
- **Behavior change**: the spec 012 `test_interior_gate.py` test (which asserted Alt3/4/5 stay boxy) will be updated/replaced — that gate is intentionally removed here.
