# Feature Specification: Superstructure Curvature Refinement

**Feature Branch**: `020-superstructure-curvature-refinement` | **Created**: 2026-06-02 | **Status**: Draft

**Input**: Roadmap 020 — close the spec 008 geometry-equivalence deferrals: a smooth hardtop leading-edge curl, a crowned (arched) windshield top, and a swept perimeter top-rail. A FreeCAD spike proved all three feasible without `Ruled=False`: dense `Ruled=True` lofts give the curl/crown 0 mm overshoot, and `makePipeShell` sweeps the rail into a valid single solid.

## Context

Spec 008 shipped working but faceted superstructure: the hardtop curl is a 3-section `Ruled=True` loft (a single drop, not a smooth curve), the windshield top is straight, and the railing top-rail is a straight cylinder per side. The smoother variants were deferred because `Ruled=False` overshoots (the same wall spec 018 proved fundamental). This spec delivers the smooth versions with the spike-proven manifold-safe techniques: **dense `Ruled=True`** (more sections tracing a cosine curve) for the curl and crown, and **`makePipeShell`** for the swept rail. No `Ruled=False`.

## Clarifications

### Session 2026-06-02

- Q: How is the smooth hardtop curl achieved given `Ruled=False` overshoots? → A: A dense `Ruled=True` loft — the forward `curl_sections` station sketches trace a cosine drop over the curl length, so the curl reads as a smooth curve with 0 mm Z-overshoot (spike-confirmed at n=3/7/13). Not `Ruled=False`.
- Q: The windshield crown? → A: **DEFERRED during implementation.** Discovery: the windshield loft is *already* `Ruled=False` (B-spline smooth) in the rake direction, so it already reads smooth. A transverse "crown" (arched top edge) requires non-rectangular section sketches, which would ripple into the spec 011 frame-opening pocket and glass pane (working, well-tested) at high regression risk for the lowest-priority sub-feature. The crown is split into a focused follow-on; this spec ships the two P1 refinements (hardtop curl + swept rail). FR-006/FR-007 are marked deferred below.
- Q: The swept perimeter top-rail? → A: A `makePipeShell` sweep of a circular profile along the closed perimeter wire (spike-confirmed valid single solid), replacing the straight per-side cylinders.
- Q: Default behavior / back-compat? → A: The smoother geometry becomes the default superstructure (an intended fidelity improvement, MINOR bump). Section counts are parameters with sensible defaults; setting `curl_sections`/`crown_sections` to their minimum reproduces the spec 008 faceted shape.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Smooth hardtop curl (Priority: P1)

The hardtop leading edge curls down as a smooth curve, not a single faceted drop.

**Independent Test**: Build the deck; the hardtop is a single manifold solid whose forward edge dips smoothly (monotone Z descent over the curl, no overshoot above the topside), with more faces than the spec 008 3-section curl.

**Acceptance Scenarios**:
1. **Given** defaults, **When** the deck builds, **Then** the hardtop is `Solids==1`+valid, its ZMax does not exceed the topside Z (0 overshoot), and its face count exceeds the old 3-section curl.
2. **Given** `curl_sections` at minimum, **When** built, **Then** the hardtop reproduces the spec 008 faceted curl.

---

### User Story 2 — Swept perimeter top-rail (Priority: P1)

The railing top-rail follows the deck perimeter as one swept tube, not straight per-side cylinders.

**Independent Test**: Build the deck; the swept top-rail is a single valid solid following the perimeter; the railing posts are unchanged.

**Acceptance Scenarios**:
1. **Given** defaults, **When** the deck builds, **Then** the swept top-rail is a valid solid (`makePipeShell`) running the perimeter, and STL export of the railing succeeds.
2. **Given** zero posts, **When** built, **Then** the railing behaves as spec 010 (no degenerate sweep).

---

### User Story 3 — Crowned windshield top (Priority: P2)

The windshield top edge arches gently (crown) instead of running straight.

**Independent Test**: Build the deck; the windshield is a single manifold solid whose top edge crowns (mid higher than the corners) within the validated range.

**Acceptance Scenarios**:
1. **Given** defaults, **When** the deck builds, **Then** the windshield is `Solids==1`+valid with a crowned top, and the glazing frame/pane (spec 011) still build.

---

### Edge Cases

- Section counts at minimum → faceted spec 008 shape (back-compat).
- The swept rail with a degenerate (zero-length) perimeter segment must not crash — fall back to the spec 010 straight rail if the sweep fails, never a broken body.
- All three refinements keep their host bodies single manifold solids that export to STL.
- Reproducibility: identical inputs → identical geometry.
- Mid-build failure rolls back per the existing `build_deck` semantics.

## Requirements *(mandatory)*

- **FR-001**: The hardtop leading-edge curl MUST be built as a dense `Ruled=True` loft whose forward sections trace a smooth (cosine) downward curve over the curl length; `Ruled=False` MUST NOT be used.
- **FR-002**: The hardtop MUST remain a single manifold solid (`Solids==1`, `isValid()`) with ZMax not exceeding the topside Z (0 overshoot) and MUST export to STL.
- **FR-003**: The number of curl sections MUST be a parameter with a default that reads smooth; its minimum MUST reproduce the spec 008 faceted curl.
- **FR-004**: The railing top-rail MUST be a `makePipeShell` sweep of a circular profile along the closed perimeter wire, producing a single valid solid; STL export MUST succeed.
- **FR-005**: If the swept rail fails to build a valid solid, the build MUST fall back to the spec 010 straight per-side rail (never a broken/empty body) and still succeed.
- **FR-006**: *(DEFERRED — see Clarifications.)* The windshield top crown is split into a follow-on spec: the windshield is already `Ruled=False`-smooth in rake, and a transverse arched top edge would endanger the spec 011 frame/pane. Out of scope here.
- **FR-007**: *(DEFERRED with FR-006.)*
- **FR-008**: All three refinements MUST be reproducible (identical inputs → identical geometry, no timestamps).
- **FR-009**: A mid-build FreeCAD failure MUST roll back via the existing `build_deck` rollback and surface as `DeckConstructionError`.
- **FR-010**: The smoother geometry MUST be the default; existing callers get it automatically (MINOR bump). Render roles (superstructure/metal) are unchanged.

## Key Entities

- **Curl section set**: The dense forward station sketches tracing the hardtop's cosine leading-edge curve.
- **Swept top-rail**: One `makePipeShell` solid following the perimeter wire, replacing the straight per-side cylinders.
- **Windshield crown**: The arched top edge produced by intermediate `Ruled=True` sections.

## Success Criteria

- **SC-001**: The default hardtop is a single manifold solid with a smooth curl (0 mm Z-overshoot, more faces than the 3-section curl) that exports to STL.
- **SC-002**: The default railing top-rail is a single valid `makePipeShell` solid following the perimeter; STL export succeeds; zero-post railings degrade gracefully.
- **SC-003**: The default windshield is a single manifold solid with a crowned top; the spec 011 frame + pane still build.
- **SC-004**: All three are reproducible; setting the section counts to minimum reproduces the spec 008 shapes (back-compat).

## Assumptions

- Smoothness comes from dense `Ruled=True` lofts + `makePipeShell`, never `Ruled=False` (spec 018 evidence); the spike confirmed 0 mm overshoot and valid swept solids.
- The swept rail has a manifold-or-fallback gate (fall back to the spec 010 straight rail), mirroring the spec 018 bilge-arc discipline.
- Additive/refinement change to existing builders; no new public modules. Section-count + crown parameters are additive fields with defaults → MINOR bump.
