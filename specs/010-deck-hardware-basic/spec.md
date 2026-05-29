# Feature Specification: Basic Deck Hardware

**Feature Branch**: `010-deck-hardware-basic`

**Created**: 2026-05-29

**Status**: Draft

**Input**: User description: "Add basic deck hardware to the Storebro deck superstructure built by storebro.deck.build_deck: rubrail, bow pulpit, lifelines, anchor locker, basic cleats. Follow the spec 008 deck module idiom; PartDesign bodies, parameter dataclasses, seated on actual hull/deck geometry; PATCH bump 1.0.3 -> 1.0.4 with sensible RC34 1972 defaults so existing build_deck() callers get the hardware automatically."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rubrail along the sheer (Priority: P1)

A restorer or scale modeler builds the default Storebro deck and immediately recognizes the boat as a vintage Storebro because a wooden rubrail runs the length of the sheer on both port and starboard sides. The rubrail is the single most identifying visual detail on these yachts; without it the hull reads as a generic motor boat.

**Why this priority**: The rubrail delivers the largest perceptual return of any item in this spec for the least geometric cost. It is the headline "Storebro tell." If only this ships, the model already looks markedly more authentic.

**Independent Test**: Call `build_deck(build_hull())` and confirm a `Rubrail` body (port + starboard) exists in the document, hugs the actual sheer line at every longitudinal station (sourced from the real deck/hull geometry, not an analytical formula), and runs from near the bow to near the transom on both sides symmetrically.

**Acceptance Scenarios**:

1. **Given** a freshly built hull, **When** `build_deck` runs with default parameters, **Then** the returned `Deck` aggregate exposes a rubrail wrapper whose body's bounding box spans the majority of the hull LOA and sits at the sheer height on both sides.
2. **Given** custom `RubrailParameters` (e.g. a taller strip), **When** `build_deck` runs, **Then** the rubrail height/thickness match the supplied values within tolerance and the strip still follows the sheer.
3. **Given** a hull whose sheer was changed (different sheer heights fore/aft), **When** `build_deck` runs, **Then** the rubrail re-seats on the new sheer line — it is not pinned to a hard-coded Z.

---

### User Story 2 - Bow furniture: pulpit and anchor locker (Priority: P2)

The same user looks at the foredeck and sees a tubular bow pulpit wrapping the stem and a recessed anchor locker hatch just aft of it — the working end of the boat reads correctly.

**Why this priority**: Bow furniture is the second-strongest visual cue after the rubrail and frames the foredeck. It depends only on the hull/deck forward geometry, so it can be developed independently of the railing-dependent lifelines.

**Independent Test**: Build the default deck; confirm a `BowPulpit` tubular body sits forward of the cabin trunk at the bow, rising to a guard-rail height, and an `AnchorLocker` body sits on the foredeck near the bow within the deck footprint.

**Acceptance Scenarios**:

1. **Given** default parameters, **When** `build_deck` runs, **Then** a bow pulpit body of tubular (small-diameter) cross-section exists at the forward end, symmetric about the centerline, with its top at the configured guard-rail height above the deck.
2. **Given** default parameters, **When** `build_deck` runs, **Then** an anchor locker body sits on the foredeck near the bow, fully within the deck plate footprint (does not overhang the sheer), forward of the cabin trunk.
3. **Given** an anchor locker positioned too far aft (overlapping the cabin trunk) or too far forward (past the deck edge), **When** parameters are validated, **Then** construction is rejected before any FreeCAD call with a clear parameter error.

---

### User Story 3 - Lifelines and cleats (Priority: P3)

The user sees lifelines strung between the existing railing stanchions and mooring cleats placed along the sheer, completing the deck-hardware silhouette.

**Why this priority**: Lifelines depend on the spec 008 railing post positions, and cleats are the smallest individual detail, so this story is naturally last. It still adds recognizable realism but is the lowest perceptual return per item.

**Independent Test**: Build the default deck; confirm lifeline tube(s) run horizontally between the railing posts at the configured height(s) on both sides, and a set of cleats sits along the sheer at the configured stations.

**Acceptance Scenarios**:

1. **Given** the default railing (6 posts per side from spec 008), **When** `build_deck` runs, **Then** lifeline tubes connect the posts on each side at the configured height(s) and do not float free of the posts.
2. **Given** a railing configured with zero posts per side, **When** `build_deck` runs, **Then** lifelines degrade gracefully (no lifelines built, no error) — they have nothing to attach to.
3. **Given** default parameters, **When** `build_deck` runs, **Then** a configurable number of cleats (default a small even count) sits along the sheer, symmetric port/starboard, each seated on the actual deck top.

---

### Edge Cases

- **Zero-count hardware**: a parameter set requesting zero cleats, zero lifelines, or zero bow-pulpit stanchions builds that item as empty (or omits it) without raising, mirroring the spec 008 zero-pillar fallback.
- **Hardware vs. superstructure collision**: an anchor locker whose footprint overlaps the cabin trunk, or a rubrail strip taller than the freeboard, is rejected at parameter validation with a `DeckParameterError` naming the offending field.
- **Lifelines with no railing**: when the railing has zero posts, lifelines have no anchors — they are skipped, not errored.
- **Both parameter forms passed**: passing both the legacy parameter form and the new hardware composite where they conflict is rejected before any FreeCAD call (consistent with the existing mutually-exclusive legacy-vs-composite rule).
- **Partial build failure**: if any single hardware body fails to construct in FreeCAD, the whole `build_deck` call rolls back every body it added (including the six superstructure bodies), restoring the document to its pre-call state.
- **Degenerate sheer at the stem**: hardware that runs to the bow (rubrail, bow pulpit) must cope with the sheer collapsing toward the stem vertex without producing a self-intersecting or null shape.
- **Reproducibility**: two builds with identical parameters produce byte-identical geometry — no timestamps, randomness, or environment-dependent values enter any hardware shape.

## Clarifications

### Session 2026-05-29

- Q: How should the rubrail be constructed so it follows the sheer? → A: Loft (Ruled=True) between per-station cross-section sketches placed at the sampled sheer points — mirrors the deck-plate / hull AdditiveLoft idiom and avoids the swept-pipe-along-perimeter fragility that spec 008 explicitly deferred for the railing top rail.
- Q: Anchor locker — recessed boolean cut into the deck plate, or a raised additive box/hatch? → A: A raised low box / hatch built as its own additive `PartDesign::Body`. A boolean subtract into the deck plate risks the non-manifold tessellation that broke STL export for spec 009's bilge arc; "basic" hardware needs a recognizable hatch, not a functional cavity.
- Q: How many lifelines per side by default? → A: A single upper lifeline (configurable count), strung between the existing railing posts at a fraction of the railing height. The reference shows predominantly one line plus the existing top rail.
- Q: API surface for the new hardware parameters? → A: A new, separate optional composite `DeckHardwareParameters` passed through a new `parameters_hardware` keyword argument on `build_deck`, orthogonal to the spec 008 `DeckSuperstructureParameters`. Keeps the superstructure composite unchanged and the change purely additive.
- Q: Default cleat layout? → A: 4 cleats total by default — two forward, two aft — placed at two longitudinal stations and mirrored port/starboard (2 stations × 2 sides). Count and stations are configurable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The deck builder MUST add five new classes of deck hardware to its output: a rubrail, a bow pulpit, lifelines, an anchor locker, and cleats.
- **FR-002**: Each hardware class MUST be constructed FreeCAD-idiomatically as a `PartDesign::Body` (or a `Part::Compound` of such bodies for multi-instance items like cleats), consistent with the spec 008 superstructure idiom — datum planes, sketches, and Pad/Loft/Sweep features. No raw mesh generation.
- **FR-003**: Each hardware class MUST have its own frozen parameter dataclass with millimeter lengths, degree angles, and `__post_init__` validation that raises `DeckParameterError` (naming the offending field and valid range) for out-of-range inputs — matching the existing deck parameter dataclasses.
- **FR-004**: All hardware that sits on the sheer or deck (rubrail, cleats, bow pulpit base, anchor locker) MUST be seated on the ACTUAL hull/deck geometry via the existing sheer-sampling and deck-top resolution helpers, NOT via re-derived analytical sheer formulas.
- **FR-005**: The rubrail MUST run along the sheer line on both port and starboard sides, symmetric about the centerline, spanning the configured longitudinal extent (defaulting to near-bow through near-transom). It MUST be constructed as an `AdditiveLoft` (Ruled=True) between per-station cross-section sketches placed at the sampled sheer points, NOT as a swept pipe along a perimeter wire.
- **FR-006**: The bow pulpit MUST be a tubular guard rail at the bow forward of the cabin trunk, symmetric about the centerline, rising to a configured guard-rail height above the deck.
- **FR-007**: The lifelines MUST run horizontally between the existing railing stanchions (the spec 008 railing posts) on both sides; the number of lines per side is configurable and defaults to a single upper lifeline at a configured fraction of the railing height.
- **FR-008**: The anchor locker MUST sit on the foredeck near the bow as a raised additive box/hatch body (NOT a boolean recess into the deck plate), fully within the deck plate footprint and forward of the cabin trunk.
- **FR-009**: The cleats MUST be placed along the sheer at configured longitudinal stations, symmetric port/starboard, each seated on the actual deck top; the default layout is 4 cleats (two forward, two aft = 2 stations × 2 sides).
- **FR-010**: New hardware MUST be exposed on the `build_deck` return aggregate so callers can access each hardware body, consistent with how the six superstructure sub-bodies are exposed.
- **FR-011**: Hardware MUST be built by default — an existing caller invoking `build_deck` with no new arguments receives the hardware automatically, parameterized with RC34 1972 reference defaults.
- **FR-012**: A new, separate optional composite `DeckHardwareParameters` (orthogonal to the spec 008 `DeckSuperstructureParameters`) MUST let callers override hardware parameters, passed through a new `parameters_hardware` keyword argument on `build_deck`; the existing mutually-exclusive legacy-vs-composite parameter handling MUST be preserved.
- **FR-013**: On any FreeCAD-side failure during hardware construction, `build_deck` MUST roll back every body it added (superstructure + hardware) and restore the document to its pre-call state, consistent with the existing rollback discipline.
- **FR-014**: Hardware geometry MUST be reproducible: identical parameters produce byte-identical output, with no timestamps, randomness, or environment-dependent values in any shape.
- **FR-015**: Hardware principal dimensions MUST match the `docs/references/Alternativ3.JPG` RC34 1972 reference within ±1% (per constitution principle IV); per-instance fine detail (individual tube fillets, cleat horn curvature) is exempt from the ±1% bar.
- **FR-016**: Zero-count hardware (zero cleats, zero lifelines, zero bow-pulpit stanchions, zero rubrail extent) MUST build empty / be omitted without raising, mirroring the spec 008 zero-pillar fallback.
- **FR-017**: Lifelines MUST degrade gracefully when the railing has zero posts (no anchors): they are skipped, not errored.
- **FR-018**: Cross-component collisions that are geometrically invalid (anchor locker overlapping the cabin trunk, rubrail taller than the available freeboard, hardware extending past the deck/hull edge) MUST be rejected at parameter validation before any FreeCAD call.
- **FR-019**: The public API change MUST be additive only — no existing public name is removed or has its signature broken. The version is bumped PATCH (1.0.3 → 1.0.4), and the `storebro.__version__` dunder MUST be corrected to match `pyproject.toml`.
- **FR-020**: The deck module MUST NOT acquire new cross-module imports beyond those it already has (it imports `storebro.hull` and `storebro._freecad_check` only); it MUST NOT import `export`, `interior`, or `cli`.

### Key Entities

- **Rubrail**: A wooden strip running along the sheer on both sides. Principal attributes: vertical height, outboard thickness/protrusion, longitudinal start/end stations, cross-section profile. Seated on the sampled sheer line.
- **Bow Pulpit**: A tubular guard rail at the bow. Principal attributes: tube diameter, guard-rail height above deck, forward extent past the deck edge, stanchion count/positions, symmetry about centerline.
- **Lifelines**: Horizontal tube runs strung between railing posts. Principal attributes: tube diameter, number of lines and their heights, dependency on the railing post stations.
- **Anchor Locker**: A recessed hatch/box on the foredeck near the bow. Principal attributes: length, width, height (or recess depth), longitudinal position from the bow, must fit within the deck footprint forward of the cabin trunk.
- **Cleats**: Mooring cleats along the sheer. Principal attributes: cleat length, height, count, longitudinal stations, port/starboard symmetry, seated on the actual deck top.
- **Deck Hardware Composite**: The new optional parameter aggregate bundling the five hardware parameter dataclasses, analogous to the spec 008 superstructure composite.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A default `build_deck(build_hull())` produces all five hardware classes in addition to the existing six superstructure bodies, with zero new errors and no regression in existing deck tests.
- **SC-002**: The rubrail follows the sampled sheer line such that its vertical position at each longitudinal station matches the actual deck-top sheer within the project tolerance (≤1% of the local sheer height).
- **SC-003**: Hardware principal dimensions match the Alternativ3.JPG reference within ±1% on every principal dimension recorded in the parameter defaults.
- **SC-004**: Two consecutive builds with identical parameters produce byte-identical exported geometry (reproducibility holds for the new hardware).
- **SC-005**: Every new parameter dataclass rejects out-of-range input with a `DeckParameterError` naming the field, verified by unit tests covering each validation branch.
- **SC-006**: A mid-build failure in any hardware body leaves the document in its exact pre-call state (rollback verified by test).
- **SC-007**: Existing `build_deck` callers that pass no new arguments continue to succeed and now receive hardware automatically (back-compat verified).
- **SC-008**: The full test suite (`uv run pytest`), `ruff check`, and `mypy --strict` all pass; the model opens and visually verifies in FreeCAD against the reference photo.

## Assumptions

- **Rubrail cross-section**: Modeled as a simple rectangular (or D-ish) strip lofted between per-station cross-section sketches at the sampled sheer points (per FR-005); an authentic moulded teak profile with a chromed insert is out of scope for "basic" hardware and deferred to a later spec.
- **Bow pulpit fidelity**: Modeled as straight tubular segments (pads/sweeps of small-diameter circles) approximating the pulpit loop; true bent-tube radii and welded joints are out of scope, consistent with how spec 008 approximated the railing top rail.
- **Lifelines**: Modeled as straight horizontal tubes between posts (not catenary-sagging wire). One or two lines depending on the default; reference suggests a single upper lifeline plus the existing top rail.
- **Anchor locker**: Modeled as a low box / raised hatch on the foredeck rather than a true boolean recess into the deck plate, unless a recess proves trivial; "basic" implies a recognizable hatch, not a functional locker cavity.
- **Cleats**: Modeled as simple horn-cleat proxies (a base pad plus a horizontal bar) rather than precisely contoured castings; count defaults to a small even number (e.g. 4: two bow, two stern) symmetric port/starboard.
- **Materials/colors**: Setting render colors/materials (teak-brown rubrail, chromed pulpit) is explicitly out of scope here — that is spec 015 (render-attributes). This spec produces geometry only.
- **Reference source**: `docs/references/Alternativ3.JPG` is the dimensional reference, consistent with specs 007–009; where the photo is ambiguous, estimate-grade defaults are used and documented, refinable in later PATCH bumps.
- **Hardware-on-by-default behavior change**: Existing tests that assert an exact body count in the document will need updating; this is an expected, additive change, not a breaking public-API change.
- **Dependency on spec 008**: Lifelines depend on the existing `RailingParameters` post stations; the railing must be built before lifelines in the build order.
