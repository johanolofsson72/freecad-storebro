# Feature Specification: Hull Module

**Feature Branch**: `001-hull-module`

**Created**: 2026-05-17

**Status**: Draft

**Input**: User description: "the hull module"

## Clarifications

### Session 2026-05-17

- Q: What exception taxonomy should the hull module use for validation vs construction failures? → A: Two custom classes — `HullParameterError(ValueError)` for pre-FreeCAD parameter validation failures, and `HullConstructionError(RuntimeError)` for FreeCAD-side construction failures. Both are part of the public hull module API.
- Q: How does the hull builder handle the FreeCAD document into which the new Body is placed? → A: Accept an optional `document` keyword argument. If supplied, place the Body in that document. If None and no FreeCAD document is currently active, create a new unnamed document, make it active, and place the Body there. Never silently mutate a user-supplied document.
- Q: How are multiple Hull Bodies named when the hull-builder function is invoked more than once in the same document? → A: Accept an optional `name` keyword argument with default `"Hull"`. Set the Body's `Label` to this value; FreeCAD's standard auto-numbering applies on duplicate Labels (e.g. `Hull`, `Hull001`, `Hull002`).
- Q: Should the hull module emit logging or telemetry in v1.0? → A: No logging in v1.0. Errors are surfaced as exceptions; success is a return value. Telemetry / progress logging is explicitly deferred to v1.1+ if profiling demand emerges.
- Q: When does the supported-FreeCAD-version check run? → A: Lazy — on the first invocation of the hull builder per process. Import of `storebro.hull` MUST NOT trigger the check, so introspection, docstring readers, and IDE tooling remain unaffected.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - FreeCAD scripter composes hull with their own geometry (Priority: P1)

A hobbyist or professional FreeCAD scripter wants to import the `storebro` package, call a single function with optional hull parameters, and receive a fully editable parametric FreeCAD Body representing the Storebro hull shell. They will compose this Body with their own additional geometry (e.g. custom hardware, bespoke fittings) inside their own FreeCAD document.

**Why this priority**: This is the foundational use case. Without a public, ergonomic hull-building function returning a parametric Body, no other module (deck, interior, export, CLI) has anything to build on. It is also the minimum slice that delivers value: a scripter can use the hull in their own pipeline even before deck/interior exist.

**Independent Test**: Run `storebro.hull.build_hull(...)` from a Python REPL connected to FreeCAD, inspect the returned Body in the FreeCAD GUI, verify that it appears in the document tree, has named parametric features, and renders as a closed hull shell — without invoking any other storebro module.

**Acceptance Scenarios**:

1. **Given** a fresh FreeCAD document and the `storebro` package installed, **When** the scripter calls the hull-builder function with no arguments, **Then** a parametric Body representing the canonical Storebro hull is added to the active document and returned to the caller.
2. **Given** the scripter passes a non-default LOA value, **When** the function executes, **Then** the returned Body has overall length matching the requested LOA within build-time tolerance, and the LOA value is exposed as a named property on the Body so the GUI shows it.
3. **Given** the scripter inspects the returned Body in the FreeCAD GUI, **When** they edit a named hull dimension on the Body's properties panel, **Then** the hull geometry recomputes correctly without re-running any storebro code (i.e. the geometry is parametric inside FreeCAD, not flattened to dumb edges).

---

### User Story 2 - Boat restorer generates the canonical Storebro hull for reference (Priority: P2)

A boat restorer or scale modeler wants to generate a faithful digital model of the historical Storebro hull using default parameters, then visually compare it against original cutaway drawings. They open the resulting `.FCStd` in the FreeCAD GUI and check that the proportions look right against their reference photos.

**Why this priority**: This validates the constitutional **Reference Fidelity** principle — default parameters must produce historically-correct proportions within ±1% on principal dimensions. It is also the most common end-user workflow for non-developers using the package via its (future) CLI.

**Independent Test**: With default parameters and the hull module alone, produce a Body whose principal dimensions (LOA, beam_max, draft, freeboard) match the historical Storebro reference values within ±1%. Measurement is automated via FreeCAD's bounding-box API in a pytest assertion. Reference values come from `docs/references/`.

**Acceptance Scenarios**:

1. **Given** the historical Storebro reference dimensions, **When** the hull is built with default parameters, **Then** the resulting Body's LOA, beam_max, draft, and freeboard each fall within ±1% of the reference values.
2. **Given** the restorer opens the generated `.FCStd` in the FreeCAD GUI, **When** they visually overlay the hull with the reference cutaway drawing, **Then** the sheer line, transom shape, and deadrise profile are qualitatively faithful to the historical hull form (verified manually, captured in the PR description per constitution principle V).

---

### User Story 3 - Naval architecture student studies parametric variation (Priority: P3)

A naval architecture student wants to systematically vary individual hull parameters (e.g. shorten LOA by 10%, sharpen the deadrise from 18° to 24°, raise the freeboard) to study how the hull form responds. They run the function multiple times with different parameter sets, export each variant to STEP via a separate tool, and compare them in their preferred CAD environment.

**Why this priority**: This validates **Parametric Everything** end-to-end — every named parameter must actually move geometry, not be a no-op. It is the litmus test that the hull is not secretly a static shape with cosmetic parameters bolted on.

**Independent Test**: For every named hull parameter, generate two hulls differing only in that parameter's value (default vs. ±10%), and assert that the resulting bounding boxes or topology measurements differ in the direction expected by the parameter's semantics.

**Acceptance Scenarios**:

1. **Given** two hull parameter sets that differ only in LOA, **When** both hulls are built, **Then** the longer-LOA hull has a strictly greater bounding-box length.
2. **Given** two parameter sets that differ only in beam_max, **When** both hulls are built, **Then** the wider hull has a strictly greater bounding-box width.
3. **Given** two parameter sets that differ only in deadrise_amidships, **When** both hulls are built, **Then** the deeper-V hull has a measurably sharper centerline V-angle at amidships (verified via a cross-section measurement).

---

### Edge Cases

- **Zero or negative dimensional parameter** (e.g. LOA = 0 m, draft = -1 m): system MUST raise `HullParameterError` citing the offending parameter name, its value, and its valid range, before attempting any FreeCAD construction.
- **Inverted sheer** (sheer_height_fwd < sheer_height_aft): system MUST detect this and raise `HullParameterError` by default — this almost always indicates a parameter mix-up. Spec deliberately does NOT support inverted-sheer hulls in v1.0.
- **Geometrically impossible hull** (e.g. LOA < beam_max, transom inside the bow plane): system MUST raise `HullParameterError` before invoking FreeCAD, with a message that identifies which two parameters conflict.
- **Extreme but valid parameter** (e.g. a parameter near a boundary listed in FR-004 / FR-008 — `deadrise_amidships` near 0° or 30°, `transom_angle` near 0° or 45°, `loa` just above `beam_max`): system MUST produce a valid hull if every per-field constraint and cross-field constraint in FR-004 + FR-012 is satisfied. If any boundary is violated, raise `HullParameterError` — never fail silently or produce subtly broken geometry.
- **FreeCAD construction failure** (e.g. lofted surface self-intersects due to a parameter interaction the validator did not catch): system MUST wrap the underlying FreeCAD error in `HullConstructionError`, attaching the parameter set as context, rather than letting an opaque FreeCAD traceback escape unwrapped.
- **Repeated invocation in the same document**: calling the hull-builder function twice in one document MUST produce two independent Bodies — FreeCAD's standard `Label` auto-numbering applies (e.g. `Hull`, `Hull001`), so no name-collision error is raised and no shared mutable state leaks between the Bodies (per FR-017).
- **Floating-point edge cases at topology closure** (e.g. a transom plane that intersects the hull surface at a vanishingly small angle): the topology computation MUST be deterministic for identical inputs — no nondeterministic ordering of edges or faces.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The hull module MUST expose a single public hull-builder function that accepts named keyword arguments for each hull parameter and returns a FreeCAD parametric Body added to the active FreeCAD document.
- **FR-002**: Every dimensional or angular hull parameter MUST be a named function argument with a documented default value. Magic numbers inside function bodies are forbidden per constitution principle I.
- **FR-003**: Default values for LOA, beam_max, draft, and freeboard MUST produce a hull whose measured principal dimensions match historical Storebro reference values within ±1% (per constitution principle IV).
- **FR-004**: The hull-builder function MUST validate every parameter for physical plausibility before invoking FreeCAD. Invalid parameters MUST raise an exception whose message includes the offending parameter name, the provided value, and the documented valid range.
- **FR-005**: For identical input parameters, the returned Body MUST have structurally identical geometry: identical topology counts (vertices, edges, faces), identical bounding box dimensions to within floating-point tolerance, and identical volume to within floating-point tolerance. Byte-identical serialization is the export module's responsibility; structural determinism is the hull module's responsibility.
- **FR-006**: The returned object MUST be a FreeCAD parametric `Part::Body` whose features are parametric FreeCAD operations — never raw `Mesh.Mesh` construction. Acceptable feature compositions:
    - **v0.1.0-alpha (current)**: Sketch features (`Part::Feature` polygons on positioned planes) plus `Part::Loft`, `Part::Mirroring`, and `Part::MultiFuse` from the Part workbench.
    - **v0.2.0 target (constitution principle III preferred)**: `Sketcher::Sketch` features (Body-internal, constrained) plus `PartDesign::AdditiveLoft` + `PartDesign::Mirrored`. Upgrade tracked in `CHANGELOG.md`.

    Either composition remains fully editable in the FreeCAD GUI (FR-007) and bans raw mesh construction (constitution principle III).
- **FR-007**: The returned Body and its features MUST remain editable in the FreeCAD GUI. Named hull dimensions MUST be exposed either as Body properties or as constrained sketch dimensions, so a GUI user can change a dimension and have FreeCAD recompute the hull.
- **FR-008**: The hull-builder function MUST accept at least the following named parameters, each with a documented default and documented unit: **LOA** (overall length, meters), **beam_max** (maximum beam, meters), **draft** (draft at amidships, meters), **deadrise_amidships** (deadrise angle at amidships, degrees), **sheer_height_aft** (sheer height at the transom, meters), **sheer_height_fwd** (sheer height at the bow, meters), **transom_angle** (transom rake angle from vertical, degrees), **freeboard** (freeboard at amidships, meters).
- **FR-009**: The hull MUST be symmetric about the centerline (the boat's longitudinal vertical plane). The module MUST NOT expose asymmetric hull parameters in v1.0.
- **FR-010**: The hull-builder function MUST produce a closed, watertight outer shell from the keel up to the sheer line. The shell MUST NOT include keel, skeg, rudder mounts, deck, cabin, or any non-shell appendage — those are out of scope for v1.0 and belong to later modules.
- **FR-011**: The hull module MUST NOT import or invoke any other storebro module (`deck`, `interior`, `export`, `cli`). It is a leaf module per the architecture rule in PROJECT-BRIEF.md.
- **FR-012**: The hull module MUST raise a typed validation error before any FreeCAD call when the parameter combination is geometrically impossible (e.g. LOA ≤ beam_max, sheer_height_fwd < sheer_height_aft when not explicitly opted-in, transom plane intersecting the bow plane).
- **FR-013**: The hull-builder function MUST check the running FreeCAD version on its first invocation per process (lazy check — importing `storebro.hull` MUST NOT trigger the check, to keep import lightweight for introspection and IDE tooling). If the version falls outside the range declared in `pyproject.toml` per constitution principle VII, the builder MUST raise `HullConstructionError` with a message of the form "unsupported FreeCAD version: <detected>, supported range: <min>–<max>" before attempting any geometry work.
- **FR-014**: All public hull functions MUST have a one-line docstring with at least one usage example, per `CLAUDE.md` DX guidance.
- **FR-015**: Parameter-validation failures (pre-FreeCAD) MUST raise `HullParameterError`, a custom exception class subclassing `ValueError`. FreeCAD-side construction failures (validator passed but FreeCAD could not build the geometry) MUST raise `HullConstructionError`, subclassing `RuntimeError`. Both classes are part of the public hull module API and MUST be importable from `storebro.hull`.
- **FR-016**: The hull-builder function MUST accept an optional `document` keyword argument (default `None`). If a FreeCAD document is supplied, the resulting Body is added to that document. If `None` and a FreeCAD document is currently active, the Body is added to the active document. If `None` and no FreeCAD document is active, the builder MUST create a new unnamed document, make it active, and add the Body to it. The builder MUST NOT silently mutate the name, label, or properties of a user-supplied document.
- **FR-017**: The hull-builder function MUST accept an optional `name` keyword argument with default `"Hull"`. The resulting Body's `Label` MUST be set to this value. If a Body with the same `Label` already exists in the target document, FreeCAD's standard auto-numbering applies (the new Body becomes `Hull001`, `Hull002`, etc.). This makes repeated invocations in the same document produce independently-addressable Bodies without raising a name-collision error.

### Key Entities

- **HullParameters**: The named set of dimensional and angular inputs that fully determine a hull's outer shell. Attributes include LOA, beam_max, draft, deadrise_amidships, sheer_height_aft, sheer_height_fwd, transom_angle, freeboard. Each attribute has a unit, a default value, a documented valid range, and a one-line description. May be implemented as keyword arguments, a dataclass, or both — the spec does not prescribe; `/speckit-plan` will decide.
- **Hull Body**: The FreeCAD parametric `Part::Body` (or equivalent) object returned by the hull builder. Composed of sketches and PartDesign features. Exposes hull dimensions as named properties so the FreeCAD GUI can edit them. Lives inside an active FreeCAD document supplied (or auto-created) by the caller.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With default parameters, the generated hull's measured LOA, beam_max, draft, and freeboard each fall within ±1% of the documented historical Storebro reference values (constitution principle IV).
- **SC-002**: Generating the default hull from a cold FreeCAD process completes in under 30 seconds on a developer laptop (Apple Silicon or comparable x86_64). Geometry build time is acceptable at "human-scale" seconds per `CLAUDE.md` priorities.
- **SC-003**: For any fixed input parameter set, two independent invocations of the hull builder produce Bodies whose volume, bounding-box dimensions, and topology counts are identical to within a documented floating-point tolerance (e.g. 1e-9 relative for dimensions, exact integer match for topology counts).
- **SC-004**: Every named hull parameter, when changed by ±10% from its default, produces a hull whose measured corresponding dimension changes monotonically in the expected direction — no silent no-op parameters.
- **SC-005**: A FreeCAD scripter who knows Python and has read the hull module's public docstrings can compose a custom hull into their own FreeCAD document in under 10 minutes without reading the implementation.
- **SC-006**: At least one geometry property test (volume, bounding box, topology count, or symmetry check) exists for every public function exported from the hull module.
- **SC-007**: Invalid parameter inputs raise `HullParameterError` with a message that names the offending parameter, its value, and its valid range — verified across at least 5 distinct invalid-input test cases. FreeCAD-side construction failures raise `HullConstructionError` wrapping the underlying FreeCAD exception — verified by at least 1 test case forcing a construction failure.
- **SC-008**: A boat restorer can open the generated `.FCStd` in the FreeCAD GUI, edit a named hull dimension on the Body's property panel, and see the hull recompute correctly — verified manually and recorded as a PR description note per constitution principle V.

## Assumptions

- **Scope of "hull"**: outer shell only, from keel line up to the sheer line, symmetric about the centerline. No keel fin, skeg, rudder mounts, propeller tunnel, deck, cabin trunk, hardtop, or internal structure. Those belong to later modules or to v1.1+.
- **Single-hull motor yacht**: catamarans, trimarans, sailing keels, and other multi-hull or sail-specific shapes are out of scope. v1.0 is the classic Storebro motor-yacht single planing/semi-displacement monohull.
- **Units**: SI throughout — meters for lengths, degrees for angles. Mixed-unit input (feet, inches) is not supported in v1.0; users convert externally.
- **Defaults source**: the precise canonical default values for LOA, beam_max, draft, etc. come from `docs/references/` cutaway drawings. PROJECT-BRIEF lists this as an open research question; `/speckit-plan` will pin specific values and cite the reference. The ±1% fidelity tolerance applies once those values are pinned.
- **FreeCAD runtime**: FreeCAD 1.1+ Python API available at runtime. Headless or GUI mode both supported. No dependency on any FreeCAD workbench beyond `Part` and `PartDesign`.
- **Hull construction approach**: lofted from station sketches between stem and transom is the most idiomatic FreeCAD pattern, but the spec does not prescribe — `/speckit-plan` will choose between lofting, additive pipe, or a sketch-and-pad pattern based on which produces the most editable parametric history.
- **Reproducibility scope**: hull module guarantees structural determinism (same topology, same dimensions). Byte-identical serialization to `.FCStd` is the export module's responsibility — it deals with timestamps, internal IDs, and any other FreeCAD-level nondeterminism in the document file.
- **Active FreeCAD document policy** (per FR-016): the hull-builder function takes an optional `document` keyword argument. If omitted and no document is active, the hull-builder function creates a new unnamed FreeCAD document and activates it. It never mutates user-supplied documents beyond adding the Body.
- **No upper bound on user creativity, but a hard validator gate**: users may pass any combination of named parameters, but the validator MUST reject combinations that produce geometrically impossible hulls before any FreeCAD code runs.
- **No logging or telemetry in v1.0**: the hull module emits no log output, no metrics, no progress events. Errors are surfaced as exceptions; success is the returned Body. Adding structured logging is explicitly deferred to v1.1+ if profiling demand emerges. Users who need to time a hull build can wrap the call with `time.perf_counter()` themselves.
- **Test environment**: pytest with the `requires_freecad` marker for geometry tests; pure-Python tests for validators, parameter handling, and exception types. CI runs both per constitution principle V.
