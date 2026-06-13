# Feature Specification: Windshield Crown (transverse arched top edge)

**Feature Branch**: `master` (solo / direct-push — no feature branch per spec-register rule)

**Created**: 2026-06-13

**Status**: Draft

**Input**: User description: "030 windshield-crown (light track). Give the Storebro windshield a transverse arched (crowned) top edge — looking at the boat head-on, the top edge of the windshield bows UPWARD at the centerline (Y=0) and drops to the corners, instead of the current dead-flat horizontal top line. ... must preserve the spec 011 frame-opening Pocket AND the separate WindshieldGlass pane ... byte-reproducible and manifold; gate with manifold-or-fallback to the current flat-top slab if the crowned loft fails."

## Context

Today the windshield (`src/storebro/deck.py`, `_build_windshield`) is a `PartDesign::Body`
lofted from three YZ-parallel **rectangular** cross-section sketches (base / mid / top
datums) with `PartDesign::AdditiveLoft`, `Ruled=False`. The loft is already smooth in
**rake** (the X position of each section varies with Z), but every section is a flat
rectangle (width along Y, thickness along Z), so the **top edge of the panel is a dead-flat
horizontal line** across the beam. The reference Storebro RC34 windshield instead has a
gentle transverse **crown** — the top trim bows upward at the centerline and falls away to
the corners.

Spec 020 (superstructure-curvature-refinement) deferred this specifically because the crown
changes the section profile from a rectangle to a shape with a curved top edge, and that
top-edge change has to coexist with the spec 011 frame work: a central `WindshieldFrameOpening`
Pocket (`ThroughAll` along X, leaving `frame_border` on all sides) and a separate
`Deck_WindshieldGlass` pane that fills the opening. The crowned top must not eat into the
frame border or leave the glass pane proud of / floating inside the panel.

## Clarifications

### Session 2026-06-13

All four questions auto-picked the recommended answer (light-track auto-pick per the feature-pipeline hook).

- Q: Default value of the new crown-rise field? → A: **Ship a sensible non-zero default of 60 mm** (the boat reads crowned out of the box — the whole point of the spec); `0.0` is the explicit OFF sentinel that reproduces the pre-030 flat-top windshield byte-identically. (Geometry default changes → new signoff hash, expected for a geometry spec, same as specs 007/008.)
- Q: How is the arched top edge realised geometrically? → A: **Deterministic polyline approximation** of the arc (straight segments tracing the arch), NOT a Sketcher circular arc — avoids Sketcher-solver nondeterminism on the reproducibility-sensitive path, matching the spec 021 NACA-foil polyline precedent.
- Q: Which loft sections get the arched top edge? → A: **All three sections (base / mid / top) get the same arched top edge with a uniform crown rise**, so every profile has identical vertex topology (robust `Ruled=False` loft) and the top face is a smooth fore-aft crowned cap; the bottom edge of every section stays a flat straight line.
- Q: What bounds a valid crown value? → A: **`0.0 ≤ crown_height < top_width / 2`** (strict upper bound excludes the degenerate semicircle/over-arch), plus finite and non-negative; out-of-range → `DeckParameterError`. The frame opening stays rectangular and is never threatened (crown only adds material above the corners, which keep the pre-030 top Z), so frame-margin validity is inherited from the flat-top config — no extra frame check needed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Crowned windshield top edge (Priority: P1)

A modeler builds the standard superstructure and the windshield's top edge reads as a gentle
upward arch at the centerline rather than a flat horizontal bar, matching the RC34 reference
silhouette when viewed head-on. The framed glass opening and its glass pane remain intact and
correctly inset.

**Why this priority**: This is the entire spec — a single cosmetic geometry refinement of one
existing body. There is no MVP smaller than "the top edge is crowned."

**Independent Test**: Build the deck superstructure with the default windshield parameters and
inspect the windshield body's bounding box and top edge: the top edge's Z at the centerline
(Y=0) exceeds the top edge's Z at the corners by the configured crown rise, the body stays a
single manifold solid, the glass opening still leaves at least `frame_border` of frame on every
side, and the glass pane still seats inside the opening.

**Acceptance Scenarios**:

1. **Given** the default `WindshieldParameters`, **When** the windshield is built, **Then** the
   windshield body is a single manifold solid whose top edge rises by the configured crown height
   at Y=0 relative to the top edge at the port/starboard corners.
2. **Given** crown height set to its OFF sentinel, **When** the windshield is built, **Then** the
   produced geometry is byte-identical to the pre-030 flat-top windshield (full back-compat).
3. **Given** glazing enabled (`WindshieldGlazingParameters.enabled`), **When** the crowned
   windshield is built, **Then** the `WindshieldFrameOpening` pocket and the separate
   `Deck_WindshieldGlass` pane are still created, the frame retains at least `frame_border`
   on all four sides of the opening, and the glass pane fits within the opening.
4. **Given** the same parameters built twice in the same process, **When** both windshields are
   exported, **Then** the resulting shapes are byte-identical (reproducibility, constitution II).

### Edge Cases

- **Crown height ≥ available top margin**: If the requested crown rise would push the arched top
  into the frame opening (less than `frame_border` of solid frame remaining above the opening) or
  invert the section, the parameter MUST be rejected at construction time with a clear
  `DeckParameterError` (fail-fast, constitution principle / project "Fail fast").
- **Crowned loft fails to produce a manifold solid** in FreeCAD: the build MUST fall back to the
  existing flat-top slab geometry (manifold-or-fallback, the spec 023/024 pattern) rather than
  emit a broken body. The fallback path is observable so the maintainer knows it triggered.
- **Crown height = 0 / OFF sentinel**: no crown is applied; geometry is byte-identical to pre-030.
- **Negative crown height**: rejected with `DeckParameterError` (an upside-down "frown" top edge
  is not a supported shape).
- **Non-finite crown height (NaN/inf)**: rejected via the existing `_reject_nonfinite_floats`
  guard (spec 029), consistent with every other float field.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `WindshieldParameters` MUST expose a new parametric crown-rise field `crown_height`
  (millimetres, default `60.0`) that controls how far the top edge rises at the centerline (Y=0)
  above the corners. `0.0` is the OFF sentinel. No magic numbers in the body (constitution I).
- **FR-002**: When the crown field is greater than zero, the built windshield's top edge MUST
  arch upward at Y=0 and fall to the port/starboard corners, while the base/bottom edge and the
  rake behaviour are unchanged.
- **FR-003**: The crown MUST be applied as a transverse arch across the beam (Y), independent of
  the existing longitudinal rake (X-vs-Z) smoothing — both shaping behaviours coexist. The arch
  MUST be realised as a deterministic polyline approximation (straight segments), not a Sketcher
  circular arc, to keep the geometry byte-reproducible (clarify decision, spec 021 precedent).
- **FR-003a**: The arched top edge MUST be applied to all three loft sections (base/mid/top) with a
  uniform crown rise so every profile shares identical vertex topology and the `Ruled=False` loft
  stays robust; the bottom edge of every section MUST remain a flat straight line.
- **FR-004**: The windshield body MUST remain a single manifold solid when the crown is applied.
- **FR-005**: When glazing is enabled, the spec 011 `WindshieldFrameOpening` pocket and the
  separate `Deck_WindshieldGlass` pane MUST still be produced. The frame opening stays rectangular
  and centered (unchanged from spec 011); because the crown raises only the centerline and leaves
  the corners at the original flat-top Z, the solid frame margin above the opening is preserved at
  the corners (≥ `frame_border`, inherited from the flat-top config) and increased at the center.
  No additional frame-margin computation is required — the invariant holds by construction.
- **FR-006**: The crown field defaults to `60.0` mm (ships crowned by default). The explicit OFF
  value `crown_height == 0.0` MUST reproduce the pre-030 flat-top windshield byte-identically
  (the crowning code path is skipped entirely at 0.0).
- **FR-007**: A crown value outside `0.0 ≤ crown_height < top_width / 2` MUST raise
  `DeckParameterError` at construction with the offending value and the valid range (fail-fast).
  The strict upper bound `< top_width / 2` excludes the degenerate over-arch (semicircle and beyond).
- **FR-008**: A non-finite crown value (NaN/±inf) MUST be rejected, consistent with the spec 029
  `_reject_nonfinite_floats` guard; a negative crown value MUST be rejected.
- **FR-009**: If the crowned loft does not yield a manifold solid at build time, the build MUST
  fall back to the existing flat-top slab geometry rather than emit a non-manifold body.
- **FR-010**: Building the same windshield parameters twice in one process MUST yield byte-identical
  geometry (reproducibility, constitution II). No timestamps, no env-dependent values introduced.
- **FR-011**: The windshield render role / material assignment (spec 015) and the `Windshield`
  wrapper public shape (`body`, `rake_degrees`, `glass_pane`) MUST be unchanged — no new public
  entity, no signature change beyond the additive parameter field.

### Key Entities

- **WindshieldParameters** (existing dataclass): gains one additive float field for crown rise.
  No new dataclass, no new wrapper type, no new state.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With the default parameters, the windshield body's top-edge Z at Y=0 exceeds its
  top-edge Z at the corners by the configured crown rise (within geometric tolerance), and the
  body has exactly one solid.
- **SC-002**: With the crown OFF sentinel, the windshield geometry is byte-identical to the
  pre-030 build (verified by a value-pinned reproducibility check).
- **SC-003**: With glazing enabled and the default crown, the frame opening retains ≥ `frame_border`
  of solid frame on all four sides and the glass pane is fully contained in the opening.
- **SC-004**: Two builds of the same parameters in one process produce byte-identical shapes.
- **SC-005**: 100% of invalid crown inputs (negative, non-finite, over-margin) raise
  `DeckParameterError`; 100% of valid inputs build without error.

## Assumptions

- The crown is a single smooth transverse arch (one upward bow, maximum at Y=0), not a
  multi-wave or asymmetric profile. Symmetric port/starboard.
- The crown affects only the **top** edge of the windshield section; the bottom edge, side
  edges, thickness, base/top widths, and rake angles are untouched.
- FreeCAD is unavailable on the dev machine, so geometry assertions live in `requires_freecad`
  tests run by the maintainer; unit tests cover the new parameter validation (range, negative,
  non-finite, OFF sentinel) without FreeCAD, matching the spec 029 pattern.
- The build degrades gracefully (flat-top fallback) on any FreeCAD geometry failure, consistent
  with the spec 023/024 manifold-or-fallback precedent — the boat must still build.
- Light track per `.claude/rules/specs.md`: single actor, no concurrency, no state machine →
  `/allium:elicit` runs, `/tla` is skipped (no non-trivial state machine).
- Solo / direct-push: committed straight to `master`, no feature branch, no PR
  (per `project_workflow` memory and the spec-register rule).
