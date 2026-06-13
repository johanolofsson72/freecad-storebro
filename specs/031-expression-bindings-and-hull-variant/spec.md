# Feature Specification: Expression Bindings + Hard-Chine Hull Variant

**Feature Branch**: `master` (solo / direct-push — no feature branch per spec-register rule)

**Created**: 2026-06-13

**Status**: Draft (closes PARTIAL — item 2 spike-deferred per user decision 2026-06-13)

**Input**: Split from spec 029 (2026-06-11). Two behavior-changing items that did not belong in a
spec-only hardening spec: (1) an optional hard-chine hull variant knob, and (2) FreeCAD
expression-engine bindings so GUI edits propagate through the parametric history.

## Context & scope decision

This spec carries two independent items. A **user scope decision on 2026-06-13** ("Defer bindings,
ship variant") sets the boundary for this run:

- **Item 1 — Hard-chine hull variant: IMPLEMENTED this spec.** A `hull_variant` knob on
  `build_hull` (`src/storebro/hull.py`), modeled on `deck.py`'s
  `superstructure_variant: Literal["standard", "ds"]`. Verifiable to the same degree as spec 030
  (unit tests here; `requires_freecad` geometry tests for the maintainer).
- **Item 2 — Expression-engine bindings: SPIKE-DEFERRED this spec.** FreeCAD is unavailable on the
  dev machine, so the byte-reproducibility of `setExpression` strings written into `Document.xml`
  (the spec 028 surface) cannot be verified. The register pre-sanctioned "byte-reproducible OR
  spike-deferred"; with verification impossible here, shipping unverified `setExpression` code would
  violate constitution II (reproducibility MUST) and the Definition of Done. The design is
  documented (see research.md) and tracked as a `deferred` item to revisit in a FreeCAD-equipped
  session. **No `setExpression` code ships in this spec.**

Spec 031 therefore **closes PARTIAL**: item 1 done, item 2 deferred with a recorded reason.

## Clarifications

### Session 2026-06-13

All four questions auto-picked the recommended answer (full-track auto-pick per the feature-pipeline
hook). The item-1/item-2 scope split itself was the user decision recorded above, not a clarify Q.

- Q: How is the hard-chine reshaping parameterised on the 5-vertex pentagon? → A: **Move the chine
  vertex (v1, bottom-outer) outboard toward the topside half-beam and up toward the topside-turn
  (z closer to 0)** via named ratio constants, which flattens the bottom panel (keel→chine) and
  steepens/shortens the topside panel (chine→turn) into a sharper knuckle. Vertex *count* and the
  other four vertices' roles are unchanged (loft-safe); `"standard"` leaves all vertices at today's
  positions.
- Q: Where does `hull_variant` live — a `build_hull` keyword or a `HullParameters` field? → A: **A
  `build_hull` keyword** (`hull_variant: Literal["standard","hard_chine"] = "standard"`), mirroring
  `superstructure_variant` on `build_deck` exactly (which is a function keyword, not a
  `DeckParameters` field). Keeps the default path and the dataclass byte-identical.
- Q: How is the SC-002 "measurable difference" asserted? → A: **At the amidships station the chine
  half-beam (`half_beam_at_bottom`) is a larger fraction of the topside half-beam
  (`half_beam_at_top`) for `hard_chine` than for `standard`**, by a named margin — i.e. the chine
  is measurably pushed outboard. Checkable from the station profile and the built geometry.
- Q: How is the manifold-or-fallback observable (FR-006/FR-010)? → A: **The `Hull` wrapper records
  the requested `hull_variant` AND a `variant_applied: bool`** that is `False` when the hard-chine
  loft failed and the build fell back to the standard hull (mirrors spec 030's fell-back pattern).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build a hard-chine hull (Priority: P1)

A modeler passes `hull_variant="hard_chine"` (CLI `--hull-variant hard_chine`) and gets a hull whose
cross-section reads as a pronounced single hard chine — flatter bottom, more vertical topside, a
sharper chine knuckle — instead of the current softer multi-chine form. The default
(`"standard"`) is unchanged and byte-identical to today's hull.

**Why this priority**: This is the implemented deliverable of the spec. There is no smaller viable
slice — the variant either exists and is selectable or it does not.

**Independent Test**: Build with `hull_variant="standard"` and `hull_variant="hard_chine"` on the
same parameters; the standard build is byte-identical to the pre-031 hull, the hard-chine build is a
single manifold solid whose cross-section differs measurably (sharper chine), and both reproduce
byte-identically on a second build in the same process.

**Acceptance Scenarios**:

1. **Given** default parameters and `hull_variant="standard"`, **When** the hull is built, **Then**
   the geometry is byte-identical to the pre-031 hull (the default path is untouched).
2. **Given** default parameters and `hull_variant="hard_chine"`, **When** the hull is built,
   **Then** the hull is a single manifold solid (`Solids == 1`, `isValid()`) whose chine is more
   pronounced than the standard hull (measurably flatter bottom / sharper chine angle).
3. **Given** an unrecognised `hull_variant` value, **When** `build_hull` is called, **Then** it
   raises `HullParameterError` naming `hull_variant` and the valid set, before any FreeCAD call.
4. **Given** the same `hull_variant="hard_chine"` parameters built twice in one process, **When**
   both hulls are compared, **Then** their geometry is byte-identical (reproducibility,
   constitution II).
5. **Given** the CLI `storebro build --hull-variant hard_chine`, **When** the build runs, **Then**
   the produced document contains the hard-chine hull and the flag is reflected in `info`/JSON
   output consistently with `--superstructure`.

### User Story 2 - Expression-engine bindings (DEFERRED — design only)

A modeler edits a hull dimension in the FreeCAD GUI and the change propagates through the parametric
feature history via FreeCAD expression bindings (`obj.setExpression(...)`), realising constitution
III editability beyond the current "rebuild from Python" flow.

**Status**: **DEFERRED this spec.** Design recorded in research.md; not implemented. Revisited in a
FreeCAD-equipped session where byte-reproducibility into `Document.xml` can be empirically verified.

**Why deferred**: No `setExpression` exists today; the hull is built from computed station profiles
(not one parametric sketch), so this needs a real FreeCAD spike; and the expression strings land in
`Document.xml` (the spec 028 reproducibility surface), so the result must be proven byte-identical —
which cannot be done without FreeCAD on the dev machine.

### Edge Cases

- **Unknown `hull_variant` value** (e.g. `"deep_vee"`, `""`, `None`-as-string): rejected with
  `HullParameterError` before any FreeCAD call (fail-fast, like `superstructure_variant`).
- **Hard-chine variant produces a non-manifold loft** in FreeCAD: the build falls back to the
  standard hull geometry (manifold-or-fallback, the spec 023/024/030 pattern) and the fallback is
  observable.
- **Variant interaction with existing knobs** (`station_count`, `bilge_radius`, deadrise): the
  hard-chine reshaping must keep the 5-vertex station topology so the dense `Ruled=True` loft stays
  vertex-compatible across all stations including the thin stem (the spec 009 lesson).
- **`hull_variant="standard"` must remain the default** so every existing caller, fixture, test, and
  the deck/interior/propulsion stack that builds on the hull are unaffected and byte-identical.

## Requirements *(mandatory)*

### Functional Requirements — Item 1 (hard-chine hull variant, IMPLEMENTED)

- **FR-001**: `build_hull` MUST accept a `hull_variant: Literal["standard", "hard_chine"]` keyword
  defaulting to `"standard"`, mirroring `build_deck`'s `superstructure_variant`.
- **FR-002**: `hull_variant="standard"` MUST reproduce the pre-031 hull byte-identically (the
  default code path is untouched; the variant only adds a branch).
- **FR-003**: `hull_variant="hard_chine"` MUST reshape the station cross-section into a more
  pronounced hard chine by moving the chine vertex (v1, bottom-outer) outboard toward the topside
  half-beam and up toward the topside-turn (z closer to 0), flattening the keel→chine bottom panel
  and steepening the chine→turn topside panel. This uses only named ratio constants — no magic
  numbers in the body (constitution I). The other four vertices and the vertex count are unchanged.
- **FR-004**: The hard-chine variant MUST keep the existing 5-vertex `PENTAGON_LEGACY` station
  topology (keel-centerline, bottom-outer/chine, topside-turn, sheer-outer, deck-centerline) so the
  `Ruled=True` `AdditiveLoft` stays vertex-compatible across all stations (including the thin stem).
- **FR-005**: The hard-chine hull MUST be a single manifold solid (`Solids == 1`, `isValid()`).
- **FR-006**: If the hard-chine loft does not yield a single manifold solid, the build MUST fall
  back to the standard hull geometry rather than emit a non-manifold body, and the fallback MUST be
  observable to the caller.
- **FR-007**: An unrecognised `hull_variant` value MUST raise `HullParameterError` (naming
  `hull_variant` and the valid set) before any FreeCAD call (fail-fast).
- **FR-008**: Building the same `hull_variant` + parameters twice in one process MUST yield
  byte-identical geometry (reproducibility, constitution II). No timestamps / env-dependent values.
- **FR-009**: The CLI MUST expose `--hull-variant {standard,hard_chine}` (default `standard`),
  threaded through `storebro build`, and reflected in `info` / JSON output consistently with the
  existing `--superstructure` flag.
- **FR-010**: The resulting `Hull` wrapper MUST record the requested `hull_variant` (a readable
  attribute, mirroring how `Deck` records `superstructure_variant`) AND a `variant_applied: bool`
  that is `False` when the hard-chine loft failed and the build fell back to the standard hull
  (FR-006), so the fallback is observable to callers and tests.

### Functional Requirements — Item 2 (expression bindings, DEFERRED)

- **FR-011 (DEFERRED)**: GUI edits to hull dimensions would propagate through the parametric history
  via FreeCAD expression bindings. **Not implemented this spec.** Design recorded in research.md;
  tracked as a `deferred` item; revisited when FreeCAD is available to verify byte-reproducibility
  into `Document.xml`. No `setExpression` code ships in spec 031.

### Key Entities

- **HullParameters / build_hull** (existing): gains the additive `hull_variant` selection (keyword
  on `build_hull`; see plan for whether it lives on the dataclass or the function signature —
  mirrors `superstructure_variant`, which is a `build_deck` keyword, not a `DeckParameters` field).
- **Hull** (existing wrapper): records the selected `hull_variant`.
- No new persisted entity, no new state machine.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `hull_variant="standard"` build is byte-identical to the pre-031 hull (value-pinned
  reproducibility check).
- **SC-002**: `hull_variant="hard_chine"` build is a single solid and, at the amidships station, its
  chine half-beam ratio (`half_beam_at_bottom / half_beam_at_top`) exceeds the standard hull's by a
  named, asserted margin (the chine is measurably pushed outboard).
- **SC-003**: 100% of invalid `hull_variant` inputs raise `HullParameterError`; 100% of valid
  inputs build without error.
- **SC-004**: Two builds of the same variant + parameters in one process are byte-identical.
- **SC-005**: `storebro build --hull-variant hard_chine` builds the hard-chine hull end-to-end and
  the variant is reflected in `info`/JSON output.
- **SC-006**: Item 2 (expression bindings) is documented as deferred with a recorded reason and is
  surfaced for explicit user decision; no `setExpression` code is present in the shipped diff.

## Assumptions

- "Hard chine" is realised by repositioning the existing 5-vertex pentagon's chine/topside vertices
  (flatter bottom + more vertical topside), NOT by changing vertex count or adding a new topology —
  this is the only loft-safe approach given the spec 009 vertex-compatibility constraint.
- The variant is a single knob with two values for now; additional hull variants (deep-vee, etc.)
  are out of scope.
- FreeCAD is unavailable on the dev machine: unit tests cover the variant knob validation, default
  preservation, and CLI/parameter wiring; geometry assertions (manifold, variant-differs,
  reproducible) live in `requires_freecad` tests run by the maintainer (the spec 029/030 pattern).
- The hard-chine variant degrades gracefully (standard-hull fallback) on any FreeCAD geometry
  failure (the spec 023/024/030 manifold-or-fallback precedent) — the boat must still build.
- Full track per `.claude/rules/specs.md`: `/allium:elicit` runs. `/tla` is expected to be SKIPPED
  via the triviality gate (synchronous single-actor hull geometry, no concurrency, no state machine
  — same class as specs 021/025); this is confirmed at the `/tla` step, not assumed away.
- Solo / direct-push: committed straight to `master`, no feature branch, no PR.
