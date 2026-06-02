# Feature Specification: DS-Variant Superstructure (enclosed deck saloon)

**Feature Branch**: `016-ds-variant-superstructure`

**Created**: 2026-06-02

**Status**: Draft

**Input**: User description: "Add a second canonical superstructure variant matching the Storebro DS model (built-in styrhytt / enclosed wheelhouse / deck saloon) seen in docs/references/storo34_side_lines.png. Reuses the hull from spec 007 verbatim — DS and standard RC34 share the underwater shape; only the deckhouse differs."

## Context

The standard Storebro RC34 superstructure (spec 008) is an **open flybridge** arrangement: a separate cabin trunk forward, a raked windshield, and a hardtop carried on open pillars, with an **open** air gap between the windshield top and the hardtop underside. The **DS** ("Deck Saloon" / Swedish *styrhytt*) variant **encloses** that helm volume: one continuous deckhouse running most of the hull length, with a raked front window wall, large wraparound side windows, an aft wall, and a flat roof. The underwater hull (spec 007) and every deck-level item — deck plate, railings, rubrail, bow pulpit, lifelines, anchor locker, cleats (specs 008/010) — are shared verbatim. **Only the deckhouse differs.**

This is the project's first superstructure *variant selection*. It mirrors the established interior layout-switching pattern (Alternativ1–5, specs 004/012/013), but at the deck level: one boat, two canonical topsides silhouettes.

## Clarifications

### Session 2026-06-02

- Q: How are DS-variant side and front windows modeled — blind recesses only, or recesses plus separate translucent glass-pane bodies? → A: Blind recesses only (no distinct glass-pane bodies), matching the spec 011 cabin-trunk side-window precedent; separate glazing panes are deferred to a future spec.
- Q: What is the deckhouse solid topology — a single filled solid block, or a hollowed shell with explicit wall thickness? → A: A single SOLID filled block (raked front wall + two side walls + aft wall + flat roof realized as one closed solid), carrying blind window recesses — not a hollowed shell. Manifold by construction, matching the spec 011 SOLID-loft lesson.
- Q: How is the DS parameter set passed to the builder? → A: Via a new `parameters_deckhouse` keyword carrying a `DeckhouseParameters` composite, orthogonal to the existing `parameters_superstructure` / `parameters_hardware` / `parameters_glazing` keywords (same pattern).
- Q: How are the open-flybridge aggregate fields handled in DS mode? → A: `cabin_trunk`, `windshield`, `hardtop`, `hardtop_pillars` become optional and are `None` in DS mode; the aggregate gains `superstructure_variant: str` and `deckhouse: Deckhouse | None` (`None` in standard mode).
- Q: When the DS variant is selected, how are the standard superstructure inputs treated? → A: An explicit `parameters_superstructure` (open-flybridge composite) is rejected as a contradictory combination; the legacy `parameters` (DeckParameters) is still accepted and continues to drive the shared deck plate.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build the DS enclosed-wheelhouse silhouette (Priority: P1)

A FreeCAD scripter or restorer wants the Storebro DS profile — the enclosed deck saloon — instead of the open flybridge. They call the deck builder selecting the `ds` variant (or pass `--superstructure ds` on the CLI) and receive a document whose topsides read as a continuous enclosed wheelhouse matching `docs/references/storo34_side_lines.png`, seated on the unchanged hull.

**Why this priority**: This is the entire feature. Without it there is no DS variant; with it the roadmap's final bonus silhouette ships.

**Independent Test**: Build a hull, build a deck with `superstructure_variant="ds"`, and verify the returned aggregate exposes a single enclosed `deckhouse` body (manifold, `Solids == 1`, `isValid()`), no open-flybridge bodies, and the shared deck plate + railings + hardware. Visually confirm in the FreeCAD GUI against the reference image.

**Acceptance Scenarios**:

1. **Given** a valid hull, **When** the deck is built with the DS variant selected, **Then** the returned aggregate has a non-`None` `deckhouse` body and `cabin_trunk`/`windshield`/`hardtop`/`hardtop_pillars` are `None`, while `deck_plate`, `railings`, and all five hardware items are populated.
2. **Given** the DS variant, **When** the deckhouse body is constructed, **Then** it is a single closed manifold solid (`Solids == 1`, `Shape.isValid()`), with a raked front wall, two side walls, an aft wall, and a flat roof.
3. **Given** the DS variant with default parameters, **When** the document is recomputed, **Then** the deckhouse principal dimensions (length, height, forward/aft width) match the `storo34_side_lines.png` reference within ±1%.
4. **Given** the DS variant, **When** the side window recesses are cut, **Then** each is a blind recess and the deckhouse remains a single manifold solid (no through-holes, no non-manifold tessellation); the raked front face serves as the windscreen with no separate recess.

---

### User Story 2 - Standard variant remains the unchanged default (Priority: P1)

Every existing caller of the deck builder — the CLI default, the interior/export/render pipeline, all current tests — continues to receive the standard open-flybridge superstructure with byte-identical geometry. The DS variant is strictly opt-in.

**Why this priority**: Back-compat is non-negotiable. The DS variant must not perturb a single existing output. Same priority as Story 1 because shipping the variant at the cost of regressing the default is a net loss.

**Independent Test**: Build a deck with no variant argument and confirm the result is identical to the pre-feature output (same bodies, same dimensions, same field population: `deckhouse is None`, all six open-flybridge bodies present).

**Acceptance Scenarios**:

1. **Given** no variant argument, **When** the deck is built, **Then** `superstructure_variant == "standard"`, `deckhouse is None`, and all six open-flybridge bodies (deck plate, cabin trunk, windshield, hardtop, pillars, railings) are present exactly as before this feature.
2. **Given** the CLI with no `--superstructure` flag, **When** a boat is built, **Then** the standard variant is used.
3. **Given** the existing geometry test suite, **When** it runs after this feature, **Then** every pre-existing standard-variant assertion still passes.

---

### User Story 3 - Select the variant from the CLI (Priority: P2)

A user building from the command line picks the topsides silhouette with a single flag, consistent with the existing `--layout` and `--engine-count` selectors.

**Why this priority**: The CLI is the primary public entry point. Without the flag the DS variant is reachable only from Python. Lower than P1 because the library API (Story 1) is the load-bearing surface; the CLI is a thin composition over it.

**Independent Test**: Run the build subcommand with `--superstructure ds` and confirm the produced document carries the DS deckhouse; run with `--superstructure standard` (and with the flag omitted) and confirm the standard superstructure.

**Acceptance Scenarios**:

1. **Given** `--superstructure ds`, **When** the build runs, **Then** the deck is built with the DS variant.
2. **Given** `--superstructure standard` or the flag omitted, **When** the build runs, **Then** the deck is built with the standard variant.
3. **Given** an unrecognized `--superstructure` value, **When** the build runs, **Then** the CLI rejects it with a clear error and a non-zero exit code (standard argument-choice validation).

---

### Edge Cases

- **Invalid DS parameters**: A DeckhouseParameters field out of range (non-positive length/width/height, front_rake_angle outside its band, forward_width > aft_width violating the tapered-silhouette invariant) is rejected before any FreeCAD call with the same `DeckParameterError` shape (parameter name, offending value, valid range) the rest of the deck module uses.
- **Cross-hull fit**: A deckhouse longer than the hull, or wider than the beam (plus walkways), is rejected with a cross-field `DeckParameterError` before construction — mirroring the standard cabin-trunk cross-hull checks.
- **Mid-build FreeCAD failure**: If any DS sub-feature fails during construction, every body added so far in this build is rolled back and the document is restored to its pre-call state, exactly as the standard build path does; the failure surfaces as `DeckConstructionError`.
- **Window recess larger than wall**: A window recess whose footprint exceeds the wall panel it is cut into is rejected (or clamped) so the deckhouse cannot be split into multiple solids — the spec 009 non-manifold regression guard.
- **Variant + explicit standard-only parameters**: Passing DS variant together with `parameters_superstructure` (an open-flybridge composite) is a contradiction; the builder rejects the combination with a clear `DeckParameterError` rather than silently ignoring one input.
- **Render attributes off**: With render attributes disabled, the DS deckhouse builds without colour/material assignment, identical in geometry to the coloured build.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The deck builder MUST accept a superstructure-variant selector with exactly two canonical values, `standard` and `ds`, defaulting to `standard`.
- **FR-002**: When `standard` is selected (including by default), the deck builder MUST produce output byte-identical to the pre-feature standard superstructure — same bodies, same dimensions, same aggregate field population.
- **FR-003**: When `ds` is selected, the deck builder MUST build a single enclosed deckhouse body (raked front wall + two side walls + aft wall + flat roof) in place of the open-flybridge cabin trunk, windshield, hardtop, and pillars.
- **FR-004**: The DS deckhouse MUST be a single closed manifold solid: `Shape.Solids` count == 1 and `Shape.isValid()` true (the spec 009 manifold regression guard).
- **FR-005**: The DS deckhouse MUST be seated on the actual sampled deck-plate top surface (not an analytical approximation) so it neither floats above nor pierces the deck.
- **FR-006**: DS-variant side windows MUST be modeled as blind recesses cut into the single filled deckhouse solid (never boolean through-holes, never separate glass-pane bodies in this spec), keeping the deckhouse a single manifold solid and not breaking mesh export. The front of the deckhouse is the raked windscreen FACE itself (a flush screen), not a separate cut recess — the reference DS front is a single large raked screen, so no front-face recess is cut. (A separate front-window recess frame is a future-PATCH refinement.)
- **FR-007**: In DS mode the deck plate, railings, rubrail, bow pulpit, lifelines, anchor locker, and cleats MUST still be built, shared verbatim with the standard variant where they do not depend on the open-flybridge bodies.
- **FR-008**: The deck aggregate MUST expose which variant was built and MUST expose the deckhouse body when present; the open-flybridge body slots MUST be absent (null) in DS mode and the deckhouse slot MUST be absent (null) in standard mode.
- **FR-009**: DS deckhouse dimensions MUST be parametric — every dimension a named parameter with a default; no magic numbers in construction logic.
- **FR-010**: DS deckhouse parameter defaults MUST be reference-faithful to `docs/references/storo34_side_lines.png` within ±1% on principal dimensions (length, height, forward width, aft width) at the canonical LOA.
- **FR-011**: Invalid DS parameters MUST be rejected before any FreeCAD call with the deck module's existing parameter-error shape (offending field name, offending value, human-readable valid range).
- **FR-012**: DS parameters MUST be validated against the hull (length fits within LOA, width plus walkways fits within beam) before construction, raising the deck module's cross-field parameter error.
- **FR-013**: Any FreeCAD-side failure during a DS build MUST roll back every body added in that build and restore the document to its pre-call state, surfacing as the deck module's construction error — identical rollback semantics to the standard path.
- **FR-014**: Selecting the DS variant together with an explicit `parameters_superstructure` (open-flybridge composite) MUST be rejected as a contradictory combination before construction. The legacy `parameters` (DeckParameters) MUST still be accepted and continues to drive the shared deck plate. DS deckhouse inputs MUST be supplied via a dedicated `parameters_deckhouse` keyword carrying a `DeckhouseParameters` composite, orthogonal to the other parameter keywords.
- **FR-015**: The CLI build subcommand MUST accept a superstructure flag whose accepted values are `standard` and `ds`, defaulting to `standard`; an unrecognized value MUST be rejected with a non-zero exit code.
- **FR-016**: Build outputs MUST remain reproducible: identical inputs (variant + parameters) produce identical geometry, with no timestamps or environment-dependent paths baked into the artifact.
- **FR-017**: The DS deckhouse (and its window glass, if modeled as a distinct body) MUST receive render colour/material attributes consistent with the spec 015 palette (deckhouse white, glazing translucent) when render attributes are enabled, and MUST build identically when they are disabled.
- **FR-018**: The DS variant MUST NOT boolean-cut or otherwise mutate the hull solid; the hull is shared read-only and reused verbatim.

### Key Entities *(include if feature involves data)*

- **Superstructure variant**: The selector identifying which topsides silhouette to build — one of `standard` (open flybridge, spec 008) or `ds` (enclosed deck saloon, this spec). Default `standard`.
- **Deckhouse**: The enclosed DS superstructure body — a single manifold solid composed of a raked front wall, two side walls (with window recesses), an aft wall, and a flat roof — replacing the standard variant's cabin trunk + windshield + hardtop + pillars. Seated on the deck-plate top.
- **DeckhouseParameters**: The parametric inputs for the deckhouse (length, forward width, aft width, height above deck, front rake angle, roof thickness, wall thickness/inset, forward offset, window geometry), in millimeters and degrees, with reference-faithful defaults and per-field validation.
- **Deck aggregate (extended)**: The deck build result, extended to carry the variant identity and an optional deckhouse, with the open-flybridge body slots becoming optional so they can be absent in DS mode.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can produce the DS enclosed-wheelhouse silhouette with a single argument (library) or a single flag (CLI), no other call-site changes.
- **SC-002**: 100% of pre-existing standard-variant geometry tests pass unchanged after the feature lands (zero regression in the default path).
- **SC-003**: The DS deckhouse builds as a single manifold solid (`Solids == 1`, `isValid()`) for the default parameters and for the full validated parameter range, and STL export of the DS build succeeds.
- **SC-004**: The DS deckhouse principal dimensions match `docs/references/storo34_side_lines.png` within ±1% at the canonical LOA, confirmed by a maintainer GUI eyeball against the reference image.
- **SC-005**: Invalid DS parameters and contradictory variant/parameter combinations are rejected before any FreeCAD call, with an error naming the offending field and its valid range; 100% of the documented invalid-input cases raise the expected error.
- **SC-006**: A mid-build FreeCAD failure in DS mode leaves the document with zero residual partial bodies (full rollback), identical to the standard path.

## Assumptions

- The DS variant reuses the spec 007 hull verbatim; no hull parameter or geometry change is in scope.
- The deck plate, railings, and all spec 010 hardware are shared with the standard variant and are not re-specified here; only their continued presence in DS mode is asserted.
- The DS deckhouse is modeled as one enclosed solid with blind window recesses, consistent with the specs 009/011 manifold-by-construction lesson; detailed mullions, opening windows, door cut-throughs, and interior helm fittings are out of scope (deferrable to a future spec).
- Default DS dimensions are estimate-grade visual measurements from `storo34_side_lines.png` at the canonical RC34 LOA, refinable in a later PATCH bump if a primary source surfaces — consistent with how spec 008 sourced its defaults.
- This is a **light track** feature per the spec register: an additive variant with no new state machine, no concurrency, and a single actor — `/clarify` + `/allium:elicit` apply; `/tla` is skipped unless the variant-selection logic proves non-trivial.
- The interior module is variant-agnostic for this spec: the DS deckhouse provides headroom that the existing interior envelope already permits; re-fitting interiors specifically to the DS saloon is out of scope.
- Adding the variant selector and the optional deckhouse slot is an additive, backward-compatible public-API change (MINOR bump): existing positional/keyword call sites are unaffected.
