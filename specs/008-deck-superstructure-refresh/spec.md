# Feature Specification: Deck Superstructure Refresh

**Feature Branch**: `008-deck-superstructure-refresh`

**Created**: 2026-05-18

**Status**: Draft

**Input**: User description: "Reshape cabin trunk, windshield, hardtop, hardtop pillars, and railings to match the Alternativ1–5 reference profiles (currently boxy placeholders). Fix the hardtop-pillars-drop-below-hull positioning bug. In scope: parametric reshape of (1) cabin trunk silhouette to match the trapezoidal+tapered Storebro forward house, (2) windshield rake and curvature to the reference angle, (3) hardtop overhang shape (currently flat slab, should taper aft and have leading-edge curl), (4) hardtop pillar geometry + correct vertical seating on the deck, (5) railing height/post spacing. Out of scope: rubrail and lifelines (spec 010), window cutouts/glass (spec 011), colors/materials (spec 015), DS enclosed wheelhouse variant (spec 016). Must remain FreeCAD-idiomatic PartDesign Bodies, all dimensions parameterized with sane defaults derived from the references, reproducible byte-identical output, ±1% reference fidelity on principal dimensions per constitution principle IV."

## Clarifications

### Session 2026-05-18

- Q: Hardtop pillar default count — total across the boat vs per side? → A: 2 per side (4 total)
- Q: Where on the deck plate top surface should pillars seat, laterally? → A: Outboard, inset 80 mm inboard from the sheer line
- Q: Windshield surface generation — extruded constant-width B-spline or lofted between port/starboard B-spline edges? → A: Lofted between port and starboard B-spline edges (supports slight top-narrowing per reference; forward-compatible with spec 011 glass replacement)
- Q: Zero-pillar fallback geometry — cantilevered hardtop or hardtop seated directly on cabin trunk roof? → A: Hardtop seats on cabin trunk roof (cantilever is out of scope)
- Q: Pillar vertical orientation under the curling hardtop leading edge — strictly vertical with upper endpoint following the curl, or pillars angled to track the curl? → A: Strictly vertical; upper endpoint Z computed at each pillar's X station where pillar meets hardtop underside

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recognizable RC34 silhouette in side view (Priority: P1)

A scale modeler or restorer opens the default `storebro build` output in the FreeCAD GUI, switches to side view, and immediately recognizes the model as a vintage Storebro RC34 1972 — not because of the hull alone, but because the cabin trunk, windshield, hardtop, and railings together form the canonical superstructure silhouette seen on the storebropassion.de reference. The superstructure is the dominant visual signature of the boat (~60% of what the eye reads as "Storebro"); a faithful silhouette is the difference between "a generic motor yacht" and "a Storebro".

**Why this priority**: This is the headline visual improvement of v1.1. The hull refresh (spec 007) made the underwater profile correct, but the superstructure still reads as a stack of cardboard boxes. Without this story, the model fails the "would a Storebro owner recognize their boat?" test — which is the project's reason for existing per PROJECT-BRIEF.

**Independent Test**: Run `storebro build --layout 3 --out /tmp/check.FCStd`, open in FreeCAD 1.1+, switch to side view (View → Right), and overlay the rendered silhouette against `docs/references/Alternativ3.JPG`. Principal dimensions of cabin trunk length, cabin trunk height above deck, windshield rake angle, hardtop length, hardtop height above deck, and hardtop overhang must match the reference within ±1%.

**Acceptance Scenarios**:

1. **Given** default `HullParameters` and default `DeckParameters`, **When** the user runs `storebro build --layout 3`, **Then** the resulting `.FCStd` shows a cabin trunk with trapezoidal silhouette (narrower at the front, wider amidships, tapered into the cockpit aft), a raked windshield with a forward-curving B-spline profile, a hardtop with aft taper and a small downward curl on its leading edge, and railings whose height and post count match the reference photo within ±1%.
2. **Given** the rendered `.FCStd` from scenario 1, **When** opened in the FreeCAD GUI, **Then** every superstructure component appears as an editable `PartDesign::Body` with named features (sketches, pads, lofts, mirrors) — not as raw `Part::Compound` or `Mesh::Feature` nodes.
3. **Given** the model viewed from side, top, and bow angles, **When** the silhouette is compared to `Alternativ3.JPG`, **Then** no superstructure feature deviates by more than ±1% on any principal dimension (length, height, width).

---

### User Story 2 - Hardtop pillars seat on deck, not through hull (Priority: P1)

A FreeCAD scripter inspecting the model in the GUI sees that every hardtop pillar starts at the deck plate top surface and ends at the underside of the hardtop. No pillar extends downward through the deck plate into the hull cavity. This is a regression fix: the v1.0.1 output ships pillars that visibly pierce the sheer line and emerge inside the cabin, which is geometrically wrong, visually jarring, and a hard blocker for any rendering or interior work.

**Why this priority**: This is a correctness bug, not a polish item. The current behavior produces output that would never pass a constitutional fidelity check (principle IV — ±1% reference fidelity) because real Storebro hardtop pillars are surface-mounted on the deck. Same priority as P1 because shipping a visually-correct superstructure with pillars still pissing through the hull is no win.

**Independent Test**: Run `storebro build --layout 3 --out /tmp/check.FCStd` and assert in a geometry test that, for every pillar `Body` in the resulting document, the pillar's bounding-box minimum Z coordinate equals the deck plate's top Z coordinate within 1 mm tolerance. No pillar may have a vertex below the deck plate top surface.

**Acceptance Scenarios**:

1. **Given** default parameters, **When** the build runs, **Then** all hardtop pillars have their lower endpoint coincident with the deck plate top surface within 1 mm.
2. **Given** a model with reduced deck height or increased hull sheer, **When** the build runs, **Then** pillars still seat on the (now-moved) deck plate top — they track the deck, not a fixed absolute Z.
3. **Given** any of the five canonical Alternativ layouts, **When** the build runs, **Then** the pillar-seating invariant holds for every layout.

---

### User Story 3 - All five Alternativ layouts render without geometry failures (Priority: P2)

A library consumer iterates through all five canonical layouts via `storebro build --layout 1..5` and gets five `.FCStd` files, each with a fully-constructed superstructure (cabin trunk, windshield, hardtop, pillars, railings). The interior fixture varies per layout (per spec 004), but the superstructure shape is uniform across all five — they share the standard RC34 cabin since the DS enclosed-wheelhouse variant is reserved for spec 016. No layout silently strips superstructure components or falls back to placeholder geometry.

**Why this priority**: The five layouts are the canonical product surface from spec 005 (CLI). If layout 4 builds a malformed hardtop because the new superstructure code didn't handle a fixture corner case, the regression is silent and ships. P2 because the failure mode is "fewer components rendered" rather than "geometrically wrong" — recoverable but still wrong.

**Independent Test**: For each `layout ∈ {1, 2, 3, 4, 5}`, run `storebro build --layout <n> --out /tmp/check_<n>.FCStd`, parse the resulting FCStd, and assert that the document contains exactly one of each: `CabinTrunkBody`, `WindshieldBody`, `HardtopBody`, `HardtopPillarsBody` (compound or group), `RailingsBody`. Each body must have a non-empty `.Shape.Vertexes` collection and a positive `.Shape.Volume`.

**Acceptance Scenarios**:

1. **Given** any layout ∈ {1..5}, **When** the build runs, **Then** the output `.FCStd` contains all five superstructure bodies with positive volume.
2. **Given** two consecutive builds of the same layout with identical parameters, **When** both outputs are compared, **Then** they are byte-identical (within the same FCStd document scope from spec 002).
3. **Given** layout 1 vs layout 3 outputs, **When** the superstructure bodies are compared, **Then** their `.Shape` digests are identical (the superstructure is layout-invariant; only the interior changes).

---

### Edge Cases

- **Zero pillars**: If `count_per_side = 0` is requested via overridden parameters, the hardtop MUST still construct by seating directly on the cabin trunk roof (the hardtop forward edge attaches to the cabin trunk aft face / roof intersection, and the hardtop spans aft from there). The cantilevered-hardtop variant is explicitly out of scope. Default `count_per_side = 2` (4 pillars total, matching the reference photo).
- **Pillar position conflicts with cabin trunk wall**: If a pillar's X position falls inside the cabin trunk footprint, the build must raise `ValueError` with the offending coordinate and the cabin trunk bounds, not silently produce intersecting geometry.
- **Hardtop overhang exceeds deck width**: If the hardtop's full width (including overhang) exceeds the deck plate width at the hardtop's longitudinal station, the build must raise `ValueError` — overhangs floating outside the hull are not physically meaningful for a Storebro.
- **Windshield curvature radius below minimum**: The forward-curving windshield is a B-spline through three control points (base, mid, top); if the curvature radius drops below 0.2 m, the spline self-intersects. Build must raise `ValueError` with the offending radius.
- **Railing taller than hardtop**: If `railing_height > hardtop_height_above_deck`, the railings would penetrate the hardtop. Build must raise `ValueError`.
- **Negative or zero principal dimensions**: Any of `cabin_trunk_length`, `windshield_height`, `hardtop_length`, `pillar_diameter`, `railing_height` ≤ 0 raises `ValueError` per constitution principle I.
- **Hull from older parameters**: When run against a hull built with v1.0.0-alpha parameters (before spec 007), the superstructure attachment points (sheer line Z at hardtop stations) must still be computed correctly. Failing this, the build raises a clear error pointing to the missing hull attribute, not a `NoneType` traceback.
- **Cross-platform path reproducibility**: A build on macOS Darwin arm64 and an identical build on Linux x86_64 produce byte-identical `.FCStd` files (within the determinism scope of spec 002, excluding the FCStd cross-invocation marker deferred since v1.0.0).

## Requirements *(mandatory)*

### Functional Requirements

#### Cabin trunk

- **FR-001**: System MUST construct the cabin trunk as a `PartDesign::Body` containing at least one `Sketch` and one `PartDesign::Pad` or `PartDesign::AdditiveLoft` feature — never as a raw `Part::Box` or generated mesh.
- **FR-002**: The cabin trunk silhouette in side view MUST be trapezoidal+tapered: lower edge follows the deck plate, upper edge is shorter than the lower edge (tapered into the cockpit aft), forward face is raked aft, aft face is near-vertical or slightly forward-raked.
- **FR-003**: The cabin trunk MUST be parameterized by named fields on a `CabinTrunkParameters` dataclass (or equivalent): `length`, `forward_width`, `aft_width`, `height`, `forward_rake_angle`, `aft_rake_angle`, `wall_inset` (distance from sheer line inboard).
- **FR-004**: Default values for all cabin-trunk parameters MUST be derived from `docs/references/Alternativ3.JPG` (the canonical RC34 1972 reference) and documented as measured-from-reference in the dataclass docstring.

#### Windshield

- **FR-005**: The windshield MUST be constructed as a `PartDesign::Body` from a `PartDesign::AdditiveLoft` (or equivalent) lofted between a port-edge B-spline curve and a starboard-edge B-spline curve, each defined by at least three control points (base, mid, top) producing a forward-curving profile in side view. The two edge curves may have different top widths (top edge narrower than base edge) to reproduce the slight top-narrowing seen in the reference. Constant-width extrusion of a single B-spline is NOT acceptable.
- **FR-006**: The windshield MUST be parameterized by `WindshieldParameters`: `base_z` (height above cabin trunk roof at attachment), `top_z`, `rake_angle_base`, `rake_angle_top`, `base_width`, `top_width` (top_width ≤ base_width per the reference top-narrowing), `thickness`.
- **FR-007**: The windshield rake angle at its base MUST match the reference Alternativ3.JPG within ±1° on the default parameters.
- **FR-008**: The windshield curvature MUST be expressible as a single B-spline (no faceted multi-panel) to support the eventual transparent-glass treatment in spec 011.

#### Hardtop

- **FR-009**: The hardtop MUST be constructed as a `PartDesign::Body` with parametric aft taper and a downward-curling leading edge — never as a flat `Part::Box` plate.
- **FR-010**: The hardtop MUST be parameterized by `HardtopParameters`: `length`, `forward_width`, `aft_width`, `thickness`, `height_above_deck`, `leading_edge_curl_depth`, `leading_edge_curl_length`.
- **FR-011**: The hardtop aft width MUST be less than its forward width (aft taper) on default parameters.
- **FR-012**: The hardtop leading-edge curl MUST drop the leading edge by `leading_edge_curl_depth` over the forward `leading_edge_curl_length` of the hardtop, producing a visible downward curve at the windshield top — not a sharp downward step.
- **FR-013**: The hardtop overhang at its forward and aft edges MUST extend beyond the pillar attachment points by at least 50 mm on default parameters, matching the reference photo overhangs.

#### Hardtop pillars

- **FR-014**: Hardtop pillars MUST be constructed as `PartDesign::Body` instances (one body per pillar, or a single body with multiple `Mirrored` / `PolarPattern` features) with circular cross-section by default.
- **FR-015**: Hardtop pillars MUST be parameterized by `PillarParameters`: `count_per_side` (default: 2 — 4 total across port + starboard, matching the reference), `diameter`, `forward_x`, `aft_x` (longitudinal positions on the deck), `inboard_offset_from_sheer` (lateral distance from the sheer line inboard to the pillar centerline, default: 80 mm).
- **FR-016**: **Every pillar's lower endpoint MUST seat on the deck plate top surface within 1 mm tolerance, laterally positioned at `inboard_offset_from_sheer` (default 80 mm) inboard from the sheer line.** No pillar geometry MUST extend below the deck plate top Z coordinate. This is the explicit fix for the v1.0.1 regression where pillars drop through the hull into the cabin.
- **FR-017**: Every pillar's centerline MUST be strictly vertical (parallel to global Z). Every pillar's upper endpoint MUST seat at the underside of the hardtop at the pillar's `(forward_x|aft_x, ±lateral)` station; the upper-endpoint Z is computed from the hardtop's curling underside surface at that station, so forward pillars naturally attach at a slightly lower Z than aft pillars when the leading-edge curl applies. Pillars are NOT angled to track the curl.
- **FR-018**: Pillars MUST be symmetric across the centerline (port and starboard mirror pairs) on default parameters, matching the reference photos.

#### Railings

- **FR-019**: Railings MUST be constructed as `PartDesign::Body` instances with parameterized post count, post spacing, top-rail diameter, and total height above the deck plate.
- **FR-020**: Railings MUST be parameterized by `RailingParameters`: `post_count_per_side`, `post_diameter`, `top_rail_diameter`, `height_above_deck`, `forward_x`, `aft_x`, `inboard_offset_from_sheer`.
- **FR-021**: Railing default values MUST be derived from the reference photos (post count, height, spacing) and documented as measured-from-reference in the dataclass docstring.
- **FR-022**: Railings MUST be symmetric port/starboard on default parameters.

#### Module integration

- **FR-023**: All superstructure parameters MUST live in a single composite `DeckSuperstructureParameters` dataclass (or a re-exported tuple of the five sub-dataclasses) — discoverable from `storebro.deck.__all__`.
- **FR-024**: The existing `storebro.deck.build_deck` public function signature MUST remain compatible: callers passing `HullParameters` only (no superstructure params) MUST continue to receive defaults derived from the reference. Backward-incompatible API changes are out of scope (PATCH-bump per semver, not MINOR/MAJOR).
- **FR-025**: All five canonical Alternativ layouts (1..5) MUST share the standard RC34 superstructure shape; per-layout superstructure variation is out of scope (spec 016 introduces the DS variant).
- **FR-026**: System MUST raise `ValueError` with the offending parameter name, the offending value, and the valid range for any parameter outside its valid bounds (see Edge Cases for specific bounds).

#### Reproducibility & FreeCAD idiom

- **FR-027**: Two consecutive `storebro build` invocations with identical parameters MUST produce byte-identical `.FCStd` files (within the determinism scope established by spec 002 — same FCStd document scope, excluding the cross-invocation marker deferred since v1.0.0).
- **FR-028**: The output `.FCStd` MUST be openable in FreeCAD 1.1+ GUI with all superstructure bodies appearing in the Model Tree as editable `PartDesign::Body` nodes with named feature children (sketches, lofts, pads, mirrors).
- **FR-029**: No superstructure feature MUST use raw `Mesh::Feature`, `Part::Compound`, or generated-mesh nodes — only `Part`, `Sketch`, `Body`, `PartDesign` per constitution principle III.

#### Test coverage

- **FR-030**: Unit tests (no FreeCAD runtime) MUST cover all parameter validation (every `ValueError` path).
- **FR-031**: Geometry tests (marker `requires_freecad`) MUST cover (a) the pillar-seating invariant FR-016 for all five Alternativ layouts, (b) the trapezoidal cabin trunk silhouette FR-002, (c) the windshield B-spline curvature FR-005 + FR-008, (d) the hardtop aft taper FR-011 and leading-edge curl FR-012, (e) the railing symmetry FR-022, (f) the byte-identical reproducibility FR-027.
- **FR-032**: Destructive tests MUST cover all eight Edge Cases listed in this spec (zero pillars, pillar/cabin conflict, oversized overhang, sub-minimum windshield curvature, railing/hardtop collision, negative dimensions, old-hull-parameters compatibility, cross-platform reproducibility).

### Key Entities *(include if feature involves data)*

- **`CabinTrunkParameters`**: Parametric description of the forward cabin trunk (length, forward/aft width, height, fwd/aft rake, wall inset). Persists no runtime state; consumed by `build_cabin_trunk(hull, params) → PartDesign::Body`.
- **`WindshieldParameters`**: Parametric description of the windshield (base/top Z, base/top rake, width, thickness). B-spline cross-section through three control points.
- **`HardtopParameters`**: Parametric description of the hardtop (length, fwd/aft width, thickness, height above deck, leading-edge curl depth + length).
- **`PillarParameters`**: Parametric description of hardtop pillars (count per side, diameter, fwd/aft X, inboard offset).
- **`RailingParameters`**: Parametric description of railings (post count per side, post + top-rail diameter, height, fwd/aft X, inboard offset from sheer).
- **`DeckSuperstructureParameters`**: Composite of the five above; the single entry-point parameter set for the superstructure refresh.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When the default-parameter `.FCStd` is viewed in FreeCAD GUI side view and overlaid on `docs/references/Alternativ3.JPG`, principal superstructure dimensions (cabin trunk length, cabin trunk height, windshield rake angle, hardtop length, hardtop height above deck) deviate from the reference by ≤ 1% per constitution principle IV.
- **SC-002**: Zero hardtop pillars extend below the deck plate top surface in any of the five Alternativ layouts (asserted by an automated geometry test on every CI run).
- **SC-003**: 100% of pytest tests pass (`uv run pytest` exits 0), 100% ruff-clean (`uv run ruff check .` exits 0), 100% mypy-clean (`uv run mypy src/` exits 0).
- **SC-004**: The output `.FCStd` opens in FreeCAD 1.1+ on macOS Darwin arm64 within 5 seconds, with all six superstructure bodies (cabin trunk, windshield, hardtop, port pillars, starboard pillars, railings) appearing as editable PartDesign Bodies in the Model Tree.
- **SC-005**: Two consecutive builds of the same layout with identical parameters produce byte-identical `.FCStd` files (SHA-256 digests match) within the determinism scope of spec 002.
- **SC-006**: All five Alternativ fixtures (1..5) build successfully and produce identical superstructure geometry across layouts (only interior varies); asserted by comparing `.Shape` digests of `CabinTrunkBody`, `WindshieldBody`, `HardtopBody`, `HardtopPillarsBody`, `RailingsBody` across the five output documents.
- **SC-007**: The signoff commit message body includes a "Visually verified in FreeCAD: \<version\> on \<OS\>" line per constitution principle V, with the path to the generated signoff `.FCStd` artifact and its SHA-256 recorded in the commit. (Constitution V refers to a "PR description"; this project runs solo direct-push per `project_workflow.md`, so the same content lives in the commit message body — no semantic dilution.) Visual evidence of the side-view silhouette overlaid on `Alternativ3.JPG` showing ≤ 1% deviation on principal dimensions is captured as a screenshot in `docs/references/signoff/spec-008-side-overlay.png` and referenced from the commit.
- **SC-008**: Geometry test coverage for the superstructure module reaches ≥ 90% (measured by `pytest --cov=src/storebro/deck`), with every public function having at least one unit test and one geometry test.

## Assumptions

- The v1.0.1 hull from spec 007 is the geometric baseline; the superstructure attaches to its sheer line at the hardtop and railing stations. No hull changes are introduced by this spec.
- The Alternativ1–5 reference images (upper halves of `docs/references/Alternativ1.JPG` through `Alternativ5.JPG`, sourced from storebropassion.de) are the canonical reference. The boat shown in all five is the same RC34 hull + RC34 superstructure; only the interior layout differs in the lower-half cutaway. Therefore the superstructure shape is layout-invariant.
- The DS variant (enclosed wheelhouse / built-in styrhytt) is explicitly out of scope and reserved for spec 016. This spec produces the standard RC34 open-cockpit superstructure only.
- Reference dimensions are extracted by visual measurement from `Alternativ3.JPG` at the scale established by the known LOA (10.36 m for RC34 1972). The ±1% fidelity bar applies to dimensions extractable from the side-view photo; out-of-plane details (e.g., exact crown of the cabin trunk roof) accept reference photo measurement noise (~±2%) as the practical limit.
- The windshield is constructed by lofting between a port-edge B-spline and a starboard-edge B-spline; each edge curve is itself planar (vertical plane), and the loft introduces lateral interpolation. The two edge curves share their base width and may narrow toward the top to reproduce the reference top-tapering. A doubly-curved (compound 3D) windshield with crowning across the width is a stretch goal deferred to a later spec.
- Pillar cross-section is circular by default. Square or rectangular pillar profiles are out of scope; if reference photos for specific Alternativ layouts show non-circular pillars, that variation lives in spec 016 (DS variant) or a future spec.
- The hardtop is a single rigid body; folding/removable hardtop variants are out of scope.
- Rubrail (the prominent wooden strip along the sheer) is explicitly out of scope and reserved for spec 010. Its absence in the v1.1 superstructure refresh output is acceptable.
- Window cutouts (portholes, windshield as transparent glass, cabin trunk side windows) are out of scope and reserved for spec 011. The windshield and cabin trunk in this spec are opaque solid bodies.
- Colors and materials are out of scope and reserved for spec 015. The superstructure ships in FreeCAD's default grey shading.
- The PartDesign-Body idiom established in spec 006 (datum plane → sketch → loft/pad → mirror) is the geometry pattern. Each superstructure component is its own Body with its own feature stack — they are not consolidated into a single super-Body, to keep the FreeCAD GUI Model Tree readable and to allow downstream specs (010 hardware, 011 cutouts, 015 colors) to target individual bodies.
- The Allium specification (`spec.allium`) uses the name `SuperstructureBundle` for the composite output entity that aggregates the five sub-bodies. The Python implementation reuses the existing v1.0.1 `Deck` aggregate dataclass at `src/storebro/deck.py:327` (with one new field — see contracts/python-api-additive.md) to preserve backward compatibility. The two names refer to the same logical entity; `data-model.md §2.6` is the bridge.
- The existing `build_deck` public API signature is preserved per FR-024. Internal helpers may be renamed, split, or replaced — but `storebro.deck.build_deck(hull: HullBody, layout: Alternativ) → DeckBundle` remains stable. Semver bump for this spec is PATCH (v1.0.1 → v1.0.2), not MINOR.
- Reproducibility is enforced within the determinism scope established by spec 002: same FCStd document scope is byte-identical; cross-FCStd-invocation byte equality remains a known limitation deferred since v1.0.0 (per spec register history entry 2026-05-17).
