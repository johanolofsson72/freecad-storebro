# Feature Specification: Render Attributes (Colors & Materials)

**Feature Branch**: `master` (solo / direct-push — no feature branch per project workflow)

**Created**: 2026-06-02

**Status**: Draft

**Track**: Spec-only (pure cosmetic property assignment — no new geometry, no new entities, no state transitions)

**Input**: User description: "015-render-attributes — Assign cosmetic render attributes (colors + materials) to every geometry body the library produces, so the generated `.FCStd` renders with realistic Storebro appearance in the FreeCAD GUI: gelcoat-white hull, teak/mahogany trim, chromed/stainless hardware, translucent glass, bronze propeller/shaft, dark engine. Reproducible, headless-safe, FreeCAD-idiomatic, additive API, default-on with an opt-out flag."

## Clarifications

### Session 2026-06-02

- Q: How is coloring exposed in the public API — a parameter on each build function, a single post-build pass over the document, or both? → A: Both — a single central palette + applier helper (public) that colors objects by role, invoked by each public `build_*` via an additive `apply_render_attributes: bool = True` kwarg (default on). Matches the spec-010/011/014 optional-kwarg pattern and keeps geometry construction and cosmetics separable while satisfying default-on for the public build API.
- Q: How is windshield-glass translucency represented so it is both headless-persisted and GUI-visible? → A: The glass palette entry stores a low alpha (< 1.0) in its RGBA constant; the applier persists the color as data, and when a GUI view object is present it also derives the view transparency from that alpha. Headless tests assert the windshield-glass palette alpha is below 1.0.
- Q: Is opt-out global or per-role? → A: Global on/off only (`--no-colors` CLI flag / `apply_render_attributes=False` kwarg); per-role toggling is out of scope.
- Q: Is a two-tone hull boot/waterline stripe in scope? → A: No — the hull is a single solid body and cannot be two-toned without splitting geometry, which this spec-only track forbids; boot/waterline stripe is deferred.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A built model looks like a Storebro when opened in FreeCAD (Priority: P1)

A restorer or scale modeler runs `storebro build --layout 3 --out boat.FCStd`, opens the file in the FreeCAD GUI, and immediately sees a recognizable vintage Storebro: an off-white gelcoat hull, warm teak-brown rubrail and interior joinery, bright chromed/stainless railings and deck hardware, translucent glass in the windshield, and a bronze propeller on a steel shaft behind a dark engine. No manual recoloring is required — the model arrives painted.

**Why this priority**: This is the entire point of the spec. Up to v1.1.0 every body renders in FreeCAD's default flat grey, which reads as a CAD blank, not a boat. Color is ~10% of the modelling effort but a large share of the "it looks like a Storebro" perception, and it is the last cosmetic gap before the model is presentable.

**Independent Test**: Build any layout, open the `.FCStd` in the FreeCAD GUI, and confirm each major component carries its expected color (hull white, rubrail brown, railings metallic-grey, windshield glass translucent, propeller bronze, engine dark). Delivers immediate visual value on its own.

**Acceptance Scenarios**:

1. **Given** a freshly built document containing hull, deck, interior, and propulsion bodies, **When** the model is opened in the FreeCAD GUI, **Then** the hull renders gelcoat off-white, the rubrail and interior furniture render warm teak/mahogany brown, the railings/pulpit/lifelines/cleats render light-grey metallic, the windshield glass renders translucent blue-grey, the propeller renders bronze, and the engine renders dark grey-green.
2. **Given** the same model, **When** a body's stored render attributes are inspected programmatically (without a GUI), **Then** each body reports a deterministic color and a named material consistent with its role.
3. **Given** a body whose role has no explicit palette entry (e.g. a custom non-canonical interior compartment), **When** attributes are applied, **Then** the body receives a sensible neutral default color rather than being skipped or raising an error.

---

### User Story 2 - Opt out for a neutral, uncolored model (Priority: P2)

A FreeCAD scripter who wants to apply their own appearance scheme, or who needs a neutral model for measurement/export work, builds the boat with coloring turned off and gets the previous default-grey geometry untouched.

**Why this priority**: Colors are a default-on convenience, but some downstream uses (custom rendering pipelines, neutral STEP hand-off, screenshots against a specific style) want the geometry without imposed appearance. A clean opt-out keeps the feature from being a lock-in.

**Independent Test**: Build the same layout twice — once normally, once with coloring disabled — and confirm the disabled build carries no render attributes (FreeCAD default appearance) while geometry is identical between the two.

**Acceptance Scenarios**:

1. **Given** a build invoked with coloring disabled (CLI flag and/or API parameter), **When** the document is produced, **Then** no body carries library-assigned color or material attributes and the geometry is byte-for-byte identical to a build that never applied attributes.
2. **Given** a build invoked normally, **When** the document is produced, **Then** coloring is applied (default-on).

---

### User Story 3 - Coloring never breaks reproducibility or headless builds (Priority: P3)

A CI job builds the model on a headless machine (no GUI) and asserts byte-identical exports across runs. Coloring must neither crash the headless build nor introduce any run-to-run variation.

**Why this priority**: Constitution principle II (reproducibility) and principle III (FreeCAD-idiomatic, headless-capable) are non-negotiable. A cosmetic feature that breaks determinism or the headless path would be a net regression regardless of how good it looks.

**Independent Test**: Run a headless build twice with identical inputs and confirm (a) both succeed without a GUI, (b) stored attributes are present and identical, and (c) deterministic exports remain byte-identical.

**Acceptance Scenarios**:

1. **Given** a headless build (no GUI document, `ViewObject` unavailable), **When** the model is built with coloring on, **Then** the build succeeds and every body persists its color/material as data that survives a save/reload.
2. **Given** two headless builds with identical parameters, **When** the resulting documents (and deterministic exports) are compared, **Then** all assigned colors and materials are identical and the export bytes match.
3. **Given** a build run with a GUI present, **When** coloring is applied, **Then** the GUI-visible appearance is set from the same stored attributes, so headless and GUI builds agree on color.

---

### Edge Cases

- **Headless (no GUI)**: `ViewObject` is `None` in console mode — applying attributes MUST NOT dereference it unconditionally; the stored data attributes carry the color so the GUI can render it on next open.
- **Unknown / custom body role**: a body whose label/role is not in the palette gets the neutral default, never a crash or a silent skip that leaves it visibly inconsistent.
- **Coloring disabled**: opting out leaves bodies in FreeCAD's default appearance and changes no geometry.
- **Glazing that is a recess, not a separate body**: portholes (hull pockets) and cabin-trunk side windows (cabin-trunk recesses) are part of opaque parent bodies, so they take the parent color; only the windshield has a separate glass body that can be made translucent. Separate transparent glass inserts for portholes/cabin windows are out of scope (deferred).
- **Compound wrappers**: components exposed as `Part::Feature` compounds (rubrail, railings, cleats, lifelines, hardtop pillars) receive the role color on the wrapper they present.
- **Twin vs single screw**: both propeller/shaft/rudder trains (port and starboard) receive the same role colors regardless of `engine_count`.
- **Missing FreeCAD**: on a host without FreeCAD, geometry cannot be built at all; coloring inherits that constraint and is only exercised by the geometry-tier (`requires_freecad`) tests.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The library MUST assign a deterministic color and a named material to every geometry body it produces across the hull, deck, interior, and propulsion modules.
- **FR-002**: Colors and materials MUST be sourced from a single central palette that maps each body role to an RGBA color and a material name. No color value may be hard-coded at a body's construction site.
- **FR-003**: The palette MUST cover these roles with the following intent: hull → gelcoat off-white; deck plate / cabin trunk / hardtop / anchor locker → gelcoat off-white (superstructure); rubrail and interior furniture/joinery → warm teak/mahogany brown; railings, bow pulpit, lifelines, cleats, hardtop pillars → light-grey metallic (chrome/stainless); windshield frame → metallic/dark frame; windshield glass → translucent blue-grey (low alpha); engine bed and engine → dark grey-green; propeller → bronze; shaft → steel/metallic; rudder → bronze/steel; bulkheads → light neutral.
- **FR-004**: Colors MUST be deterministic constants — no randomness, no environment-, time-, or run-dependent values — so that identical inputs produce identical assigned attributes (constitution principle II).
- **FR-005**: Coloring MUST succeed in a headless build where the GUI view object is unavailable, persisting the color/material as document data that survives save and reload.
- **FR-006**: When a GUI document is present, the GUI-visible appearance MUST be set from the same palette values so headless and GUI builds agree on color.
- **FR-007**: Coloring MUST be on by default for `storebro build` and the public build API, so a normal build yields a colored model.
- **FR-008**: The CLI MUST provide a global opt-out flag (`--no-colors`) and each public `build_*` function MUST provide an equivalent additive `apply_render_attributes: bool = True` parameter (default on) to disable coloring, yielding a neutral model whose geometry is byte-identical to an uncolored build. Opt-out is global on/off only — per-role toggling is out of scope.
- **FR-009**: Disabling coloring MUST leave all bodies in FreeCAD's default appearance with no library-assigned attributes.
- **FR-010**: A body whose role is not present in the palette MUST receive a defined neutral default color/material rather than being skipped or causing an error.
- **FR-011**: Coloring MUST NOT alter any geometry: no body's shape, solid count, validity, bounding box, or volume may change as a result of applying render attributes.
- **FR-012**: Coloring MUST NOT break existing deterministic exports — STEP/STL/BREP outputs (which carry no appearance) remain byte-identical, and within-document `.FCStd` determinism is preserved.
- **FR-013**: All new public API surface MUST be additive (no breaking changes to existing `build_*` signatures or aggregates): a single public palette + applier helper plus an additive `apply_render_attributes: bool = True` kwarg on each public `build_*`, bumping the version from 1.1.0 (MINOR for the additive API).
- **FR-014**: The windshield glass palette entry MUST store a low alpha (< 1.0) so it reads as translucent glass; the applier persists this as data and, when a GUI view object is present, also derives the view transparency from that alpha.

### Key Entities *(include if feature involves data)*

- **Render attribute**: the cosmetic appearance of a single body — an RGBA color plus a named material label. Carries no geometric meaning; purely visual.
- **Palette**: the central, deterministic mapping from a body role (identified by its stable role/label) to a render attribute. Single source of truth for every color in the model.
- **Body role**: the semantic identity of a produced body (hull, rubrail, railing, windshield-glass, propeller, engine, bulkhead, …), already encoded by each body's stable label at construction time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the bodies produced by a default `storebro build` carry a non-default, role-appropriate color and a named material when opened in the FreeCAD GUI.
- **SC-002**: A viewer who opens a default-built model can correctly identify hull, teak trim, metallic hardware, glass, propeller, and engine by color alone, with no manual recoloring.
- **SC-003**: Two builds with identical inputs produce identical assigned colors/materials on every body, and deterministic exports remain byte-identical (0 differences).
- **SC-004**: A headless build with coloring on succeeds (0 GUI-related failures) and every body persists its color/material across a save/reload.
- **SC-005**: A build with coloring disabled produces geometry byte-identical to an uncolored build, with 0 bodies carrying library-assigned attributes.
- **SC-006**: Applying render attributes changes 0 geometric properties (shape, solid count, validity, bounding box, volume) on every body.

## Assumptions

- "User" for this library means the FreeCAD scripter / CLI caller and anyone who opens the produced `.FCStd` in the FreeCAD GUI.
- Each body already has a stable, role-identifying label (verified in hull.py / deck.py / interior.py / propulsion.py) that the palette keys on; no renaming of existing bodies is required.
- Portholes and cabin-trunk side windows are recesses in opaque parent bodies, so they take the parent color; separate transparent glass inserts for them are deferred (only the windshield has a standalone glass body to make translucent).
- FreeCAD's standard appearance/material facilities (per-object color and a material property) are sufficient — no custom rendering engine, no external material library.
- Color is cosmetic only and carries no engineering meaning (not used for material properties, mass, or simulation).
- The geometry tier runs only where FreeCAD is installed; on the implementation host without FreeCAD, color logic is validated by the headless-safe code paths and unit-level palette tests, with the GUI eyeball deferred to a FreeCAD 1.1+ host (constitution principle V), consistent with specs 010–013.
- Exact RGBA constants are an implementation detail chosen to match the reference photos; the spec fixes the intent (off-white, teak-brown, metallic-grey, translucent glass, bronze, dark engine), not the precise hex values.
