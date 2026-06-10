# Feature Specification: Interior Layout Expansion

**Feature Branch**: `025-interior-layout-expansion`

**Created**: 2026-06-10

**Status**: Draft

**Input**: User description: "Widen the interior model: Alternativ5 integrated galley-in-salon, custom-layout furniture mode, additional compartment types (aft cabin, dinette, engine room, wet locker), and asymmetric layouts (drop the v1.0 symmetry constraint)."

## User Scenarios & Testing *(mandatory)*

A library consumer (restorer, scale modeler, FreeCAD scripter) drives the interior model from a YAML layout. Today they get furnished compartments only for the canonical Alternativ1–5 (and DS) layouts, only five compartment types, every compartment forced onto the centreline, and the Alternativ5 "integrated galley" reads as a bare salon. This feature widens the model so consumers can describe richer boats — their own custom layouts get real furniture, more compartment kinds exist, compartments can sit off-centre, and the canonical Alternativ5 finally shows its galley. Existing canonical layouts keep building exactly as before (Alternativ5 excepted, which gains its galley), and the public API is unchanged.

### User Story 1 - Alternativ5 integrated galley-in-salon (Priority: P1)

The canonical Alternativ5 layout has one large compartment described as a combined salon with an integrated galley, but it is furnished only with a settee and table — no galley. The consumer wants the Alternativ5 salon to also carry galley fittings (a counter with sink and stove recesses) so the day-cruiser layout reads correctly.

**Why this priority**: It is the one canonical-layout correctness gap (Alternativ5 ships visibly wrong today), it is self-contained, and it exercises the "two furniture sets in one compartment" mechanism the other stories also benefit from.

**Independent Test**: Build the Alternativ5 layout; confirm its salon-galley compartment contains BOTH settee/table furniture AND a galley counter with sink + stove recesses, every piece is a single valid solid, and the other four canonical layouts are byte-identical to before.

**Acceptance Scenarios**:

1. **Given** the Alternativ5 layout, **When** the interior is built, **Then** the integrated salon-galley compartment carries settee + table furniture AND a galley counter with blind sink + stove recesses, all fused into the compartment's compound.
2. **Given** the Alternativ5 galley counter, **When** its solid count is checked, **Then** it is a single valid solid (the spec 012 galley manifold guard holds).
3. **Given** Alternativ1–4 layouts, **When** built, **Then** their geometry is byte-identical to the spec 013/024 output (only Alternativ5 changed).

---

### User Story 2 - Custom-layout furniture mode (Priority: P1)

Today only the canonical/bundled layouts get furniture; a consumer's own (non-canonical) YAML layout gets plain placeholder boxes. The consumer wants their custom layout's compartments to receive the same type-keyed furniture the canonical layouts get — a custom compartment with `type: galley` gets a galley, `type: forward_cabin` gets a berth, and so on.

**Why this priority**: This is the single biggest capability unlock — it lets consumers build any boat, not just the shipped five — and it reuses the existing type-keyed furniture builders directly.

**Independent Test**: Build a small custom (non-canonical) YAML layout with a forward_cabin + galley + head; confirm each compartment is furnished with the matching furniture (not a bare box), every piece is a single valid solid, and `is_furnished` is true.

**Acceptance Scenarios**:

1. **Given** a custom YAML layout with `type: galley`, **When** the interior is built, **Then** that compartment carries a galley counter with sink + stove recesses, not a placeholder box.
2. **Given** a custom layout with several typed compartments, **When** built, **Then** every compartment of a furnishable type is furnished (`is_furnished == true`) and its body is a compound of the furniture pieces.
3. **Given** a custom layout, **When** built twice with identical input, **Then** the two builds are byte-identical.

---

### User Story 3 - Additional compartment types (Priority: P2)

The model recognizes only five compartment types. The consumer wants more kinds so a layout can describe a real boat: an aft cabin, a dinette, an engine room, and a wet locker. Each new type produces furniture appropriate to it.

**Why this priority**: Broadens what a layout can express, but depends on the type-keyed dispatch the first two stories establish, so it follows them.

**Independent Test**: Build a layout containing one compartment of each new type; confirm each is accepted (no "unknown type" error), each is furnished with its appropriate fitting, every piece is a single valid solid, and an out-of-envelope fitting is rejected.

**Acceptance Scenarios**:

1. **Given** a layout with a compartment of type `aft_cabin`, `dinette`, `engine_room`, or `wet_locker`, **When** built, **Then** the type is accepted and the compartment is furnished with the fitting appropriate to that type.
2. **Given** a new-type fitting taller than its compartment, **When** built, **Then** a parameter error is raised before any geometry is constructed (the furniture-fit envelope guard applies to the new types).
3. **Given** a new-type compartment, **When** its furniture is inspected, **Then** every piece is a single valid solid.

---

### User Story 4 - Asymmetric layouts (Priority: P2)

The model forces every compartment onto the centreline (`y = 0`). The consumer wants to place compartments off-centre — a head to port, a locker to starboard — so the layout can be asymmetric, as real boats often are.

**Why this priority**: A distinct capability that drops a v1.0 constraint; valuable but independent of the furniture stories, so it can land in either order after them.

**Independent Test**: Build a layout with a compartment at `y != 0`; confirm it is accepted (no centreline error), the compartment and its furniture are positioned off-centre, the compartment stays within the hull half-beam envelope, and a compartment pushed past the half-beam is rejected.

**Acceptance Scenarios**:

1. **Given** a compartment with `position.y != 0`, **When** built, **Then** it is accepted (the v1.0 centreline constraint no longer applies) and the compartment + furniture are offset transversely by that amount.
2. **Given** a compartment whose transverse extent would exceed the hull half-beam at its station, **When** built, **Then** a parameter error is raised before geometry construction.
3. **Given** an asymmetric layout, **When** built twice, **Then** the two builds are byte-identical.

---

### Edge Cases

- **Backward compatibility (canonical layouts)**: Alternativ1–4 and the DS layout MUST build byte-identically to their spec 013/024/023 output; only Alternativ5 changes (it gains its galley). With the symmetry constraint dropped, every existing `y = 0` layout still validates and builds unchanged.
- **Reproducibility**: every new construction (Alt5 galley-in-salon, new-type fittings, off-centre placement) MUST be byte-reproducible across identical builds (constitution II), consistent with the spec 024 analytic-primitive reproducibility.
- **Manifold**: every furniture piece stays a single valid solid; the spec 012 galley counter manifold guard (`Solids == 1`) is preserved, including for the Alt5 integrated galley.
- **Envelope**: furniture-fit and hull-envelope validation apply to the new types and to off-centre placements; an out-of-envelope fitting or a compartment past the half-beam is rejected before geometry is built.
- **Overlap**: the existing no-overlap validation still applies; asymmetric placement must not let two compartments intersect.
- **Engine room**: an engine_room compartment is furnished with a representative engine-block-like fitting (or kept structural); it must not collide with the propulsion module's engine bodies if both are present (they are separate modules — the interior fitting is representative, not the propulsion engine).
- **Unknown type / malformed YAML**: an unknown compartment type or malformed asymmetric position still raises a clear parameter error (the existing validation idiom).

## Clarifications

### Session 2026-06-10

- Q: How is the Alternativ5 integrated galley-in-salon expressed? → A: A new `salon_galley` compartment type that furnishes BOTH the salon set (settee + table) AND a galley counter (sink + stove recesses) in one compartment. The Alternativ5 fixture's combined compartment changes from `type: salon` to `type: salon_galley`; the `salon` type stays pure (settee + table only).
- Q: How does the custom-layout furniture gate widen? → A: Drop the layout-name gate entirely — furniture is dispatched by compartment TYPE for every layout (canonical, DS, and custom alike). Any compartment whose type is furnishable gets its furniture; only genuinely non-furnishable types keep a structural box. Canonical layouts are unaffected (they already furnish by type).
- Q: What fitting does an `engine_room` compartment get? → A: A representative engine-block-like solid (box-derived, analytic primitives), so the compartment reads as furnished rather than a bare box. It is representative interior furniture, independent of the propulsion module's engine bodies.
- Q: What is the transverse bound for an off-centre (`y != 0`) compartment? → A: `|position.y| + width/2 <= hull half-beam at the compartment's longitudinal station`, rejected with a parameter error before any geometry is constructed (the existing envelope-validation idiom, extended to the transverse axis).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A new `salon_galley` compartment type MUST be furnished with BOTH the salon furniture (settee + table) AND a galley counter (with blind sink + stove recesses), fused into the compartment's compound. The Alternativ5 fixture's combined compartment MUST use this type (changed from `salon`); the `salon` type stays settee + table only.
- **FR-002**: Furniture MUST be dispatched by compartment TYPE for every layout (canonical, DS, and custom); the layout-name furnishing gate MUST be removed, so a custom (non-canonical) layout's furnishable-type compartments are furnished, not boxed. Only genuinely non-furnishable types keep a structural box.
- **FR-003**: The set of recognized compartment types MUST be extended to include `aft_cabin`, `dinette`, `engine_room`, `wet_locker`, and `salon_galley`, in addition to the existing `forward_cabin`, `galley`, `head`, `salon`, `helm`.
- **FR-004**: Each new compartment type MUST produce furniture appropriate to it: `aft_cabin` → a berth, `dinette` → settee + table, `engine_room` → a representative engine-block-like solid (box-derived, independent of the propulsion module), `wet_locker` → a locker/shelving fitting, `salon_galley` → settee + table + galley counter (FR-001).
- **FR-005**: The furniture-fit envelope validation MUST apply to the new compartment types (a fitting taller than its compartment is rejected before geometry construction).
- **FR-006**: The v1.0 centreline constraint (`position.y` must be 0) MUST be removed so compartments can be placed off-centre (`y != 0`); the compartment and its furniture MUST be positioned at the specified transverse offset.
- **FR-007**: An off-centre compartment MUST satisfy `|position.y| + width/2 <= hull half-beam at the compartment's longitudinal station`; a compartment violating this MUST be rejected with a parameter error before geometry construction (the hull-envelope guard extended to the transverse axis).
- **FR-008**: Every furniture piece produced MUST be a valid, watertight (STL-exportable) solid shape; the galley counter and each new-type fitting MUST be a single valid solid, and the spec 012 galley manifold guard (`Solids == 1`, `isValid()`) MUST be preserved, including for the Alternativ5 integrated galley. (Some existing fittings — e.g. the spec 024 head faucet — are legitimately two disjoint valid solids; "single solid" is required of the galley counter and the new-type fittings, not of every pre-existing piece.)
- **FR-009**: Two builds of the same layout with identical inputs MUST produce byte-identical geometry (constitution II).
- **FR-010**: The public `build_interior` signature and the `Interior` aggregate MUST stay backward-compatible; new behavior is additive (new types, off-centre placement, custom furnishing) and opt-in via the YAML layout content.
- **FR-011**: Alternativ1–4 and the DS layout MUST build byte-identically to their pre-025 output; only Alternativ5 changes geometry (it gains its galley). The Alternativ5 fixture MUST be updated so its galley-in-salon is expressed in the canonical fixture data.
- **FR-012**: Construction MUST stay FreeCAD-idiomatic and consistent with the spec 012 interior idiom: furniture is `Part::Feature` B-rep solids (no raw mesh outside export adapters), each furnished compartment is a `Part::Compound`, and every new dimension is a named parameter with a default (constitution I, III).
- **FR-013**: The existing no-overlap and hull-containment validations MUST continue to hold for layouts using the new types and asymmetric placement.

### Key Entities

- **Compartment type**: the enumerated kind of a compartment, now extended with `aft_cabin`, `dinette`, `engine_room`, `wet_locker`, `salon_galley`; drives which furniture builder(s) run. Furniture is dispatched by this type for every layout (the layout-name gate is gone).
- **Custom layout**: a non-canonical YAML layout; previously boxed, now furnished by compartment type like any other layout.
- **Integrated salon-galley** (`salon_galley` type): a compartment carrying both salon (settee + table) and galley (counter + sink/stove recesses) furniture; used by Alternativ5.
- **New-type fittings**: berth (aft_cabin), settee+table (dinette), engine-block-like fitting (engine_room), locker (wet_locker), each with named parameters and defaults.
- **Transverse offset**: a compartment's `position.y`, now permitted non-zero; bounded by the hull half-beam at the compartment's station.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The Alternativ5 build contains a compartment with both settee/table and a galley counter (sink + stove recesses); the galley counter is a single valid solid.
- **SC-002**: A custom non-canonical layout with N furnishable-type compartments produces N furnished compartments (0 placeholder boxes for furnishable types); `is_furnished` is true for each.
- **SC-003**: A layout using all four new types builds successfully; each new-type compartment is furnished and every furniture piece is a single valid solid.
- **SC-004**: A compartment placed at `y != 0` builds successfully and is offset transversely; a compartment whose extent exceeds the half-beam is rejected with a clear parameter error.
- **SC-005**: Alternativ1–4 and the DS layout produce byte-identical geometry to their pre-025 output (volume + shape digest unchanged).
- **SC-006**: Two builds of any layout (canonical, custom, or asymmetric) with identical inputs produce byte-identical geometry.
- **SC-007**: 100% of furniture pieces across all layouts are valid and STL-exportable (watertight); the galley counter and every new-type fitting are single solids; no new construction introduces a non-watertight mesh.
- **SC-008**: Build time stays at human-scale (seconds), consistent with the existing interior geometry suite budget.

## Assumptions

- **Alt5 mechanism**: the integrated galley-in-salon is expressed either by a combined compartment type (e.g. `salon_galley`) or by furnishing the Alternativ5 salon compartment with both salon and galley fittings; the canonical Alternativ5 fixture is updated accordingly. `/clarify` will confirm the mechanism. Either way the result is one compartment carrying both furniture sets.
- **Custom-furnishing gate**: the furniture gate widens from "canonical/bundled layout names" to "any layout whose compartments use furnishable types" — custom layouts get furniture by type. Compartments of a non-furnishable/structural type (if any) keep a structural box.
- **New-type fittings**: reuse the existing berth/salon/galley builders where the new type maps cleanly (aft_cabin→berth, dinette→settee+table). engine_room and wet_locker get representative box-derived fittings (engine-block-like solid; locker with shelving), built with the same Part B-rep idiom and analytic primitives so they stay byte-reproducible (no arc-loft reproducibility risk, per spec 024).
- **Asymmetric envelope**: dropping `y = 0` keeps all other validation (overlap, hull containment, furniture-fit); the transverse bound is the hull half-beam at the compartment's longitudinal station. Symmetry was a v1.0 simplification, not a geometric necessity.
- **Reproducibility**: all new geometry uses analytic Part primitives (boxes, fillets, cuts, fuses) like spec 024, which a spike proved byte-reproducible — no lofts, so no spec 022/018 arc-loft reproducibility wall.
- **Scope boundary**: the DS enclosed-saloon interior layout is NOT part of this spec (absorbed into spec 023). This spec does not touch deck/superstructure or the propulsion module.
- **Verification host**: geometry tests require FreeCAD 1.1+ (bundled-Python `PYTHONPATH`); unit-only validation (type set, parameter dataclasses, asymmetric/envelope validators) runs without FreeCAD.
