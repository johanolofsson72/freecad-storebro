# Feature Specification: Propulsion — Engine Bay, Engine, Shaft, Propeller & Rudder

**Feature Branch**: `014-propulsion`

**Created**: 2026-06-01

**Status**: Draft

**Input**: User description: "014-propulsion — Parametric propulsion module for the Storebro RC34: engine bay, engine block, propeller shaft, propeller, and rudder, mounted in the hull aft section. Reuses the FreeCAD-idiomatic PartDesign Body construction pattern established in the hull and deck modules. New public API: build_propulsion(...) composing the five components, each driven by frozen parameter dataclasses with sensible RC34-era defaults (twin or single inboard diesel layout per the vintage Storebro). Components seat on actual sampled hull geometry. Integrate into the CLI build composition and the export pipeline. v1.1+ feature — first new geometry surface beyond hull+deck+interior."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A complete single-screw propulsion train (Priority: P1)

A FreeCAD scripter builds the Storebro model and gets a complete, correctly placed inboard propulsion installation: an engine bed (stringers) in the bilge, an engine block seated on the bed, a propeller shaft running aft and down through the hull bottom at a realistic shaft angle, a propeller aft of the shaft exit, and a rudder aft of the propeller. The five components compose into one `build_propulsion(...)` call and seat on the *actual* sampled hull geometry, not estimated coordinates.

**Why this priority**: This is the MVP — a single complete, dimensionally plausible propulsion train is what makes the model read as a powered yacht instead of an empty hull. Every other story builds on the single-train geometry. It is independently valuable even if the twin variant never ships.

**Independent Test**: Call `build_propulsion(hull, deck)` with `engine_count=1`; confirm all five components exist as separate FreeCAD bodies, the shaft is angled down-and-aft, the propeller and rudder sit below the waterline aft of the shaft exit, and the engine bed sits in the bilge above the keel.

**Acceptance Scenarios**:

1. **Given** a built hull and deck, **When** `build_propulsion(hull, deck, parameters=PropulsionParameters(engine_count=1))` runs, **Then** exactly one engine bed, one engine block, one shaft, one propeller, and one rudder body are produced and returned in the `Propulsion` aggregate.
2. **Given** the default shaft angle, **When** the shaft is built, **Then** the shaft's forward (engine-coupling) end is higher than its aft (propeller) end, and the aft end exits below the hull bottom at the design shaft-exit station.
3. **Given** the propeller and rudder, **When** they are built, **Then** the propeller hub centre lies aft of the shaft-exit point on the shaft axis, and the rudder lies aft of the propeller, both with their lowest extent below the waterline (Z < 0).
4. **Given** the engine bed and engine block, **When** they are built, **Then** the engine block rests on the bed, and both lie within the hull's interior envelope at their longitudinal station (above the keel, below the deck, inboard of the topsides) — no part of the engine protrudes through the hull shell.

---

### User Story 2 - Twin-screw configuration (Priority: P2)

The scripter selects the twin-engine layout characteristic of the vintage Storebro motor yacht and gets a port and a starboard propulsion train — two engine beds, two engines, two shafts, two propellers — mirrored about the centreline, each offset outboard by a parametric amount, with the rudder(s) placed per the configured rudder count.

**Why this priority**: Twin diesels are the historically faithful RC34 configuration, but the geometry is the single-train builders applied twice with a transverse offset and a mirror. It depends entirely on P1's per-train builders, so it is sequenced second.

**Independent Test**: Call `build_propulsion(hull, deck)` with `engine_count=2`; confirm two complete trains exist, mirrored about Y=0, each shaft/propeller offset outboard by the configured engine offset, and the rudder count matches the configuration.

**Acceptance Scenarios**:

1. **Given** `engine_count=2`, **When** `build_propulsion` runs, **Then** two engine beds, two engines, two shafts, and two propellers are produced, with the port set at +Y offset and the starboard set at the mirrored −Y offset.
2. **Given** `engine_count=2` and the default rudder configuration, **When** the rudder(s) are built, **Then** the rudder count matches the configured value and each rudder is positioned aft of its associated propeller (or on the centreline for a single-rudder twin).
3. **Given** `engine_count=2`, **When** the trains are built, **Then** neither train's geometry overlaps the centreline keel nor the opposite train (the outboard offset keeps them clear).

---

### User Story 3 - CLI and export composition (Priority: P3)

A user runs `storebro build --layout Alternativ3 --out boat.FCStd` (or any export format) and the resulting model includes the propulsion bodies alongside hull, deck, and interior, fully editable in the FreeCAD GUI and present in the STEP / STL / BREP / FCStd exports.

**Why this priority**: Composition and export are the delivery surface — without them the propulsion geometry exists only when called directly from Python. It is last because it depends on P1 (and optionally P2) producing valid bodies first.

**Independent Test**: Run the CLI build to an `.FCStd`; open it and confirm the propulsion bodies are present in the document tree; export to STEP/STL/BREP and confirm the propulsion solids appear in each artifact.

**Acceptance Scenarios**:

1. **Given** the CLI build command, **When** it runs, **Then** `build_propulsion` is invoked in the composition after `build_deck`/`build_interior` and its bodies are added to the same document.
2. **Given** an `.FCStd` export of the composed document, **When** the file is opened in FreeCAD, **Then** all propulsion bodies appear in the document tree with their parametric history (sketches + features) intact.
3. **Given** a STEP/STL/BREP export of the composed document, **When** the artifact is inspected, **Then** the propulsion solids are present in the export.

---

### Edge Cases

- **Engine count out of range**: `engine_count` outside `{1, 2}` is rejected by validation with a clear error naming the offending value and the valid set.
- **Shaft angle boundary**: a shaft angle of 0° (horizontal) is valid; a negative angle or an angle steep enough to drive the shaft exit above the waterline or outside the hull's aft underbody is rejected.
- **Outboard offset too large** (twin): an `engine_offset_y` that would push a train outboard past the hull topsides at the engine station is rejected by validation.
- **Component clearance**: with default parameters, the propeller tip and rudder must clear the hull bottom; the engine must clear the keel below and the cabin sole/deck above. A parameter override that violates these clearances is rejected.
- **No hull modification**: propulsion components are separate additive bodies seated on/through the hull; the hull solid itself is never booleaned (avoids the non-manifold fragility seen in specs 009/011). The shaft passes through a stern-tube/shaft-log boss that is its own additive body — the hull shell is not cut.
- **Reproducibility / rollback / manifold**: identical inputs produce byte-identical geometry; a mid-build failure rolls the document back to its pre-call state; every produced solid is a single closed manifold so STL export is unaffected.
- **Missing deck**: `build_propulsion` requires a built hull; the deck is used only where a component must reference deck-top Z (e.g. clearance ceiling). If no deck is supplied, the engine-height ceiling falls back to the hull sheer (documented assumption).

## Clarifications

### Session 2026-06-01

- Q: Default engine configuration — single or twin screw? → A: Twin (`engine_count=2`), the historically faithful RC34 motor-yacht layout; single (`engine_count=1`) fully supported via the parameter.
- Q: Default rudder count, especially for the twin layout? → A: One rudder per screw — `rudder_count` defaults to `engine_count` (single rudder for single screw, twin rudders for twin screws); overridable.
- Q: How is the shaft's hull penetration modeled — boolean cut through the hull, or additive boss? → A: Additive stern-tube/shaft-log boss as its own body; the hull solid is never booleaned (preserves manifold integrity per specs 009/011).
- Q: Default propeller blade count? → A: 3 blades (typical vintage diesel inboard), parametric via the propeller parameter dataclass.
- Q: Default shaft down-angle? → A: 10° down-and-aft, parametric and validated so the shaft exit stays in the aft underbody below the waterline.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose a public `build_propulsion(hull, deck=..., parameters=..., *, document=..., name=...)` function that composes five propulsion components — engine bed (stringers), engine block, propeller shaft, propeller, and rudder — and returns a `Propulsion` aggregate wrapper, mirroring the `build_hull`/`build_deck` signature and return-shape conventions.
- **FR-002**: Each component MUST be driven by a frozen parameter dataclass with RC34-era defaults, aggregated by a `PropulsionParameters` composite (mirroring `DeckSuperstructureParameters`/`DeckHardwareParameters`), with validation in `__post_init__` raising a module-specific `PropulsionParameterError` that names the offending value and its valid range.
- **FR-003**: Components MUST seat on the *actual* sampled hull geometry (hull bottom / keel-depth / topside envelope at the relevant longitudinal station) rather than analytical estimates, reusing the hull-sampling approach already used by the deck module.
- **FR-004**: The propeller shaft MUST be built at a parametric down-and-aft shaft angle (default 10°), with its forward end at the engine coupling and its aft end exiting below the hull bottom at the design shaft-exit station; the propeller (default 3 blades, parametric) MUST sit aft of the shaft exit on the shaft axis and the rudder aft of the propeller.
- **FR-005**: The engine bed and engine block MUST sit within the hull interior envelope at the engine station — above the keel, below the deck/sole, inboard of the topsides — with no part protruding through the hull shell.
- **FR-006**: The system MUST support both single-screw (`engine_count=1`) and twin-screw (`engine_count=2`, the default) configurations; the twin configuration produces port and starboard trains mirrored about the centreline, each offset outboard by a parametric `engine_offset_y`. The `rudder_count` MUST default to `engine_count` (one rudder per screw) and be overridable.
- **FR-007**: The system MUST NOT apply any boolean operation to the hull solid; propulsion bodies are separate additive bodies. The shaft penetration is modeled as an additive stern-tube/shaft-log boss body, not a cut through the hull shell (preserves the hull's manifold integrity per specs 009/011 lessons).
- **FR-008**: Every produced propulsion solid MUST be a single closed manifold (`Solids == 1` and `isValid()`), so STL export is unaffected; this is asserted as a post-build guard mirroring the spec 011/012 manifold guards.
- **FR-009**: Construction MUST be FreeCAD-idiomatic PartDesign (`Body` + `Sketch` + `Pad`/`AdditiveLoft`/`Revolution`/`Pocket` as appropriate) — no raw mesh generation — and the generated bodies MUST remain editable in the FreeCAD GUI with parametric history intact (constitution principle III).
- **FR-010**: A mid-build failure MUST roll the document back to its pre-call state by removing every object added during the call, in reverse order, mirroring the `build_hull`/`build_deck` rollback pattern (accumulate `added`, reverse `removeObject` on exception; wrap unexpected errors as `PropulsionConstructionError`, pass `PropulsionParameterError` through).
- **FR-011**: `build_propulsion` MUST be composed into the CLI build command after the deck/interior steps, adding its bodies to the same document so they flow into all export formats (FCStd / STEP / STL / BREP) without any explicit export-registration step.
- **FR-012**: Geometry MUST be reproducible — identical input parameters produce byte-identical output (constitution principle II): no timestamps, no nondeterministic topology ordering, no environment-dependent paths.
- **FR-013**: The public API surface added by this spec (`build_propulsion`, `Propulsion`, `PropulsionParameters`, the per-component parameter dataclasses, `PropulsionParameterError`, `PropulsionConstructionError`, and the component wrapper dataclasses) MUST be additive; existing hull/deck/interior/CLI/export callers MUST continue to work unchanged.
- **FR-014**: The version MUST be bumped MINOR (1.0.7 → 1.1.0 — first new public geometry surface / new module per semver and the v1.1+ roadmap) and `storebro.__version__` kept in sync with `pyproject.toml`, guarded by the existing version-consistency test.
- **FR-015**: Materials, colors, and transparency are OUT OF SCOPE (spec 015); geometry fidelity is representative (consistent with the deck-hardware fidelity level), not a CAD-faithful diesel or airfoil-accurate propeller.

### Key Entities

- **Propulsion** (aggregate): the wrapper returned by `build_propulsion`, holding the document, the resolved parameters, and references to each produced component (engine bed(s), engine(s), shaft(s), propeller(s), rudder(s)), plus build metadata — analogous to the `Hull`/`Deck` aggregates.
- **Engine Bed / Stringers**: longitudinal structural members in the bilge that the engine sits on; seated above the keel at the engine station.
- **Engine Block**: a representative inboard diesel block (a box-like solid with basic top features), resting on the bed; one per engine.
- **Propeller Shaft**: a cylindrical shaft on the down-and-aft shaft axis, from the engine coupling to aft of the hull exit; includes the additive stern-tube/shaft-log boss at the hull penetration.
- **Propeller**: a hub plus a parametric number of representative blades, aft of the shaft exit on the shaft axis, below the waterline.
- **Rudder**: a foil-plate blade plus a vertical stock, aft of the propeller, below the waterline; count configurable (single or twin).
- **PropulsionParameters** (composite): aggregates the per-component parameter dataclasses plus layout fields (`engine_count`, `engine_offset_y`, `rudder_count`, shaft angle/station, etc.); the single entry point a caller overrides.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A default `build_propulsion(hull, deck)` produces a complete propulsion installation (all five component types) with zero errors.
- **SC-002**: With `engine_count=1`, exactly one of each component is produced; with `engine_count=2`, two beds/engines/shafts/propellers are produced, mirrored about Y=0, and the rudder count matches the configuration.
- **SC-003**: The shaft is angled down-and-aft (forward end Z > aft end Z), the shaft exit is below the hull bottom and above no higher than the waterline at the exit station, and propeller→rudder ordering along the axis is preserved (propeller aft of exit, rudder aft of propeller).
- **SC-004**: No propulsion solid intersects the hull shell from outside-in (the engine sits inside the hull envelope; the running gear sits below the hull bottom); each propulsion solid is a single closed manifold (solid count = 1, valid).
- **SC-005**: Two consecutive builds with identical parameters produce byte-identical geometry (checksum-equal exports).
- **SC-006**: A mid-build failure rolls the document back to its pre-call state (no orphaned objects remain).
- **SC-007**: The CLI build composes propulsion into the document and all four export formats include the propulsion solids.
- **SC-008**: `uv run pytest`, `uv run ruff check .`, and `uv run mypy src/` all pass; the composed model opens and is visually verified in FreeCAD against the reference profile (constitution principle V).

## Assumptions

- **Twin default, single supported**: the default configuration is twin-screw (`engine_count=2`), the historically faithful RC34 motor-yacht layout; single-screw (`engine_count=1`) is fully supported via the parameter. (`/clarify` may confirm or flip this default.)
- **No hull boolean**: the hull solid is never modified; propulsion bodies are additive and seated on/through sampled hull geometry, with the shaft penetration modeled as an additive stern-tube boss — chosen to avoid the non-manifold STL-export failures seen in specs 009 and 011.
- **Representative fidelity**: the engine block, propeller blades, and rudder foil are representative/stylized solids at the deck-hardware fidelity level, not CAD-faithful machinery or airfoil-accurate blades. Detailed machinery is a possible future spec.
- **Shaft angle default**: 10° down-and-aft, parametric and validated so the shaft exit stays in the hull's aft underbody below the waterline. Default propeller is 3-bladed; default `rudder_count` equals `engine_count`.
- **Deck optional for ceiling**: the deck is used to derive the engine-height clearance ceiling; if no deck is supplied, the ceiling falls back to the hull sheer at the engine station.
- **Coordinate convention**: bow = XMax, stern = XMin, waterline = Z=0, port = +Y / starboard = −Y, FreeCAD-internal millimetres — consistent with hull/deck (the interior meter-scale issue, spec 017, does not affect this module since it samples the mm-scale hull).
- **Scale**: propulsion is built at the hull's mm scale; the interior-scale fix (spec 017) is independent and not addressed here.
- **Materials/colors**: out of scope — spec 015.
- **Version bump**: MINOR (1.0.7 → 1.1.0) because this is the first new public geometry module beyond the v1.0 hull/deck/interior/export/CLI set.
