# Feature Specification: Window & Porthole Cutouts

**Feature Branch**: `011-window-cutouts`

**Created**: 2026-05-29

**Status**: Draft

**Input**: User description: "Add window and porthole openings to the Storebro model: portholes in the hull topsides, cabin-trunk side windows, and a windshield reworked as a frame + recessed glass pane. Geometry only (transparency/color is spec 015). PATCH bump 1.0.4 -> 1.0.5, additive API, glazing on by default."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Portholes in the hull (Priority: P1)

A restorer builds the default hull and sees a row of small circular portholes cut into the topsides on both sides, above the waterline — the hull reads as a cabin cruiser with accommodation below, not a solid shell.

**Why this priority**: Portholes are the most recognizable "this hull has a cabin" cue and they exercise the riskiest mechanic in this spec (boolean cuts into the hull solid). Getting them right de-risks everything else.

**Independent Test**: Call `build_hull()` and confirm the hull body carries a row of circular openings (port + starboard, symmetric, above the waterline) cut as editable subtractive features, and the resulting solid is still a single closed manifold.

**Acceptance Scenarios**:

1. **Given** default parameters, **When** `build_hull` runs, **Then** the hull body has N portholes per side (symmetric port/starboard) above the waterline, each a clean circular opening, and the body remains a valid single solid.
2. **Given** custom porthole parameters (count, diameter, height), **When** `build_hull` runs, **Then** the openings match the supplied values within tolerance and stay above the waterline.
3. **Given** a porthole whose diameter or position would not cleanly intersect the hull wall (e.g., placed below the keel or larger than the local freeboard), **When** parameters are validated, **Then** construction is rejected with a clear parameter error before any broken shape is produced.
4. **Given** zero portholes requested, **When** `build_hull` runs, **Then** no openings are cut and the hull is the same solid as before (no error).

---

### User Story 2 - Cabin-trunk side windows (Priority: P2)

The same user looks at the cabin trunk and sees rectangular (rounded-corner) window openings cut through each side wall — the deckhouse reads as having windows, not blank sides.

**Why this priority**: Side windows are the second-strongest glazing cue and depend on the cabin trunk built in spec 008, so they layer naturally after the hull portholes.

**Independent Test**: Build the default deck; confirm the cabin trunk body has a rectangular rounded-corner opening cut through each side wall, port and starboard, symmetric, sized to fit within the wall.

**Acceptance Scenarios**:

1. **Given** the default cabin trunk, **When** `build_deck` runs, **Then** each side wall has a window opening cut through it, symmetric port/starboard, fully within the wall extents.
2. **Given** a window taller or longer than the cabin trunk wall, **When** parameters are validated, **Then** construction is rejected with a clear parameter error before any broken shape is produced.
3. **Given** zero windows requested, **When** `build_deck` runs, **Then** the cabin trunk is uncut (no error).

---

### User Story 3 - Windshield as frame + glass (Priority: P3)

The user sees the windshield as a glass pane held in a frame, rather than a solid grey slab — there is a frame border around a recessed glass pane.

**Why this priority**: The windshield is a single component and the change is the most self-contained, so it comes last. It completes the "this boat has glazing" read.

**Independent Test**: Build the default deck; confirm the windshield is a frame body (slab with a central opening) plus a separate thin glass-pane body seated in the opening, both within the windshield envelope.

**Acceptance Scenarios**:

1. **Given** default parameters, **When** `build_deck` runs, **Then** the windshield consists of a frame body with a central opening plus a distinct glass-pane body that sits inside the opening.
2. **Given** a frame border so wide that no opening remains, **When** parameters are validated, **Then** construction is rejected with a clear parameter error.
3. **Given** glazing disabled for the windshield, **When** `build_deck` runs, **Then** the windshield falls back to the spec 008 solid slab (no error).

---

### Edge Cases

- **Recess too deep**: a porthole/window recess depth >= the local wall thickness (which would punch through or exceed the solid) MUST be rejected at validation. This is the spec 009 lesson: boolean ops that produce non-manifold results break STL export downstream — blind recesses avoid it entirely as long as depth stays below the wall.
- **Opening too large**: an opening larger than the available solid face (e.g., porthole diameter > local freeboard, window > wall extents) MUST be rejected.
- **Below the waterline**: portholes positioned at or below the waterline MUST be rejected (a porthole below the waterline is a hole in the boat).
- **Zero-count**: zero portholes / zero windows / windshield-glazing-off each build the un-cut solid without raising.
- **Reproducibility**: identical parameters produce byte-identical geometry — no timestamps, randomness, or environment-dependent values in any cut or pane.
- **Partial build failure**: if any cut or pane fails mid-build, the whole `build_hull` / `build_deck` call rolls back to its pre-call state.
- **Both parameter forms**: the existing mutually-exclusive legacy-vs-composite parameter handling is preserved; the new glazing parameters are additive and independent.
- **Manifold preservation**: after all cuts, each cut solid (hull, cabin trunk) MUST remain a single closed manifold suitable for STL export.

## Clarifications

### Session 2026-05-29

- Q: The hull is a SOLID loft (no interior cavity). Should portholes be through-holes or blind recesses? → A: Blind circular recesses pocketed into the hull topside to a shallow fixed depth. A through-hole into a solid has no cavity to enter and risks the spec 009 non-manifold failure; a blind recess is always manifold and reads correctly as a porthole from outside. (Spec 015 can later darken/glaze the recess face.)
- Q: The cabin trunk is also a SOLID loft. Should side windows be through-tunnels or blind recesses per side? → A: Blind rectangular rounded-corner recesses pocketed into each side wall (per side, not a port↔starboard tunnel). Manifold-safe and reads as a window; a through-tunnel would let you see straight through the boat and carries non-manifold risk.
- Q: How are portholes placed by default? → A: A row of 3 per side, evenly spaced over the cabin-trunk longitudinal extent, centered vertically at mid-freeboard (halfway between the waterline and the sheer). Count, diameter, span, and height are parameters.
- Q: API surface for the new glazing parameters? → A: Two separate optional composites — `HullGlazingParameters` (portholes) passed via a new `parameters_glazing` kwarg on `build_hull`, and `DeckGlazingParameters` (cabin-trunk windows + windshield frame/pane) passed via a new `parameters_glazing` kwarg on `build_deck`. Orthogonal to existing composites; additive.
- Q: Which openings get a separate glass-pane body in v1.0.5? → A: Only the windshield (frame + recessed pane body, since the windshield is a thin slab where a clean through-opening is safe). Portholes and cabin windows are blind recesses only — no separate pane bodies — to keep scope bounded and manifold-safe; pane bodies for ports/windows deferred to a later spec.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The hull builder MUST cut a parametric row of circular porthole recesses into the hull topsides (blind shallow pockets, NOT through-holes), port and starboard, symmetric about the centerline, above the waterline, as editable subtractive features on the existing hull body's feature tree. Default: 3 per side, evenly spaced over the cabin-trunk longitudinal extent, centered at mid-freeboard.
- **FR-002**: The deck builder MUST cut rectangular rounded-corner window recesses into each cabin-trunk side wall (blind pockets per side, NOT a port↔starboard tunnel), symmetric, as editable subtractive features.
- **FR-003**: The deck builder MUST rework the windshield into a frame body (the thin slab with a central through-opening pocketed out, leaving a configurable border) plus a separate thin glass-pane body seated in the opening.
- **FR-004**: All cuts MUST be FreeCAD-idiomatic subtractive features (no raw mesh) and MUST keep the parametric history editable in the GUI.
- **FR-005**: Each new opening/pane class MUST have its own frozen parameter dataclass (mm lengths, degree angles) with `__post_init__` validation that raises the module's existing parameter-error type, naming the offending field.
- **FR-006**: All cuts MUST be seated on the ACTUAL hull/deck geometry (sampled sheer, resolved deck-top, the actual cabin-trunk and windshield bodies), not analytical formulas.
- **FR-007**: A cut that would produce a malformed result MUST be rejected with a clear parameter error BEFORE any broken shape is produced. For blind recesses (portholes, cabin windows): the recess depth MUST be less than the local wall thickness (so it stays a blind pocket, never accidentally a through-cut or a cut deeper than the solid) and the opening MUST fit within the wall extents (above the waterline for portholes, within the wall for windows). For the windshield through-opening: the border MUST leave a positive-width frame on all sides.
- **FR-008**: After all cuts, each cut solid (hull, cabin trunk, windshield frame) MUST remain a single closed manifold (validated by solid count and watertightness checks), so STL export is unaffected. Blind recesses into a solid are manifold by construction; this requirement is the regression guard.
- **FR-009**: Glazing MUST be built by default — existing `build_hull()` / `build_deck()` callers receive portholes, side windows, and the framed windshield automatically with RC34 1972 estimate-grade defaults.
- **FR-010**: Two new optional composite parameter forms MUST let callers override glazing parameters: `HullGlazingParameters` (portholes) via a new `parameters_glazing` keyword argument on `build_hull`, and `DeckGlazingParameters` (cabin-trunk windows + windshield frame/pane) via a new `parameters_glazing` keyword argument on `build_deck`. Both are orthogonal to the existing composites; the existing mutually-exclusive legacy-vs-composite handling MUST be preserved.
- **FR-011**: Zero-count glazing (zero portholes, zero windows, windshield-glazing-off) MUST build the un-cut solid without raising.
- **FR-012**: On any FreeCAD-side failure during a cut or pane build, the call MUST roll back every object it added and restore the document to its pre-call state.
- **FR-013**: Glazing geometry MUST be reproducible: identical parameters produce byte-identical output, no timestamps/randomness/environment-dependent values.
- **FR-014**: Glazing principal dimensions MUST match the `docs/references/Alternativ3.JPG` RC34 1972 reference within ±1% (per constitution IV); per-instance fine detail (corner-radius exactness, frame bevels) is exempt.
- **FR-015**: New glazing objects MUST be exposed on the `build_hull` / `build_deck` return aggregates so callers can access them.
- **FR-016**: The public API change MUST be additive only — no existing public name removed or signature broken. Version is bumped PATCH (1.0.4 → 1.0.5) and `storebro.__version__` updated to match `pyproject.toml`.
- **FR-017**: The transparency/material/color of the glass panes is OUT OF SCOPE (owned by spec 015 render-attributes); spec 011 delivers geometry only.

### Key Entities

- **Porthole**: A circular blind recess in the hull topside. Attributes: diameter, recess depth, count per side, longitudinal span, height above waterline; seated above the waterline on the actual hull wall; cut as a subtractive feature.
- **Cabin-Trunk Side Window**: A rectangular rounded-corner blind recess in a cabin-trunk side wall. Attributes: length, height, corner radius, recess depth, longitudinal position, sill height; per side.
- **Windshield Frame**: The windshield thin slab with a central through-opening pocketed out, leaving a border of configurable width.
- **Windshield Glass Pane**: A thin solid body seated in the windshield frame opening (its transparency is spec 015).
- **HullGlazingParameters**: Optional composite bundling the porthole parameters; consumed by `build_hull`.
- **DeckGlazingParameters**: Optional composite bundling the cabin-trunk window + windshield frame/pane parameters; consumed by `build_deck`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A default `build_hull()` produces a hull with the default number of portholes per side, and the hull remains a single closed manifold (solid count = 1, watertight).
- **SC-002**: A default `build_deck()` produces a cabin trunk with one window opening per side and a windshield consisting of a frame body plus a glass-pane body.
- **SC-003**: Every new parameter dataclass rejects out-of-range / non-intersecting input with a clear parameter error naming the field, verified by unit tests covering each validation branch.
- **SC-004**: An opening that would produce a non-manifold or blind cut is rejected before construction (verified by test) — STL export of the default model still succeeds.
- **SC-005**: Two consecutive builds with identical parameters produce byte-identical exported geometry.
- **SC-006**: A mid-build failure in any cut or pane leaves the document in its exact pre-call state (rollback verified by test).
- **SC-007**: Existing `build_hull()` / `build_deck()` callers that pass no new arguments continue to succeed and now receive glazing automatically.
- **SC-008**: The full test suite (`uv run pytest`), `ruff check`, and `mypy --strict` all pass; the model opens and visually verifies in FreeCAD against the reference photo.

## Assumptions

- **Porthole shape**: simple circular openings (the classic round port). Oval/rectangular ports and opening hardware (hinges, dogs) are out of scope.
- **Window shape**: rectangular with a rounded corner radius; the multi-pane mullions and sliding tracks of the real cabin windows are out of scope ("basic" glazing geometry).
- **Windshield glass pane**: a thin solid slab geometry; its transparency/material is spec 015. The pane is modeled so spec 015 can later assign a glass material to it.
- **Frame vs. pane bodies**: the windshield becomes two bodies (frame + pane) where spec 008 had one slab; this is an additive change to the `Deck.windshield` representation, expected to update windshield-specific tests.
- **Manifold guard**: the spec 009 lesson (boolean/arc ops producing non-manifold meshes that broke STL) drives FR-007/FR-008 — cuts are validated for clean intersection and the result is checked for a single closed solid.
- **Module split**: portholes modify the hull module (`build_hull`); side windows + windshield modify the deck module (`build_deck`). Both follow their module's existing parameter-error type and rollback discipline.
- **Reference source**: `docs/references/Alternativ3.JPG`, consistent with specs 007–010; estimate-grade defaults where the photo is ambiguous, refinable in later PATCH bumps.
- **Glazing-on-by-default behavior change**: existing tests asserting exact body counts or the windshield being a single solid will need updating; this is an expected additive change, not a breaking public-API change.
- **Dependency on spec 008/010**: side windows depend on the spec 008 cabin trunk; the windshield rework replaces the spec 008 windshield slab.
