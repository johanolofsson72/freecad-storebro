# Feature Specification: Window Glass Panes

**Feature Branch**: `019-window-glass-panes` | **Created**: 2026-06-02 | **Status**: Draft

**Input**: Roadmap item 019 — replace the blind window/porthole recesses with real translucent glass-pane bodies (portholes, cabin-trunk side windows, DS deckhouse windows); the windshield already has its pane (spec 011). Adds rounded window corners — see Clarifications.

## Context

Specs 011/016 cut **blind recesses** for portholes (hull topsides), cabin-trunk side windows, and DS deckhouse side windows — they read as recessed frames, not glass. The windshield (spec 011) already carries a separate translucent glass-pane body (`Deck_WindshieldGlass`, palette role `glass`). This spec gives every other recessed window the same treatment: a thin translucent pane body seated in the recess, coloured by the existing spec 015 `glass` role. Panes are **additive** bodies (no booleans into the hull/trunk solids), so they are manifold-trivial and cannot break the host solid or its STL.

## Clarifications

### Session 2026-06-02

- Q: How are the glass panes modeled? → A: As separate thin additive bodies (a disc for portholes, a rectangular slab for cabin + DS windows) seated in each recess opening, never as a boolean on the host solid. Each is one simple solid → manifold-trivial.
- Q: Rounded window corners (roadmap mentions them)? → A: **Deferred.** Rounding the rectangular window panes needs a Sketcher fillet, which carries the non-watertight-mesh risk proven by the spec 018 bilge-arc re-defer. Panes stay rectangular/circular this spec; rounded corners are a future PATCH. (The recesses themselves are already rectangular by spec 011/016 design.)
- Q: On by default? → A: Yes — glass panes build by default wherever the host glazing is enabled, with a per-call opt-out, consistent with the spec 011/015 defaults. With render attributes off, panes still build (geometry) but get no colour.
- Q: Do panes change the host solids or their exports? → A: No. The host hull / cabin trunk / deckhouse solids are untouched (still manifold, byte-identical recesses); panes are additional bodies added to the same document.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Glazed portholes, cabin windows, and DS windows (Priority: P1)

A user builds the boat and the recessed windows now read as glass: translucent panes fill the porthole recesses, the cabin-trunk side windows, and (in the DS variant) the deckhouse side windows.

**Why this priority**: The whole feature — turns recessed frames into glass.

**Independent Test**: Build hull + deck (standard and DS); confirm a glass-pane body exists per porthole, per cabin window, and per DS window; each is a single valid solid with the `glass` render role; the host solids are unchanged (still single manifold solids).

**Acceptance Scenarios**:

1. **Given** the default hull, **When** built, **Then** each porthole recess has a translucent circular glass pane (one per porthole) seated at the recess, and the hull solid is still a single manifold solid.
2. **Given** the standard deck, **When** built, **Then** each cabin-trunk side-window recess has a translucent rectangular pane.
3. **Given** the DS deck, **When** built, **Then** each deckhouse side-window recess has a translucent rectangular pane.
4. **Given** render attributes enabled, **When** built, **Then** every pane resolves to the palette `glass` role (translucent); with render attributes off, panes build with no colour.

---

### User Story 2 — Panes are opt-out and never break the host (Priority: P2)

Glass panes are on by default but can be disabled per call, and disabling/enabling them never alters the host hull/trunk/deckhouse geometry or its STL.

**Why this priority**: Back-compat + the manifold guarantee. Lower than P1 because the panes themselves are the headline.

**Independent Test**: Build with panes off → no pane bodies, host solids identical to panes-on; build with panes on → pane bodies present, host solids identical. STL export of the host succeeds in both.

**Acceptance Scenarios**:

1. **Given** glass panes disabled, **When** built, **Then** no pane bodies are added and the hull/trunk/deckhouse solids are byte-identical to the panes-on host geometry.
2. **Given** any pane configuration, **When** the host solids are exported to STL, **Then** export succeeds (panes never break the host mesh).
3. **Given** `count_per_side=0` on a window set, **When** built, **Then** no recesses and no panes (nothing to glaze).

---

### Edge Cases

- Zero windows/portholes on a side → zero panes (no degenerate bodies).
- A pane must sit within its recess footprint and not protrude through the host solid (it is thinner than the recess depth and inset to the recess).
- DS variant: deckhouse window panes exist; standard variant: cabin-trunk window panes exist; neither builds the other's panes.
- Reproducibility: identical inputs → identical pane geometry, byte-identical exports.
- A mid-build failure rolls back panes added so far along with the rest, exactly as the host builders already do.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each porthole recess MUST get one translucent circular glass-pane body seated at the recess, of the porthole diameter, when hull glazing is enabled.
- **FR-002**: Each cabin-trunk side-window recess MUST get one translucent rectangular glass-pane body seated at the recess, when deck glazing is enabled (standard variant).
- **FR-003**: Each DS deckhouse side-window recess MUST get one translucent rectangular glass-pane body, when the DS variant is built with windows.
- **FR-004**: Every glass pane MUST be an additive body (no boolean on the host solid) and MUST be a single valid solid (`Solids == 1`, `isValid()`).
- **FR-005**: The host hull, cabin trunk, and deckhouse solids MUST remain single manifold solids whose STL export succeeds, unchanged by the presence of panes.
- **FR-006**: Each pane MUST be inset within its recess (thinner than the recess depth, positioned at the recess) so it does not protrude through the host solid.
- **FR-007**: Glass panes MUST build by default where the host glazing is enabled, with a per-call opt-out; with render attributes enabled each pane MUST resolve to the palette `glass` role; with render attributes disabled panes build without colour.
- **FR-008**: Rounded window-corner geometry is OUT OF SCOPE (deferred; Sketcher-fillet non-watertight risk per spec 018). Panes are rectangular (windows) or circular (portholes).
- **FR-009**: Builds MUST stay reproducible (identical inputs → identical pane geometry, no timestamps).
- **FR-010**: A mid-build FreeCAD failure MUST roll back panes with the rest of the host build and surface as the host module's construction error.

### Key Entities *(include if data)*

- **Glass pane**: A thin translucent additive body (disc for portholes, slab for windows) seated in a recess, carrying the palette `glass` role. One per recess.
- **Pane set wrappers**: Aggregates exposing the panes built per host (porthole panes on the hull glazing result; cabin-window panes and deckhouse-window panes on the deck result).

## Success Criteria *(mandatory)*

- **SC-001**: With defaults, the hull has one translucent pane per porthole, the standard deck one per cabin window, the DS deck one per deckhouse window.
- **SC-002**: Host hull/trunk/deckhouse solids stay single manifold solids and export to STL with panes on and off.
- **SC-003**: Every pane is a single valid solid resolving to the `glass` render role when render attributes are enabled.
- **SC-004**: Panes are reproducible and opt-out; disabling them leaves the host geometry identical.

## Assumptions

- Panes are additive bodies in the host's document; they do not modify the host solids (the manifold guarantee comes for free).
- Rounded corners and per-pane mullions stay deferred (non-watertight fillet risk; future PATCH).
- The `glass` palette role (spec 015) and the windshield glass-pane pattern (spec 011) are reused; no new render role.
- Additive public-API surface (pane wrappers + opt-out kwargs) → MINOR bump.
