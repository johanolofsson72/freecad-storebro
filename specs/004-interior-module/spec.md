# Feature Specification: Interior Module

**Feature Branch**: `004-interior-module`

**Created**: 2026-05-17

**Status**: Draft

**Input**: User description: "the interior module — cabins, galley, heads, salon driven by canonical Alternativ1-5 YAML fixtures, consumes hull from spec 001 and deck from spec 003"

## Clarifications

### Session 2026-05-17

- Q: How should `position` and `dimensions` be structured inside a compartment's YAML entry? → A: **Named sub-dicts** with axis keys: `position: {x: float, y: float, z: float}` and `dimensions: {length: float, width: float, height: float}`. Verbose but unambiguous for hand-authored fixtures; impossible to confuse axis order at a glance.
- Q: Should the YAML schema require an explicit `schema_version` field? → A: **Yes, required**. v1.0 schema is `schema_version: 1`. A missing or unknown `schema_version` raises `InteriorParameterError`. Gives migration headroom in v1.1+ without breaking older fixtures.
- Q: What point on each compartment box does `position` reference? → A: **Forward-bottom-center**. `position.x` is the X coordinate of the compartment's forward face (measured aft from the bow at `x=0`), `position.y` is the Y coordinate of the compartment's centerline (always 0 because FR-009 requires centerline symmetry — the field is still present in the schema for future asymmetric variants but must be 0 in v1.0), and `position.z` is the compartment's floor (typically the deck-plate top for above-deck compartments and the keel-line for below-deck compartments).
- Q: Should `build_interior(hull, deck)` have a default `layout` so a no-arg call works after a default hull + deck? → A: **Default to `"Alternativ3"`**. This is the most photographed RC34 layout and the project's canonical "Storebro silhouette" example. Callers wanting any specific layout pass an explicit name or path; the default keeps the "just build me a boat" path one line long.
- Q: May two compartments share a boundary face (zero-thickness bulkhead contact)? → A: **Yes, face-touching is allowed**; only volume-overlap is rejected. Compartments commonly share a bulkhead — the forward cabin's aft face is the galley's forward face. The validator's overlap check uses a small positive volume threshold (e.g. `> 1e-6 m³`) to permit face-touching while rejecting genuine volumetric overlap.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Boat restorer materializes a canonical Storebro interior layout (Priority: P1)

A boat restorer has built the default hull (spec 001) and mounted the default deck (spec 003). They now want to add the interior — cabins forward, galley + head amidships, salon aft — matching one of the five canonical Storebro Royal Cruiser 34 layouts the project ships ("Alternativ1" through "Alternativ5", documented in `docs/references/`). They expect a single function call that takes the existing hull and deck plus a layout name (or a default) and produces a fully editable, parametric set of interior compartments inside the same FreeCAD document.

**Why this priority**: This is the foundational use case AND the unique value proposition of the project — no public parametric Storebro model exists today. The hull + deck + interior triple is what the project's PROJECT-BRIEF promises restorers and scale modelers. Without it, the hull is a soup bowl and the deck is decoration; with it, the model is recognizably the boat someone is restoring or scaling.

**Independent Test**: From a Python REPL with FreeCAD on PATH, run `from storebro import build_hull, build_deck, build_interior; h = build_hull(); d = build_deck(h); i = build_interior(h, d, layout="Alternativ3"); i.document.saveAs("/tmp/whole_boat_with_interior.FCStd")` and verify the resulting FreeCAD document opens with the hull, deck, AND four compartment volumes (forward cabin, galley, head, salon) all visible and parametrically editable.

**Acceptance Scenarios**:

1. **Given** a default hull and default deck in the same document, **When** the restorer calls `build_interior(hull, deck, layout="Alternativ3")`, **Then** the FreeCAD document gains four compartment Bodies (forward cabin, galley, head, salon) with labels like `Interior_Alternativ3_ForwardCabin`, each parametrically editable in the GUI.
2. **Given** the restorer exports the result via spec 002's `export_fcstd`, **When** they reopen it in the FreeCAD GUI, **Then** all interior compartments are present, editable, and bounded by the hull/deck envelope (no compartment clipping through the hull's outer shell).
3. **Given** the restorer points the builder at a different layout name (`Alternativ1`, `Alternativ2`, `Alternativ4`, `Alternativ5`), **When** the call succeeds, **Then** the resulting compartment count, positions, and proportions match the documented layout's cutaway drawing in `docs/references/`.

---

### User Story 2 - Naval architecture student compares all five layouts (Priority: P2)

A naval architecture student wants to render all five canonical layouts side by side — same hull, same deck, five interiors. They write a short loop that iterates over `["Alternativ1", "Alternativ2", "Alternativ3", "Alternativ4", "Alternativ5"]` and builds an interior per layout into separate FreeCAD documents. They open the five `.FCStd` files in the GUI and study how each layout uses the same volume differently.

**Why this priority**: The five-layout study is the project's most distinctive offering — no other open-source tool ships five historically-curated Storebro interior options. Validating it works end-to-end is what makes the library notable.

**Independent Test**: Build five interiors (one per layout) into five fresh FreeCAD documents and assert that the compartment counts, types, and positions differ as documented by the cutaway drawings. The "Alternativ N" → compartment set mapping is the ground truth.

**Acceptance Scenarios**:

1. **Given** the same default hull + deck, **When** the student iterates over all five layout names, **Then** each layout produces a recognizable compartment set; the five resulting documents are NOT byte-identical (different layouts produce different geometry).
2. **Given** any two distinct layouts, **When** the student measures compartment counts and positions, **Then** the difference is non-trivial (≥1 compartment differs in position, type, or count).

---

### User Story 3 - Power user supplies their own YAML layout fixture (Priority: P3)

A power user wants to design a layout that isn't one of the five shipped canonical options — say, a single-large-cabin liveaboard variant. They write a YAML file describing their compartments (each with type, position, dimensions, name) and pass its path to the builder. The builder validates the YAML against the same schema the shipped layouts use, raises clear errors on schema violations, and produces interior compartments per the user's layout.

**Why this priority**: User-supplied layouts are the extensibility hook the constitution implies ("five canonical layouts ship as data, not code"). Without it, the project is a closed catalog of five variants; with it, it's a parametric platform.

**Independent Test**: Write a minimal valid YAML fixture (one cabin), pass its path to `build_interior(hull, deck, layout="/tmp/my_layout.yaml")`, and verify the resulting compartment matches the YAML. Then write a malformed YAML (missing required field, out-of-envelope position) and verify the builder raises a typed validation error citing the file path and the offending field.

**Acceptance Scenarios**:

1. **Given** a user-supplied YAML file with a valid schema and compartments inside the hull/deck envelope, **When** the user calls `build_interior(hull, deck, layout="/tmp/my_layout.yaml")`, **Then** the builder produces compartments matching the YAML.
2. **Given** a user-supplied YAML file with a missing required field (e.g., a compartment with no `position`), **When** the user calls the builder, **Then** the builder raises `InteriorParameterError` whose message cites the YAML file path, the offending compartment name, and the missing field.
3. **Given** a user-supplied YAML file with a compartment positioned outside the hull's beam, **When** the user calls the builder, **Then** the builder raises `InteriorParameterError` whose message cites the offending compartment and the envelope constraint that was violated.

---

### Edge Cases

- **`hull` is None or has an empty `.Shape`**: builder MUST raise typed error before reading any YAML.
- **`deck` is None or has an empty `.deck_plate.body.Shape`**: builder MUST raise typed error before reading any YAML.
- **`hull.document` is not `deck.document`**: builder MUST raise typed error — the deck must already be mounted on the same hull.
- **Layout name is not one of the five canonical names and is not a valid filesystem path**: builder MUST raise typed error citing the layout argument and the list of canonical names.
- **YAML file does not exist**: builder MUST raise typed error citing the requested path.
- **YAML file exists but has invalid syntax**: builder MUST surface the YAML parse error wrapped in `InteriorParameterError` with the file path.
- **YAML defines a compartment that extends outside the hull's bounding box** (e.g., longer than LOA, wider than beam, or below the keel): builder MUST raise `InteriorParameterError` before any FreeCAD construction.
- **YAML defines two compartments that overlap geometrically**: builder MUST raise `InteriorParameterError` citing both compartment names. Cabin / galley / salon volumes are mutually exclusive — they share bulkheads, not volumes.
- **YAML defines zero compartments**: builder MUST raise `InteriorParameterError` ("a layout must contain at least one compartment").
- **FreeCAD-side construction failure during one compartment**: builder MUST roll back any compartment Bodies already added to the document, mirroring spec 003's FR-018 discipline.
- **Layout name with path separators that resolves to a file outside the project** (e.g., `../../../etc/passwd`): builder accepts the path as-is — there is no privilege boundary in this library — but the YAML must still pass schema validation. No special path-traversal handling is needed because the worst case is "file fails to parse as a valid layout YAML".

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The interior module MUST expose a single public function that accepts a `Hull` (from spec 001), a `Deck` (from spec 003), and a `layout` argument identifying either one of five canonical names (`Alternativ1`–`Alternativ5`) or a filesystem path to a YAML file (default `"Alternativ3"` per clarify Q4), and returns an `Interior` aggregate containing one parametric Body per compartment.
- **FR-002**: The five canonical layouts MUST be shipped as YAML fixtures inside the installed package (`src/storebro/fixtures/Alternativ1.yaml` through `Alternativ5.yaml`). They MUST be loadable by canonical name without needing a filesystem path — the module locates them via `importlib.resources`.
- **FR-003**: Default values for compartment positions, dimensions, and counts in each canonical layout MUST match the historical Storebro Royal Cruiser 34 (1972) cutaway drawings in `docs/references/Alternativ*.JPG` within ±5% on principal compartment dimensions (looser than spec 001/003's ±1% because interior cutaways are less precise than hull plans).
- **FR-004**: The builder MUST validate every YAML layout against a documented schema before invoking FreeCAD. Schema violations (missing required field, wrong type, out-of-range value, invalid compartment type) MUST raise `InteriorParameterError` whose message includes the YAML source (file path or fixture name), the offending compartment name, and the schema violation.
- **FR-005**: For identical input `(Hull, Deck, layout)` tuples, the returned `Interior` MUST have structurally identical geometry per compartment: identical topology counts, identical bounding-box dimensions, identical volume. Byte-identical serialization is spec 002's contract.
- **FR-006**: Returned Bodies MUST be FreeCAD parametric Bodies composed of Sketch + parametric features. No `Mesh.Mesh` construction inside the interior module per constitution III.
- **FR-007**: Each compartment Body MUST remain editable in the FreeCAD GUI. Compartment position and dimensions MUST be exposed as `App::PropertyLength` properties on the Body so a GUI user can edit and recompute.
- **FR-008**: The YAML layout schema MUST support exactly four compartment types in v1.0: `forward_cabin`, `galley`, `head`, `salon`. Other types (engine_room, aft_cabin, swim_platform_storage, etc.) are out of scope and raise a schema error if used.
- **FR-009**: All compartment Bodies MUST be symmetric about the centerline (the boat's longitudinal vertical plane). The YAML schema does NOT support asymmetric compartments in v1.0.
- **FR-010**: Every compartment MUST be bounded by the hull's outer shell (no clipping through it) and by the deck plate above. The validator MUST reject compartments that exceed the hull envelope before any FreeCAD construction.
- **FR-011**: The interior module MAY import `storebro.hull` AND `storebro.deck` (it consumes both types). It MUST NOT import `storebro.export` or `storebro.cli`. Sharing `storebro._freecad_check` is permitted (matches spec 002 + spec 003's amended leaf-module rule).
- **FR-012**: The builder MUST raise `InteriorParameterError` before any FreeCAD call when two compartments overlap geometrically (intersection volume > `1e-6 m³` per clarify Q5). Face-touching compartments (shared boundary face, zero intersection volume) are permitted and common — adjacent compartments share bulkheads.
- **FR-013**: The interior module MUST check the running FreeCAD version on its first invocation per process via the shared `storebro._freecad_check` helper, raising `InteriorConstructionError` on unsupported versions.
- **FR-014**: All public interior functions MUST have a one-line docstring with at least one usage example, per DX guidance matching spec 001/002/003.
- **FR-015**: Parameter-validation failures MUST raise `InteriorParameterError` (subclassing `ValueError`). FreeCAD-side construction failures MUST raise `InteriorConstructionError` (subclassing `RuntimeError`). Both classes are part of the public module API. Independent of spec 001's and spec 003's exception classes (each module owns its own taxonomy, matching spec 003 clarify Q5).
- **FR-016**: The builder MUST accept an optional `document` keyword argument (default `None`). If supplied, the document MUST equal `hull.document` (which by FR-016 of spec 003 equals `deck.document`); cross-document interior building is rejected with `InteriorParameterError`. If `None`, the builder uses `hull.document`.
- **FR-017**: The builder MUST accept an optional `name` keyword argument (default `"Interior_{layout_name}"`). The compartment Bodies MUST be labeled `{name}_{compartment_type}` (e.g., `Interior_Alternativ3_ForwardCabin`). FreeCAD label auto-numbering applies on collision.
- **FR-018**: On FreeCAD-side construction failure mid-build, the interior module MUST roll back any compartment Bodies already added to the document before raising `InteriorConstructionError` (matches spec 003 FR-018).
- **FR-019**: The builder MUST detect document mismatch between `hull.document` and `deck.document` and raise `InteriorParameterError("deck", "deck.document must equal hull.document — deck was not built on this hull")` before any FreeCAD call.
- **FR-020**: The five canonical YAML fixtures (`Alternativ1.yaml` through `Alternativ5.yaml`) MUST each contain a `schema_version: 1` (required per clarify Q2), a `layout_name`, a `source` (citation to `docs/references/AlternativN.JPG`), and a list of `compartments`. Each compartment carries:
    - `name`: String, unique within the layout
    - `type`: One of `forward_cabin`, `galley`, `head`, `salon` (per FR-008)
    - `position`: A sub-dict with keys `x`, `y`, `z` (floats, meters) — the forward-bottom-center reference point per clarify Q3 (x measured aft from bow, y always 0 in v1.0, z is compartment floor)
    - `dimensions`: A sub-dict with keys `length`, `width`, `height` (floats, meters)
    - `description`: Optional human-readable string
- **FR-021**: The YAML schema MUST require a top-level `schema_version` field with value `1` for v1.0 fixtures. Missing or unknown `schema_version` raises `InteriorParameterError` citing the YAML source and the required version. Future schema migrations bump the version and document the migration in CHANGELOG (per clarify Q2).

### Key Entities

- **InteriorParameters / LayoutSpec**: The parsed YAML layout — a list of compartment specifications plus metadata (layout name, source citation). Loaded once at builder entry and validated against schema before any FreeCAD call.
- **Compartment**: A single interior volume — a forward cabin, galley, head, or salon. Carries name, type, position, dimensions. Constructs to a single FreeCAD Body.
- **Interior**: The return value of the builder. Holds a list of compartment Body wrappers, the input `Hull` + `Deck` references, the layout name, the document, the resolved aggregate label, and `build_duration_seconds`.
- **CompartmentBody (per type)**: Wrapper around the FreeCAD Body for one compartment. Same pattern as spec 003's six sub-Body wrappers.
- **InteriorParameterError**: Pre-FreeCAD validation failure. Subclasses `ValueError`. Carries the layout source (file path or fixture name) plus the offending compartment name and schema violation.
- **InteriorConstructionError**: FreeCAD-side construction failure or unsupported-version failure. Subclasses `RuntimeError`. Mirrors spec 003's `DeckConstructionError` shape.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For each of the five canonical layouts (`Alternativ1` through `Alternativ5`), the generated interior's compartment count, types, and principal dimensions match the documented layout reference within ±5% on dimensions and exactly on counts/types.
- **SC-002**: Generating the default-layout (Alternativ3) interior on the default hull + deck completes in under 60 seconds on a developer laptop. Combined with spec 001's 30 s + spec 003's 45 s, the whole-boat build stays under 135 s — well inside the "human-scale seconds" budget.
- **SC-003**: For any fixed `(Hull, Deck, layout)` tuple, two independent invocations produce `Interior` aggregates whose per-compartment volume, bounding-box dimensions, and topology counts are identical to within `1e-9` relative tolerance.
- **SC-004**: Loading the same canonical layout name in two independent builds produces compartment Bodies that match (same count, same per-compartment dimensions). The YAML loader is deterministic.
- **SC-005**: A FreeCAD scripter who knows Python and has read the interior module's public docstrings can write a custom YAML layout fixture and build it onto their own hull + deck in under 20 minutes.
- **SC-006**: At least one geometry property test exists for each canonical layout AND each of the four compartment types.
- **SC-007**: Invalid layouts (malformed YAML, schema violations, envelope overflows, geometric overlaps) raise `InteriorParameterError` with a message that names the source, the offending compartment, and the violation — verified across at least 10 distinct invalid-input test cases (the highest bar in the project so far, reflecting the data-driven nature of this module).
- **SC-008**: FreeCAD-side construction failures mid-build leave the document in the same state as before the call (no orphan compartment Bodies). Verified by a forced-failure test that monkeypatches the 3rd-of-4 compartment builder to raise.
- **SC-009**: Every compartment in every canonical layout fits inside the hull envelope on the default hull — verified by a geometric containment test that asserts each compartment's bounding box is fully inside the hull's `Shape.BoundBox`.

## Assumptions

- **Scope of "interior"**: four compartment types only — `forward_cabin`, `galley`, `head`, `salon`. No engine room, no aft cabin (the RC34 had a single fore cabin), no separate dinette, no wet locker, no fuel/water tanks. Those are deferred to v1.1+ or modeled as part of the cabin/salon volumes.
- **Box compartments**: each compartment is approximated as an axis-aligned rectangular box. No curved bulkheads, no slanted walls following the hull. The box is positioned and sized to fit inside the hull envelope; the visual approximation is acceptable for v1.0.
- **Bulkheads are implicit**: shared walls between adjacent compartments are not modeled as separate Bodies. Each compartment is a solid volume; "bulkhead" is conceptually the boundary face between two adjacent compartments.
- **No furniture**: bunks, settees, galley cabinetry, hatches, doors are out of scope. Each compartment is an empty volume.
- **Five canonical layouts are fixed**: Alternativ1-5 are the historically documented Storebro Royal Cruiser 34 1972 variants. Adding a sixth canonical layout requires a future spec.
- **YAML is the layout format**: not JSON, not TOML. Matches industry conventions for hand-authored fixture data and reads cleanly in the FreeCAD ecosystem. PyYAML (or equivalent stdlib YAML reader) is the runtime dependency.
- **Reference fidelity**: ±5% on compartment dimensions (looser than the hull's ±1% because interior cutaways are less dimensionally precise than hull plans). The defaults are estimate-grade; refinable in PATCH bumps when primary source documentation surfaces.
- **Hull and deck must be on the same document**: cross-document composition is rejected. The interior is built on top of the hull-and-deck-on-the-same-document pattern established by spec 003.
- **Single layout per call**: a single `build_interior` call produces one layout. Multiple layouts in the same document are supported by calling the builder twice with different layout names (FreeCAD label auto-numbering applies).
- **No logging / no telemetry in v1.0**: same as spec 001/002/003.
- **Test environment**: pytest with `unit` and `requires_freecad` markers. Geometry tests skip cleanly without FreeCAD.
