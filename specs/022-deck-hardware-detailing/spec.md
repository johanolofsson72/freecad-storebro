# Feature Specification: Deck Hardware Detailing

**Feature Branch**: `022-deck-hardware-detailing`

**Created**: 2026-06-02

**Status**: Draft

**Input**: User description: "Detail the spec 010 deck hardware (currently straight-tube/box placeholders) to a contoured, foundry-faithful level — moulded teak rubrail profile with chrome insert, bent-tube bow-pulpit radii + welded joints, lifeline catenary sag, contoured cleat castings, and a functional recessed anchor-locker cavity — without booleaning the hull and without introducing non-manifold STL."

## Clarifications

### Session 2026-06-02

- Q: What moulded cross-section should the rubrail outboard face use? → A: The **default is a chamfered** (straight-line) outboard face — it is byte-reproducible under cumulative FreeCAD state (constitution II). The **rounded** (Sketcher-arc) face is exposed as an explicit opt-in (`rounded_profile=True`, guarded by a manifold-or-fallback gate to the chamfer), but is NOT the default because the arc loft's volume drifts under accumulated OCC tessellation state (the spec 018 arc-instability wall). **Implementation finding: the user promoted the rounded fillet to in-scope, but constitution II (non-negotiable byte-reproducibility) forces it to be opt-in rather than default.**
- Q: How does the chrome insert relate to the teak rubrail? → A: A separate thin strip body running flush along the rubrail outboard face — no groove is cut into the teak (keeps both bodies single manifold solids by construction).
- Q: How is the bent-tube bow pulpit constructed? → A: A single `PartDesign::AdditivePipe` sweep along a wire path whose corners are arc-filleted, PLUS a small torus weld-bead body at each joint (chrome role), with a manifold-or-fallback gate reverting to the spec 010 straight cylinders on sweep failure. (User promoted the weld beads from deferred to in-scope.)
- Q: What curve shape models the lifeline sag? → A: A **true catenary** (hyperbolic-cosine) curve sampled into a B-spline sweep path, with the sag depth controlling the catenary parameter; falls back to the straight tube on sweep failure. (User promoted the true catenary from deferred to in-scope.)
- Q: How is the contoured cleat casting built? → A: A `Ruled=True` lofted tapered base (larger bottom footprint → smaller top footprint) plus swept-arc curved horns, fused into a single manifold `PartDesign` body per cleat.
- Q: Does the anchor locker get a separate lid? → A: Yes — in addition to the recessed cavity, emit a **separate lid body** seated over the cavity (its own `PartDesign::Body`, teak render role). (User promoted the lid from deferred to in-scope.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Moulded rubrail with chrome insert (Priority: P1)

A restorer building the RC34 model wants the rubrail to read as the moulded teak sheer strip with its chrome rubbing insert — the single most identifying detail on a vintage Storebro — not a plain rectangular bar.

**Why this priority**: The rubrail is the headline Storebro tell (spec 010 rationale). Upgrading its cross-section from a flat rectangle to a moulded profile plus a chrome insert strip is the highest perceptual return of the five refinements.

**Independent Test**: Build the deck with default hardware; the rubrail compound contains the port + starboard moulded teak bodies AND a separate chrome insert body, each a single valid solid; the insert resolves to the chrome render role.

**Acceptance Scenarios**:

1. **Given** a built deck with default hardware, **When** the rubrail is built, **Then** each side body is a single valid solid whose cross-section is the moulded profile (rounded outboard face, not a plain rectangle) and a separate chrome insert body runs the rubrail length.
2. **Given** `RubrailParameters` with the chrome insert disabled, **When** the rubrail is built, **Then** the teak bodies still build and no chrome insert body is emitted.
3. **Given** the rubrail bodies, **When** STL is exported, **Then** every body tessellates as a watertight manifold mesh.
4. **Given** a rounded-profile loft that fails to produce a single valid solid, **When** the rubrail is built, **Then** it falls back to the chamfered straight-line profile and still emits valid side bodies.

---

### User Story 2 - Bent-tube bow pulpit with welded joints (Priority: P2)

The bow pulpit should read as a single bent stainless tube with radiused corners and welded joints, not three disconnected straight cylinders meeting at hard right angles.

**Why this priority**: The pulpit is a prominent bow silhouette element; the spec 010 straight-cylinder placeholder reads as obviously synthetic. Radiused bends are the fix.

**Independent Test**: Build the pulpit with default hardware; the tube path has radiused corners (the joint regions are filled, not gapped), and the body is a single valid solid; if the swept path fails, the build falls back to the spec 010 straight tubes and still produces a valid body.

**Acceptance Scenarios**:

1. **Given** a built deck with default hardware, **When** the bow pulpit is built, **Then** the result is a single valid solid whose corners are radiused (welded joints filled) rather than abutting straight cylinders, with a torus weld-bead body at each joint (chrome role).
2. **Given** a degenerate or failing swept path, **When** the bow pulpit is built, **Then** the build falls back to the spec 010 straight-tube construction and still emits a valid body (FR-FALLBACK).
3. **Given** `bow_pulpit.stanchion_count == 0`, **When** the pulpit is built, **Then** an empty-footprint body is produced (preserves spec 010 FR-016).

---

### User Story 3 - Lifeline catenary sag (Priority: P3)

The lifelines between the railing posts should sag gently under their own weight (catenary), as real wire lifelines do, instead of being perfectly straight rigid tubes.

**Why this priority**: Subtle realism touch; lowest perceptual return but cheap once the swept-path infrastructure exists from US2.

**Independent Test**: Build lifelines with a non-zero sag depth; the tube's mid-span Z dips below its end-Z by approximately the sag depth; zero sag (or swept-path failure) reproduces the spec 010 straight tube.

**Acceptance Scenarios**:

1. **Given** `lifelines.sag_depth > 0`, **When** the lifeline is built, **Then** the tube follows a true catenary whose mid-span Z is lower than the endpoint Z by approximately `sag_depth`, and the body is a single valid solid.
2. **Given** `lifelines.sag_depth == 0`, **When** the lifeline is built, **Then** the tube is straight (reproduces spec 010 exactly).
3. **Given** a swept-path failure, **When** the lifeline is built, **Then** the build falls back to the straight tube and still emits a valid body.

---

### User Story 4 - Contoured cleat castings (Priority: P3)

Each mooring cleat should read as a contoured casting — a tapered/filleted base with curved horns — rather than a box with a straight cylinder on top.

**Why this priority**: Cleats are small and repeated; contouring them lifts close-up fidelity but is low whole-boat impact.

**Independent Test**: Build cleats with default hardware; each cleat body is a single valid solid whose base is tapered (top footprint smaller than bottom) and whose horns are curved; the cleat count is unchanged from spec 010.

**Acceptance Scenarios**:

1. **Given** default cleat hardware, **When** cleats are built, **Then** each cleat is a single valid solid with a tapered base (top cross-section area < base cross-section area) and curved horns.
2. **Given** the same `count_per_station`/`station_count`, **When** cleats are built, **Then** the total cleat count equals the spec 010 count (`count_per_station * station_count * 2`).
3. **Given** zero cleat counts, **When** cleats are built, **Then** an empty compound is produced (preserves spec 010 FR-016).

---

### User Story 5 - Functional recessed anchor-locker cavity (Priority: P3)

The anchor locker should read as an openable locker with a recessed cavity in its top, not a solid raised box.

**Why this priority**: Turns a featureless box into a recognizable functional fitting; self-contained, no interaction with hull/deck.

**Independent Test**: Build the anchor locker with default hardware; the locker body has a blind cavity recessed into its top (the body is hollowed at the top but remains a single valid solid); the cavity is a pocket on the locker body only — the hull and deck are never booleaned.

**Acceptance Scenarios**:

1. **Given** default anchor-locker hardware, **When** the locker is built, **Then** the body has a blind recessed cavity in its top face and remains a single valid solid (`Solids == 1`, `isValid()`), and a separate lid body is emitted seated over the cavity.
2. **Given** `anchor_locker.cavity_depth == 0` (or cavity disabled), **When** the locker is built, **Then** the locker reproduces the spec 010 solid raised box and no lid body is emitted.
3. **Given** the built locker, **When** the hull and deck shapes are inspected, **Then** they are byte-for-byte unchanged versus a build with the locker absent (the cavity never touches hull/deck — FR-NOBOOL).

---

### Edge Cases

- What happens when a moulded-profile sketch degenerates (e.g. fillet radius ≥ half the rubrail dimension)? → parameter validation rejects it before construction (`DeckParameterError`).
- How does the system handle a swept AdditivePipe path that FreeCAD cannot loft (self-intersection, degenerate tangent)? → manifold-or-fallback gate reverts that item to its spec 010 construction and logs nothing in artifacts (reproducible).
- What happens when the chrome insert thickness exceeds the teak rubrail it sits in? → validation rejects (insert must fit within the rubrail envelope).
- What happens when the anchor-locker cavity depth ≥ the locker height? → validation rejects (cavity must leave a floor).
- What happens to STL manifold-ness at the high default station/curl densities? → every produced body asserts `Solids == 1 && isValid()`; any item that would break manifold-ness falls back.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The rubrail cross-section MUST be a moulded profile instead of a plain rectangle, lofted `Ruled=True` between the sampled sheer stations on both port and starboard sides. The **default** profile is **chamfered** (straight-line, byte-reproducible per constitution II). A **rounded** (Sketcher-arc) profile is available as an opt-in (`rounded_profile`), guarded by a manifold-or-fallback gate to the chamfer; it is not the default because the arc loft is not byte-reproducible under cumulative FreeCAD state (spec 018 arc-instability evidence).
- **FR-002**: The rubrail MUST carry a separate thin chrome insert strip as its own `PartDesign::Body`, running the rubrail length, resolvable to a chrome render role; the insert MUST be omittable via a parameter (teak-only fallback).
- **FR-003**: The bow pulpit MUST have radiused bends at its tube corners (welded-joint reading) rather than abutting straight cylinders, built as a swept additive tube where feasible, PLUS a small torus weld-bead body at each tube joint (chrome render role).
- **FR-004**: The lifelines MUST sag in a **true catenary** (hyperbolic-cosine) curve between the railing posts, sampled into a swept B-spline path, with the sag depth a validated parameter controlling the catenary; zero sag reproduces the spec 010 straight tube.
- **FR-005**: Each cleat MUST be a contoured casting (tapered/filleted base, curved horns) and remain a single valid manifold solid.
- **FR-006**: The anchor locker MUST have a functional recessed cavity in its top, built as a blind `PartDesign::Pocket` on the locker body only; the cavity MUST leave a floor (depth < height) and keep the body a single valid solid. The locker MUST also emit a **separate lid body** seated over the cavity (its own `PartDesign::Body`, teak render role) — omittable via parameter.
- **FR-007** (NOBOOL): No refinement may boolean the hull or deck plate solids. The hull and deck shapes MUST be identical whether or not the hardware refinements run. Hardware sits as additive bodies seated on sampled geometry.
- **FR-008** (FALLBACK): Every refinement that uses a swept/lofted path (bow pulpit, lifelines) MUST have a manifold-or-fallback gate: if the refined construction fails to produce a single valid solid, the build reverts that item to its spec 010 construction and still emits a valid body.
- **FR-009** (MANIFOLD): Every body produced or modified by this spec MUST satisfy `Shape.Solids == 1` and `Shape.isValid()` so STL export stays watertight (specs 009/011/018 discipline).
- **FR-010**: All new shape-controlling fields MUST be added additively to the existing `RubrailParameters`, `BowPulpitParameters`, `LifelineParameters`, `CleatParameters`, and `AnchorLockerParameters` dataclasses, each defaulted so existing callers get the refined geometry automatically, each validated (raise `DeckParameterError` with the offending value and the valid range on invalid input).
- **FR-011**: No public API may be removed. All spec 010 public types, fields, wrappers, and the `build_deck(..., parameters_hardware=...)` entry point MUST keep working unchanged for existing callers.
- **FR-012**: The chrome insert role MUST be added to the render palette/role resolver so the insert colours as chrome under the spec 015 render attributes (and is omitted when render attributes are disabled).

### Key Entities

- **RubrailParameters**: gains moulded-profile controls (outboard-face fillet radius, with a chamfer fallback width) and chrome-insert controls (presence flag, insert thickness/height, inset).
- **BowPulpitParameters**: gains a bend-radius control for the radiused corners and a weld-bead radius control.
- **LifelineParameters**: gains a `sag_depth` control (catenary depth).
- **CleatParameters**: gains base-taper / horn-curvature controls.
- **AnchorLockerParameters**: gains cavity controls (depth, wall thickness / inset) and lid controls (presence flag, lid thickness).
- **Chrome insert body**: a new thin additive body parallel to the rubrail, render role = chrome.
- **Weld-bead bodies**: small torus bodies at each bow-pulpit joint, render role = chrome.
- **Locker lid body**: a separate additive slab seated over the locker cavity, render role = teak.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Building the deck with default hardware produces, for every refined item, a body with exactly one solid that passes `isValid()` (100% manifold rate across rubrail teak bodies, chrome insert, bow pulpit, every lifeline, every cleat, and the anchor locker).
- **SC-002**: The hull and deck-plate shapes are identical (same volume, same vertex count) whether the hardware refinements run or not — zero hull/deck mutation.
- **SC-003**: STL export of the full deck (hull + superstructure + refined hardware) succeeds and yields a watertight mesh (no naked edges on the hardware bodies).
- **SC-004**: Every existing spec 010 caller (default `build_deck`, explicit `parameters_hardware`, zero-count fallbacks) continues to build without code changes — 100% back-compatibility.
- **SC-005**: Each swept refinement (bow pulpit, lifelines) demonstrably falls back to its spec 010 construction when its path is forced to fail, still yielding a valid body.

## Assumptions

- The build runs on FreeCAD 1.1.1; `PartDesign::AdditivePipe` (sweep) and `PartDesign::Pocket` behave as in specs 011/016/020.
- "Foundry-faithful" means a recognizable contoured silhouette at model-viewing distance, not a CAD-accurate casting — within constitution principle IV's ±1% reference fidelity on principal dimensions, visual-only on fine contour.
- Render attributes (spec 015) are the colour source; this spec only adds the chrome-insert role mapping, it does not change how render attributes are applied.
- Default densities (station sampling, curl sections) are inherited from the existing hardware builders; no new global density knob is introduced.
- The reference for silhouette is `docs/references/Alternativ3.JPG` and the storebro reference set; exact casting geometry is not available, so cleat/pulpit contours are reasonable approximations.
- This is a light-track cosmetic/detailing refinement: single synchronous build, no new state machine, no concurrency — `/tla` is expected to be skipped per the triviality gate.
