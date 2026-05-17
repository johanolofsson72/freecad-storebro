# Feature Specification: PartDesign Hull Upgrade

**Feature Branch**: `006-partdesign-hull-upgrade`

**Created**: 2026-05-17

**Status**: Draft — **BLOCKING for v1.0.0 tag**

**Input**: User description: "PartDesign hull upgrade — refactor the hull from legacy `Part::Loft` + `Part::Mirroring` + `Part::MultiFuse` (which FreeCAD 1.1+ rejects inside a `PartDesign::Body`) into a proper PartDesign body: 5 PartDesign sketches inside the Body, a `PartDesign::AdditiveLoft` additively building the half-hull solid, a `PartDesign::Mirrored` mirroring it across the XZ plane."

## Clarifications

### Session 2026-05-17

- Q: Where do the five datum planes attach — Body-local origin (`Body.Origin.YZ_Plane` + X-offset) or the document's global XZ plane? → A: **Body-local** (`Body.Origin.YZ_Plane` referenced with an X-offset per station). FreeCAD-idiomatic PartDesign convention; keeps the feature graph self-contained so transformations applied to the Body propagate to every sketch and datum without re-anchoring.
- Q: Do the eight named hull-parameter properties on the Body (`Loa`, `BeamMax`, `Draft`, `Freeboard`, `DeadriseAmidships`, `SheerHeightAft`, `SheerHeightFwd`, `TransomAngle`) drive the sketch dimensions via FreeCAD's expression engine, or are they purely informational? → A: **Informational** for v1.0.0 (matches v0.1.0-alpha behavior). Sketches are the source of truth for parametric editing per FR-004 + US2; the eight properties remain readable on the Body but do not propagate to sketch constraints. Expression-engine bidirectional binding (Body property → sketch constraint) is deferred to a future spec.
- Q: When `PartDesign::AdditiveLoft` produces a non-manifold result for an extreme but otherwise valid `HullParameters` combination, should the implementation attempt recovery (retry with adjusted spacing, re-tessellate) or fail fast? → A: **Fail fast** — raise `HullConstructionError` immediately, citing the offending parameter combination in the message. Matches spec 001 (input → `ValueError`, construction → `RuntimeError`) and spec 003 (deck rollback on failure) patterns. No retry, no fallback. The user re-runs with adjusted parameters.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Hull constructs successfully on FreeCAD 1.1+ (Priority: P1, MVP)

A library consumer — the CLI's `storebro build` invocation, a downstream Python script, or any of the four prior modules — calls `build_hull()` on a host with FreeCAD 1.1 or later. The call returns a populated `Hull` object whose `body` has a non-empty `.Shape`. No exceptions are raised by FreeCAD's PartDesign workbench rejecting incompatible feature types.

**Why this priority**: This is what blocks v1.0.0. The current v0.1.0-alpha hull fails with `ValueError: Body: object is not allowed` on FreeCAD 1.1.1 because legacy `Part::Loft` and `Part::Mirroring` features cannot be added to a `PartDesign::Body` container. Until this is fixed, the entire library is non-functional on a real FreeCAD host — every downstream module fails at its first call to `build_hull()`. Without P1 there is no v1.0.0, no `.FCStd` to open, no demo, nothing.

**Independent Test**: On a host with FreeCAD 1.1.1+, run `uv run pytest -m requires_freecad tests/geometry/test_hull_default_call.py -v`. Verify all tests in that file pass (specifically `test_default_call_returns_hull_with_body` and `test_default_call_within_sc002_budget`). Equivalent CLI invocation: `uv run storebro build --out /tmp/boat.FCStd` exits with code 0 and produces a non-empty file.

**Acceptance Scenarios**:

1. **Given** a FreeCAD 1.1.1 host with the package installed, **When** the user runs `build_hull()` with default parameters, **Then** the call returns a `Hull` object whose `body.Shape` is non-empty (positive volume, closed shape).
2. **Given** the same setup, **When** the user runs the full pipeline `build_hull() → build_deck(hull) → build_interior(hull, deck) → export_fcstd(hull.document, "/tmp/boat.FCStd")`, **Then** every step completes without exceptions and the resulting `.FCStd` contains a recognizable hull + deck + interior assembly.
3. **Given** the same setup, **When** the user runs `uv run pytest -m requires_freecad -v`, **Then** all 86 geometry tests that currently fail with `HullConstructionError: ValueError: Body: object is not allowed` now pass (the only allowed remaining failures are hash-baseline-not-seeded skips, addressed via the standing `refresh_hashes.py` workflow).

---

### User Story 2 — Hull is GUI-editable per the FreeCAD-idiomatic principle (Priority: P2)

A boat restorer opens a generated `.FCStd` in the FreeCAD GUI. They see the hull as a single `PartDesign Body` in the tree view. Expanding the Body shows five named sketches (one per station) and the PartDesign feature stack that produces the solid. Double-clicking any sketch opens it in the sketcher with handles on its construction geometry. Dragging a handle and accepting the change causes the hull to deform in real-time when the document recomputes.

**Why this priority**: Constitution principle III (FreeCAD-Idiomatic) says generated documents MUST remain editable in the FreeCAD GUI with parametric history intact. The v0.1.0-alpha hull's `Part::Loft` features technically appeared in the GUI but were structurally orphaned from the `PartDesign Body` (the cause of the construction failure), making the parametric history meaningless. The PartDesign rebuild produces a proper feature graph that matches how a FreeCAD user would build the hull by hand. Without P2 the hull is non-idiomatic — a black box solid that the GUI can show but not edit.

**Independent Test**: Open `/tmp/storebro_v1_signoff.FCStd` in the FreeCAD GUI. Verify (a) the Body tree shows five sketches named `HullStation1` through `HullStation5` (or equivalent), (b) double-clicking `HullStation3` opens the amidships sketch in the sketcher view, (c) selecting a sketch handle, dragging it 100 mm, accepting, and recomputing causes the hull's amidships beam to visibly change in the 3D view.

**Acceptance Scenarios**:

1. **Given** a generated `.FCStd` open in FreeCAD GUI, **When** the user expands the Body in the tree, **Then** five named station sketches and a `PartDesign::AdditiveLoft` feature (or equivalent named feature) are visible as children of the Body.
2. **Given** the same setup, **When** the user double-clicks a station sketch, **Then** the sketcher view opens with that station's profile visible and editable.
3. **Given** the user modifies a station-sketch dimension and recomputes, **When** the document recompute completes, **Then** the hull's outer shape reflects the change without any error dialog and without breaking the PartDesign feature graph.

---

### User Story 3 — Backward compatibility for library consumers (Priority: P2)

The four downstream public modules (`storebro.export`, `storebro.deck`, `storebro.interior`, `storebro.cli`) continue to consume the `Hull` return value without code changes. The `Hull.body` attribute exposes a `.Shape`, `.Label`, and the named parameter properties (`Loa`, `BeamMax`, `Draft`, `Freeboard`, `DeadriseAmidships`, `SheerHeightAft`, `SheerHeightFwd`, `TransomAngle`) just like the v0.1.0-alpha implementation did.

**Why this priority**: Spec 005 already shipped (commit `b21077e`); it cannot be retrofitted without rework. The deck, interior, and export modules each have an integration surface that depends on `hull.body.Shape` and `hull.document`. If those surfaces change, every downstream module breaks and the v1.0.0 milestone takes a much larger blast radius than just the hull. P2 keeps the rebuild surgically scoped to the hull's internal feature graph; the public dataclass shape is preserved.

**Independent Test**: With the rebuilt hull module installed, run `uv run pytest tests/unit/ -v` (no FreeCAD needed) — every unit test that touches `HullParameters`, `Hull`, or any downstream module that imports `from storebro.hull import ...` continues to pass without modification. Then `uv run pytest -m requires_freecad tests/geometry/test_deck_default_call.py tests/geometry/test_export_fcstd.py tests/geometry/test_cli_build_default.py -v` — all green, demonstrating that the deck, export, and CLI consumers work unchanged.

**Acceptance Scenarios**:

1. **Given** the rebuilt hull module is installed, **When** any downstream module's existing test that depends on `hull.body.Shape` or `hull.document` runs, **Then** it passes without modification to the consumer's source code.
2. **Given** the same setup, **When** a caller reads `hull.body.Loa` (or any of the eight named hull-parameter properties), **Then** the property exists on the Body and equals the corresponding `HullParameters` field value.
3. **Given** the same setup, **When** a caller pickles or repr-formats a `Hull` instance, **Then** the textual representation includes the same field names and types as the v0.1.0-alpha version (`body`, `parameters`, `document`, `label`, `build_duration_seconds`).

---

### Edge Cases

- **Recompute fails mid-construction**: If FreeCAD's recompute fails (e.g., the sketches produce a non-manifold loft), the document MUST be left in a clean state — no orphan sketches, no half-built Body. The existing `HullConstructionError` rollback discipline (spec 001 + spec 003 rollback patterns) is preserved.
- **User passes a pre-existing FreeCAD document with conflicting object names**: The hull builder MUST auto-number Body and sketch labels (`HullBody001`, `HullStation1_001`, etc.) just like the v0.1.0-alpha implementation did. No silent overwrites.
- **Custom parameters at boundary values**: Hull constructed with extreme but valid parameters (LOA=5.0 m, beam_max=1.5 m, deadrise=30°) MUST still produce a closed manifold solid. If the chosen station spacing collapses two sketches into the same X coordinate, raise `HullConstructionError` with a clear message naming the parameter combination.
- **Determinism across FreeCAD recompute orderings**: PartDesign feature recompute order MUST be deterministic — same inputs produce byte-identical `.FCStd` output bytes (per constitution II). If FreeCAD's recompute is order-sensitive on multi-feature Bodies, the implementation MUST stabilize the order (e.g., fixed `Body.Tip` assignment, explicit feature placement).
- **Hash baselines invalidated**: The PartDesign feature graph is structurally different from the legacy Part workbench graph; the produced `.FCStd` / `.step` / `.stl` / `.brep` SHA-256 hashes WILL differ from any baseline that was previously recorded. Hash baselines MUST be refreshed via `tests/geometry/fixtures/refresh_hashes.py` as part of this spec's polish phase.
- **FreeCAD 1.1 vs 1.0**: Constitution principle VII requires the supported range to remain `>=1.1, <2.0`. The PartDesign rebuild MUST NOT introduce a dependency on FreeCAD 1.2+ features (e.g., new PartDesign primitives that landed after 1.1.1). Test on 1.1.x.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `build_hull()` MUST construct a hull successfully on FreeCAD 1.1.0 and later — every supported version in the `[tool.freecad-storebro] supported_freecad` range. Specifically, the implementation MUST NOT use feature types that any supported FreeCAD version rejects when added to a `PartDesign::Body`.
- **FR-002**: The hull's parametric construction MUST use FreeCAD's PartDesign workbench: a `PartDesign::Body` container, station profiles modeled as PartDesign sketches attached to PartDesign datum planes (one datum per station), a single PartDesign additive feature (the loft) producing the half-hull solid, and a single PartDesign mirror feature producing the full hull from the half by reflecting across the centerline plane (XZ plane).
- **FR-003**: All five station sketches MUST be children of the Body in the FreeCAD GUI tree view, accessible by their named labels (`HullStation1` through `HullStation5`, corresponding to the transom, aft, amidships, fwd, and stem profiles respectively).
- **FR-004**: The hull's PartDesign feature graph MUST remain editable: a GUI user MUST be able to double-click any station sketch, modify its construction geometry, and recompute the document to see the hull deform accordingly. No feature shall be created in a "read-only" or "locked" state that prevents downstream editing.
- **FR-005**: The public `Hull` dataclass surface MUST remain unchanged from the v0.1.0-alpha implementation: `body` (FreeCAD object with `.Shape`), `parameters` (`HullParameters` instance), `document` (FreeCAD document), `label` (string), `build_duration_seconds` (float). No fields added, removed, or renamed.
- **FR-006**: The `Hull.body` attribute MUST expose the same eight named parameter properties (`Loa`, `BeamMax`, `Draft`, `Freeboard`, `DeadriseAmidships`, `SheerHeightAft`, `SheerHeightFwd`, `TransomAngle`) as the v0.1.0-alpha implementation, with the same value types (floats in meters / degrees). Per clarify Q2, these properties are **informational only** for v1.0.0 — they reflect the parameters used to build the hull but do NOT drive sketch dimensions via FreeCAD's expression engine. Sketches are the source of truth for parametric editing in the GUI; bidirectional Body-property→sketch binding is deferred to a future spec.
- **FR-007**: The `Hull.body.Shape` MUST be a closed, manifold solid (no open edges, positive volume) for all valid `HullParameters` in the supported parameter envelope.
- **FR-008**: `build_hull()` MUST be byte-deterministic per constitution principle II: two consecutive invocations with identical parameters in fresh FreeCAD documents MUST produce solids whose `.Shape` has identical volume, identical bounding box, identical face count, and identical edge count, AND whose `.FCStd` export through `export_fcstd()` produces byte-identical archives.
- **FR-009**: Every currently-failing geometry test in `tests/geometry/` (86 tests as of register-rewrite entry on 2026-05-17) MUST pass on FreeCAD 1.1.1 after this spec's implementation lands. The pass count includes hull tests (constructs, dimensions, determinism, topology, parametricity, GUI editability, visual signoff), deck tests (since deck depends on hull), interior tests, export tests (since they each call `build_hull()` first), and the CLI build tests.
- **FR-010**: The implementation MUST NOT introduce raw mesh manipulation (no `Mesh.Mesh()` calls, no vertex-by-vertex generation). Per constitution principle III, all geometry construction stays inside FreeCAD's PartDesign B-rep abstractions.
- **FR-011**: When `build_hull()` fails (FreeCAD version unsupported, recompute fails, parameters out of envelope), it MUST raise `HullConstructionError` with the same attribute shape as the v0.1.0-alpha implementation: `parameters` (the offending `HullParameters`), `underlying` (the original exception, where applicable), `detected_version` (when version-check fails), `supported_range` (when version-check fails). Existing tests that catch and inspect `HullConstructionError` MUST continue to work.
- **FR-012**: If a `build_hull()` call partway through construction raises an exception, the document state MUST be left clean: no orphan sketches, no half-built Body, no datum planes left dangling. The rollback discipline mirrors spec 003's deck rollback pattern.
- **FR-013**: The hull's PartDesign `Body.Tip` MUST be set to the mirror feature (the final feature in the graph). This is what FreeCAD uses to determine which feature's shape is the Body's "output" — the deck and interior modules consume `hull.body.Shape`, which reads from `Body.Tip`.
- **FR-014**: Station sketch construction geometry (the actual profile curves) MUST use the same dimensional parameters as the v0.1.0-alpha station profiles, so the resulting hull's principal dimensions (LOA, beam, draft) match within constitution principle IV's ±1% reference fidelity bar against the historical RC34 1972 reference. No re-derivation of the profile equations.

### Key Entities

- **Hull Body**: A `PartDesign::Body` document object containing the parametric feature graph. Carries the named parameter properties and serves as the editable container in the FreeCAD GUI tree. Public surface is reachable via `Hull.body`.
- **Station Sketch**: A `Sketcher::SketchObject` attached to a PartDesign datum plane at a specific X coordinate along the hull. Five instances total; each holds the construction geometry for one station's half-profile.
- **Datum Plane**: A `PartDesign::Plane` attached to the Body's local YZ reference frame, offset to a specific station X coordinate. Five instances, one per station sketch.
- **Additive Loft Feature**: A `PartDesign::AdditiveLoft` consuming the five station sketches in order and producing a half-hull solid as the Body's intermediate state.
- **Mirror Feature**: A `PartDesign::Mirrored` reflecting the additive loft across the Body's XZ plane to produce the full closed hull. This feature is the `Body.Tip`.
- **Hash Baselines**: The `tests/geometry/fixtures/expected_hashes.toml` known-good SHA-256 digests for each output format. Refreshed as part of this spec's polish phase because the PartDesign feature graph produces structurally different `.FCStd` bytes than the legacy implementation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 86 of 86 currently-failing geometry tests pass after implementation. Verified by `uv run pytest -m requires_freecad -v` reporting `86 passed` or higher (plus any skips for unseeded hash baselines, which are addressed in the same spec via baseline refresh).
- **SC-002**: `build_hull()` completes in under 30 seconds on a developer laptop (same budget as the v0.1.0-alpha; the PartDesign overhead is acceptable as long as total build time stays well under spec 002's 3-minute end-to-end target).
- **SC-003**: A boat restorer can open a generated `.FCStd` in the FreeCAD GUI, drag a single station-sketch handle 100 mm, recompute the document, and observe the hull deform — all in under 30 seconds of mouse interaction. Verified manually as part of constitution principle V's visual signoff.
- **SC-004**: `build_hull()` is byte-deterministic. Two back-to-back invocations with identical parameters produce identical SHA-256 digests when exported via `export_fcstd`. Verified by `tests/geometry/test_hull_determinism.py` (passing).
- **SC-005**: No public API surface changes from the v0.1.0-alpha. Verified by `tests/unit/test_hull_public_docstrings.py`, `tests/unit/test_hull_parameters.py`, `tests/unit/test_hull_errors.py` continuing to pass without modification.
- **SC-006**: All four downstream modules (`storebro.export`, `storebro.deck`, `storebro.interior`, `storebro.cli`) work end-to-end without source code changes. Verified by `uv run storebro build --out /tmp/boat.FCStd` exiting with code 0 on a FreeCAD 1.1.1 host.
- **SC-007**: The PartDesign feature graph is GUI-editable. Verified by the constitution-mandated visual signoff: PR description records "Visually verified in FreeCAD: 1.1.x on macOS arm64 — dragged HullStation3 handle, hull recomputed and beam dimension changed correspondingly."

## Assumptions

- **FreeCAD 1.1.0+ provides `PartDesign::AdditiveLoft` and `PartDesign::Mirrored` features that match the PartDesign Body model.** Both have been part of PartDesign since at least FreeCAD 0.19; FreeCAD 1.1.1 (current test host) confirms availability.
- **Station-sketch profile equations from the v0.1.0-alpha remain correct.** The earlier `_compute_stations(params)` function produces the right 2D half-profile curves; only the FreeCAD construction mechanics around those curves changes. The profile math is not re-derived.
- **Each station sketch attaches to its own datum plane (one `PartDesign::Plane` per station, parallel to YZ at the station X coordinate).** This is the FreeCAD-idiomatic way to position PartDesign loft profiles. The alternative — five sketches all on the same global YZ plane — is invalid for `PartDesign::AdditiveLoft`.
- **`Body.Tip` is the mirror feature (the final feature in the chain).** `hull.body.Shape` reads from `Body.Tip`, so this assignment is what makes the downstream modules see the full mirrored hull.
- **Hash baselines reset is part of this spec.** The legacy implementation's hash baselines (if any) are invalidated; the new PartDesign feature graph produces structurally different output bytes. Polish phase includes running `refresh_hashes.py`, eyeballing the diff, and committing the new baselines.
- **Geometry build time stays under the existing 30-second hull budget on a developer laptop.** PartDesign overhead is acceptable; if a measurement shows we exceeded the budget by more than 30%, escalate as a separate optimization spec, not a blocker for this one.
- **No FreeCAD GUI is required during automated tests.** Geometry tests construct the document in a headless FreeCAD Python session; the GUI editability check (SC-003 / SC-007) is a manual signoff captured in the PR description per constitution V.
- **The `_freecad_check` lazy version probe continues to work unchanged.** The probe reads `pyproject.toml`'s `[tool.freecad-storebro]` table and raises `HullConstructionError` on unsupported versions; this spec does not touch that helper.
