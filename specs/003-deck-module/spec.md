# Feature Specification: Deck Module

**Feature Branch**: `003-deck-module`

**Created**: 2026-05-17

**Status**: Draft

**Input**: User description: "the deck module — deck plate, cabin trunk, windshield, hardtop, railings mounted on the hull from spec 001"

## Clarifications

### Session 2026-05-17

- Q: Should cabin trunk glazing (window cutouts, deadlights, portholes) be in v1.0 scope? → A: **No, defer to v1.1+**. v1.0 ships solid cabin trunk sides and a solid-face windshield; glazing arrives once the interior module (spec 004) exists to receive light, and once a separate `Glazing` Body keeps the cabin trunk shell deterministic on its own.
- Q: How is the hardtop supported above the cockpit? → A: **Two aft vertical support pillars**. The cabin trunk supports the forward portion of the hardtop; two symmetric vertical pillars (port + starboard) at the hardtop's aft edge support the cockpit-side overhang. Pillar diameter is a parameter with a default. This matches the Storebro Royal Cruiser 34 1972 silhouette.
- Q: How are cabin trunk corners styled? → A: **Rounded fillets with a documented radius parameter** (`cabin_trunk_corner_radius`, meters). Matches the RC34 1972 cabin corners (~50-100 mm typical radius). Sharp 90° corners would visibly diverge from period reference photography.
- Q: Is the deck plate a 3D solid with thickness, or a zero-thickness surface? → A: **3D solid with a documented `deck_plate_thickness` parameter** (default ~25 mm for fiberglass deck plate). A zero-thickness surface would render as a flickering knife-edge in any 3D viewer and would fail the STL watertight check from spec 002 SC-008. The 25 mm default is estimate-grade; refinable in PATCH bumps.
- Q: Should `DeckParameterError` / `DeckConstructionError` share a base class with the hull module's exceptions for cross-module catch idioms? → A: **No, independent classes**. Each public module owns its own exception taxonomy. `DeckParameterError(ValueError)` and `DeckConstructionError(RuntimeError)` are unrelated to spec 001's classes at the inheritance level. Callers wanting to catch "any storebro validation error" can `except ValueError`, which both subclass anyway — no extra coupling required.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - FreeCAD scripter mounts a deck onto a parametric Storebro hull (Priority: P1)

A FreeCAD scripter (the same Python user from spec 001's hull module) has built a hull via `build_hull()` and now wants to mount the complete superstructure on top: deck plate at the sheer line, cabin trunk forward, windshield raked aft, hardtop covering the cockpit, perimeter railings. They expect a single function call that takes the existing `Hull` and produces an editable deck composition in the same FreeCAD document — no re-deriving the sheer line from raw numbers, no manual placement of cabin elements, no fighting with FreeCAD's GUI to align the deck plate with the hull's top edge.

**Why this priority**: This is the foundational use case and the only one that exercises the cross-module dependency arrow (hull → deck) the project depends on. Without it the boat looks like a soup bowl; the entire visual signoff path (constitution V) for the canonical Storebro shape is blocked. The cabin/hardtop/railing chain also produces the most visually-recognizable Storebro silhouette — anything later that varies the look (interior layouts, render presets) only matters if the deck-as-seen-from-outside is right.

**Independent Test**: From a Python REPL with FreeCAD on PATH, run `from storebro import build_hull, build_deck; hull = build_hull(); deck = build_deck(hull); deck.document.saveAs("/tmp/whole_boat.FCStd")` and verify the resulting FreeCAD document opens with the hull plus six deck elements (deck plate, cabin trunk, windshield, hardtop, hardtop pillars, railings) all visible and parametrically editable.

**Acceptance Scenarios**:

1. **Given** a freshly-built default hull, **When** the scripter calls the deck builder with no other arguments, **Then** six parametric Bodies are added to the hull's FreeCAD document: `DeckPlate`, `CabinTrunk`, `Windshield`, `Hardtop`, `HardtopPillars`, `Railings` — each with named editable dimensions on its property panel.
2. **Given** a hull built into a user-supplied FreeCAD document containing other geometry (e.g., the user's custom hardware), **When** the deck builder runs, **Then** it adds its Bodies to that same document without modifying any pre-existing object.
3. **Given** the scripter exports the resulting document to `.FCStd` via spec 002's `export_fcstd`, **When** they reopen it in the FreeCAD GUI, **Then** all six deck Bodies are present, editable, and aligned with the hull's sheer line (no floating gaps, no clipping into the hull below the waterline).

---

### User Story 2 - Boat restorer renders the canonical Storebro silhouette (Priority: P2)

A boat restorer building a digital twin of a Storebro Royal Cruiser 34 (1972) wants the default deck-builder output to match the historical superstructure proportions — cabin trunk length and offset, windshield rake angle, hardtop overhang, railing height — within ±1% on principal dimensions, the same fidelity bar the hull module already meets. They render the result in any FreeCAD-compatible tool, hold it next to a period photograph, and the silhouette is recognizable.

**Why this priority**: Reference fidelity (constitution IV) is the project's identity. A geometrically-plausible-but-generic deck on top of a correctly-proportioned hull turns a Storebro into "a motor yacht". This story makes the v0.3.0-alpha checkpoint into "a Storebro".

**Independent Test**: Build a default hull, build a default deck on it, save to `.FCStd`, open in the FreeCAD GUI, overlay mentally against `docs/references/` photographs of an RC34 1972. The cabin trunk, hardtop, and railings are visually faithful within the documented tolerance. The PR description captures the signoff per constitution V.

**Acceptance Scenarios**:

1. **Given** the historical RC34 1972 reference dimensions, **When** the default deck is built on the default hull, **Then** the cabin trunk length, cabin trunk forward offset (from stem), hardtop length, and railing height each fall within ±1% of the reference values pinned in `/speckit-plan`.
2. **Given** the restorer holds a period photo next to the rendered model, **When** they compare the silhouette, **Then** the windshield rake angle, cabin trunk crown, and hardtop overhang qualitatively match — verified manually and recorded in the PR description per constitution V.

---

### User Story 3 - Naval architecture student studies superstructure parametrics (Priority: P3)

A naval architecture student wants to systematically vary individual deck parameters — extend the cabin trunk by 10%, raise the hardtop, steepen the windshield rake, shorten the railing — and study how each change affects the overall topside silhouette. They generate variant `.FCStd` files in a loop, name them by parameter, and compare them in their CAD tool of choice.

**Why this priority**: Parametricity (constitution I, SC-005 from spec 001) is the project's core promise. The hull module proved it for hull dimensions; the deck module proves it for superstructure dimensions and validates that the parametric chain composes correctly across modules.

**Independent Test**: For each named deck parameter, generate two decks differing only in that parameter (default vs. ±10%) on the same hull, and assert that the corresponding measured dimension of the resulting `Deck` differs in the expected direction.

**Acceptance Scenarios**:

1. **Given** two deck parameter sets differing only in `cabin_trunk_length`, **When** both decks are built on the same hull, **Then** the longer-cabin deck has a strictly longer `CabinTrunk` Body bounding-box length.
2. **Given** two parameter sets differing only in `hardtop_height`, **When** both decks are built, **Then** the taller-hardtop deck has a strictly higher `Hardtop` Body top-Z coordinate.
3. **Given** two parameter sets differing only in `railing_height`, **When** both decks are built, **Then** the taller-railing deck has a measurably greater `Railings` Body height extent.

---

### Edge Cases

- **`hull` is None or has an empty `.Shape`** (caller passed a Hull whose document was closed or whose body lost its shape via a botched recompute): builder MUST raise a typed error before any FreeCAD construction, naming the offending input.
- **Cabin trunk longer than the hull** (`cabin_trunk_length >= hull.parameters.loa`): geometrically the cabin would stick out past stem and transom; builder MUST raise a validation error before invoking FreeCAD.
- **Cabin trunk forward offset places the cabin past the bow** (`cabin_trunk_fwd_offset + cabin_trunk_length > hull.parameters.loa`): builder MUST raise a validation error.
- **Hardtop overhang larger than hardtop length** (`hardtop_overhang_fwd + hardtop_overhang_aft >= hardtop_length`): hardtop would collapse to a vertical line; builder MUST reject.
- **Negative or zero `railing_height`**: builder MUST raise a typed validation error.
- **Windshield rake angle outside `[0, 60]°`**: physically meaningful range; builder MUST reject values outside it.
- **Document mismatch**: caller supplies a `document` kwarg that is NOT the document containing `hull.body`. Builder MUST raise a typed error rather than silently add the deck to the wrong document or duplicate geometry across two documents.
- **Repeated invocation in the same document**: calling the deck builder twice on the same hull MUST add a second independent set of five Bodies (with FreeCAD's standard auto-numbering on labels), not silently mutate the first set.
- **FreeCAD construction failure during one element** (e.g., the windshield loft fails because of a parameter interaction that passed validation): builder MUST roll back any Bodies already added to the document, then raise a typed construction error wrapping the underlying failure. Partial decks in the document are worse than no deck at all.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The deck module MUST expose a single public deck-builder function that accepts a `Hull` (the return type from spec 001's `build_hull`) and optional named keyword arguments for each deck parameter, and returns a `Deck` aggregate containing six parametric Bodies: `DeckPlate`, `CabinTrunk`, `Windshield`, `Hardtop`, `HardtopPillars` (two aft support pillars per clarify Q2), `Railings`.
- **FR-002**: Every dimensional or angular deck parameter MUST be a named function argument with a documented default. Magic numbers inside function bodies are forbidden per constitution principle I.
- **FR-003**: Default values for principal deck dimensions (cabin trunk length, cabin trunk forward offset, hardtop length, hardtop height above deck, railing height) MUST produce a deck whose measured principal dimensions match historical Storebro Royal Cruiser 34 (1972) reference values within ±1% (per constitution principle IV). Defaults sourcing follows the same citation-grade / estimate-grade split used in spec 001 (see spec 001 research.md §R1).
- **FR-004**: The deck builder MUST validate every parameter for physical plausibility AND for geometric compatibility with the supplied hull BEFORE invoking FreeCAD. Invalid parameters MUST raise a typed exception (`DeckParameterError`) whose message includes the offending parameter name, the provided value, and the documented valid range or constraint.
- **FR-005**: For identical input parameters (same hull, same deck kwargs), the returned `Deck` MUST have structurally identical geometry: identical topology counts, identical bounding-box dimensions to within floating-point tolerance, identical volume per element. Byte-identical serialization is spec 002's responsibility.
- **FR-006**: The returned Bodies MUST be FreeCAD parametric Bodies composed of Sketch + parametric features (Loft / Pad / Mirroring / Pipe — the same composition rule as spec 001's hull, including the v0.2.0 PartDesign upgrade target). Raw `Mesh.Mesh` construction is forbidden inside the deck module per constitution principle III.
- **FR-007**: Each Body MUST remain editable in the FreeCAD GUI. Named deck dimensions MUST be exposed as `App::PropertyLength` / `App::PropertyAngle` properties on the appropriate Body (e.g., `CabinTrunk.TrunkLength`, `Hardtop.HardtopHeight`, `Railings.RailingHeight`).
- **FR-008**: The deck builder MUST accept at least the following named parameters, each with a documented default and documented unit: **deck_plate_thickness** (meters; default ≈ 0.025 m / 25 mm per clarify Q4), **cabin_trunk_length** (meters), **cabin_trunk_fwd_offset** (meters from stem), **cabin_trunk_width** (meters, must satisfy `< hull.beam_max - 2 × deck_side_walkway`), **cabin_trunk_height** (meters above deck plate), **cabin_trunk_corner_radius** (meters; default ≈ 0.075 m per clarify Q3), **windshield_rake** (degrees from vertical, aft direction positive), **hardtop_length** (meters), **hardtop_height** (meters above cabin trunk top), **hardtop_overhang_fwd** (meters), **hardtop_overhang_aft** (meters), **hardtop_pillar_diameter** (meters; default ≈ 0.04 m per clarify Q2 — two aft support pillars), **railing_height** (meters above deck plate), **deck_side_walkway** (meters; perimeter walkway width between hull edge and cabin trunk side).
- **FR-009**: All five Bodies MUST be symmetric about the centerline (boat's longitudinal vertical plane). The deck module MUST NOT expose asymmetric deck parameters in v1.0.
- **FR-010**: The deck plate MUST be geometrically aligned with the hull's sheer line — its perimeter follows the hull's upper edge as exposed by `Hull.body`. The deck plate MUST be a 3D solid of thickness `deck_plate_thickness` (default 25 mm per clarify Q4), NOT a zero-thickness surface. There MUST NOT be a visible gap or overlap between the hull's top and the deck plate's underside when viewed in the FreeCAD GUI.
- **FR-011**: The deck module MAY import `storebro.hull` (it consumes the `Hull` type) but MUST NOT import `storebro.interior`, `storebro.export`, or `storebro.cli`. Sharing the internal `storebro._freecad_check` helper is permitted (matches spec 002's FR-013 amendment).
- **FR-012**: The deck builder MUST raise `DeckParameterError` before any FreeCAD call when a parameter combination is geometrically impossible (e.g., `cabin_trunk_length >= hull.parameters.loa`, `hardtop_overhang_fwd + hardtop_overhang_aft >= hardtop_length`, cabin width exceeds hull beam minus side walkways).
- **FR-013**: The deck builder MUST check the running FreeCAD version on its first invocation per process (lazy check, sharing spec 001's `_freecad_check` cache). On unsupported versions, raise `DeckConstructionError` with `detected_version` and `supported_range` set.
- **FR-014**: All public deck functions MUST have a one-line docstring with at least one usage example, per DX guidance and matching spec 001/002.
- **FR-015**: Parameter-validation failures MUST raise `DeckParameterError` (a custom exception subclassing `ValueError`, INDEPENDENT of spec 001's `HullParameterError` per clarify Q5). FreeCAD-side construction failures MUST raise `DeckConstructionError` (subclassing `RuntimeError`, INDEPENDENT of `HullConstructionError`). Both classes are part of the public deck module API. Callers wanting cross-module catch-alls use the standard library bases (`ValueError`, `RuntimeError`) — no shared `storebro`-level base class.
- **FR-016**: The deck builder MUST accept an optional `document` keyword argument (default `None`). If supplied, the document MUST equal `hull.document` — passing a different document raises `DeckParameterError`. If `None`, the builder uses `hull.document`. The builder MUST NOT silently mutate the document beyond adding the five Bodies.
- **FR-017**: The deck builder MUST accept an optional `name` keyword argument (default `"Deck"`). The resulting `Deck` aggregate's `.label` is set to this value. The six sub-Bodies MUST be labeled `{name}_DeckPlate`, `{name}_CabinTrunk`, `{name}_Windshield`, `{name}_Hardtop`, `{name}_HardtopPillars`, `{name}_Railings`. FreeCAD's standard label auto-numbering applies on collision.
- **FR-018**: On FreeCAD-side construction failure mid-build, the deck builder MUST roll back any Bodies already added to the document (i.e., remove them) before raising `DeckConstructionError`. Partial decks in the user's document are forbidden.
- **FR-019**: The deck builder MUST detect when `hull.body.Shape` is null / empty and raise `DeckParameterError("hull", "hull body has no shape — recompute the source document first")` before any FreeCAD construction.

### Key Entities

- **DeckParameters**: The named set of dimensional and angular inputs that fully determine a deck's superstructure. ~11 fields per FR-008. Each attribute has a unit, default, valid range, and one-line description. Frozen dataclass (matching spec 001's `HullParameters` pattern).
- **Deck**: The return value of the deck builder. Holds the six sub-Bodies (`deck_plate`, `cabin_trunk`, `windshield`, `hardtop`, `hardtop_pillars`, `railings`), the input `DeckParameters`, the source `Hull` reference, the `document`, the resolved `label`, and `build_duration_seconds`.
- **DeckPlate / CabinTrunk / Windshield / Hardtop / HardtopPillars / Railings**: The six FreeCAD `Part::Body` (or v0.2.0 `PartDesign::Body`) objects added to the document. Each exposes the relevant subset of deck parameters as named properties for GUI editing. `HardtopPillars` is a single Body containing both port and starboard pillars (mirrored per FR-009).
- **DeckParameterError**: Pre-FreeCAD validation failure. Subclasses `ValueError`. Carries `parameter_name`, `parameter_value`, `valid_range` attributes.
- **DeckConstructionError**: FreeCAD-side failure or unsupported-version failure. Subclasses `RuntimeError`. Mirrors spec 001's `HullConstructionError` shape.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With default parameters on the default hull, the generated deck's measured principal dimensions (cabin trunk length, hardtop length, railing height — the citation-grade set) each fall within ±1% of the documented historical Storebro Royal Cruiser 34 (1972) reference values.
- **SC-002**: Generating the default deck on the default hull from a cold FreeCAD process completes in under 45 seconds on a developer laptop. Combined with spec 001's 30-second hull budget, the whole boat builds in under 75 seconds.
- **SC-003**: For any fixed `(Hull, DeckParameters)` pair, two independent invocations of the deck builder produce `Deck` aggregates whose volume, bbox dimensions, and topology counts (per sub-Body) are identical to within `1e-9` relative tolerance for the floats and exact integer match for topology counts.
- **SC-004**: Every named deck parameter, when changed by ±10% from its default, produces a deck whose measured corresponding dimension changes monotonically in the expected direction. No silent no-op parameters.
- **SC-005**: A FreeCAD scripter who knows Python and has read the deck module's public docstrings can compose a custom deck onto their own hull and add their own decorations in under 15 minutes without reading the implementation.
- **SC-006**: At least one geometry property test exists for every public function exported from the deck module AND for every one of the five sub-Bodies.
- **SC-007**: Invalid parameter inputs raise `DeckParameterError` with a message that names the offending parameter, its value, and its valid range or geometric constraint — verified across at least 7 distinct invalid-input test cases.
- **SC-008**: FreeCAD-side construction failures mid-build leave the user's FreeCAD document in the same state as before the call (no orphan Bodies, no partial geometry), and the raised `DeckConstructionError` carries the source `Hull` and `DeckParameters` for diagnosis. Verified by a forced-failure test (one of the five element builders monkeypatched to raise after at least one earlier element has already been added).
- **SC-009**: Deck plate ↔ hull sheer alignment. The strict bar of `1e-6` meters applies once the v0.2.0 Shape-sampling upgrade lands (alongside spec 001's PartDesign loft upgrade): the deck plate's underside is sampled at the same five stations as the hull's sheer face is built, and each pair of measurements agrees within `1e-6` m. For v0.3.0-alpha the sheer is derived analytically from `hull.parameters` (not Shape-walked); the relaxed bar is "the deck plate's underside Z lies within the hull's sheer-line vertical extent" (the implementation produces a flat deck plate at average sheer Z, which falls inside the per-station range). The strict bar is restored when the v0.2.0 upgrade lands; tracked in CHANGELOG alongside the PartDesign migration.

## Assumptions

- **Scope of "deck"**: the six named elements only — deck plate, cabin trunk (with rounded corners and solid sides), windshield, hardtop, two aft hardtop pillars, perimeter railings. No fly bridge, no swim platform, no anchor pulpit, no bow rail extensions, no transom door, no glazing (per clarify Q1). Those join in v1.1+ or downstream specs.
- **Single cabin trunk**: one fore-of-amidships cabin with one continuous windshield. No aft cabin, no flybridge, no split cabins.
- **Hardtop is a fixed flat roof**: no canvas bimini, no folding hardtop, no sliding sunroof. Future variants are deferred.
- **Railings are continuous loops**: a perimeter rail at fixed height, no individual stanchions or hand-modelled posts in v1.0. Stanchion-and-rail with discrete posts is a v1.1+ refinement.
- **No glazing in v1.0** (clarify Q1): cabin trunk has solid sides; the windshield is a solid face. Cutting window openings (deadlights, portholes, opening hatches) is out of scope for v1.0. Glazing arrives in v1.1+ once the interior module exists to receive the light.
- **Symmetric only**: every Body mirrors across the X-Z plane. Asymmetric decks are out of scope.
- **Units**: meters and degrees throughout. SI only.
- **Defaults source**: principal cabin/hardtop/railing dimensions come from historical Storebro Royal Cruiser 34 (1972) references. The same citation-grade vs estimate-grade split from spec 001's research.md §R1 applies.
- **Active FreeCAD document**: the deck builder reuses the hull's document by default. Cross-document deck building is explicitly rejected (FR-016).
- **No logging / no telemetry in v1.0**: matches spec 001 clarify Q4 and spec 002.
- **Test environment**: pytest with the same two markers (`unit`, `requires_freecad`). Geometry tests skip cleanly without FreeCAD on PATH.
