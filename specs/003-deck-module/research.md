# Research: Deck Module (Phase 0)

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-05-17

Resolves the unknowns identified during planning. Each section uses the `Decision / Rationale / Alternatives` format.

---

## R1. Canonical default deck dimensions (resolves OQ1 from spec.allium)

### Decision

Default deck dimensions for the Storebro Royal Cruiser 34 1972 baseline:

| Parameter | Default | Unit | Source / status |
|---|---|---|---|
| `deck_plate_thickness` | 0.025 | m | **Estimate** — typical fiberglass deck thickness (~25 mm); fairs against industry conventions |
| `cabin_trunk_length` | 4.50 | m | **Estimate** — ~43% of LOA (10.35 m); typical RC34 1972 cabin proportion. Refine in PATCH when primary source surfaces |
| `cabin_trunk_fwd_offset` | 2.00 | m | **Estimate** — distance from stem to cabin trunk forward face; ~19% of LOA |
| `cabin_trunk_width` | 2.20 | m | **Estimate** — leaves ~0.50 m total side walkway (`beam_max 3.20 - 2×0.40 = 2.40` envelope), with the cabin taking 2.20 and 0.20 m margin |
| `cabin_trunk_height` | 1.20 | m | **Estimate** — typical headroom-clearing cabin; era-typical |
| `cabin_trunk_corner_radius` | 0.075 | m | **Estimate** (clarify Q3) — ~75 mm rounded fillet matches RC34 1972 |
| `windshield_rake` | 25.0 | ° | **Estimate** — RC34 era characteristic mid-rake windshield |
| `hardtop_length` | 3.50 | m | **Estimate** — extends cabin top aft over cockpit; ~78% of cabin trunk length |
| `hardtop_height` | 0.10 | m | **Estimate** — slight thickness/lip above cabin trunk top |
| `hardtop_overhang_fwd` | 0.20 | m | **Estimate** — slight overhang past windshield |
| `hardtop_overhang_aft` | 0.40 | m | **Estimate** — pronounced aft overhang for cockpit shade |
| `hardtop_pillar_diameter` | 0.04 | m | **Estimate** (clarify Q2) — 40 mm stainless tubing typical |
| `railing_height` | 0.65 | m | **Estimate** — knee-to-hip rail height |
| `deck_side_walkway` | 0.40 | m | **Estimate** — side deck width between hull edge and cabin trunk side |

All 14 parameters are estimate-grade pending a primary source (Storebro shipyard drawings, RC34 1972 brochure scan, restoration documentation). The same revision discipline from spec 001 R1 applies: future maintainers refine in PATCH bumps while keeping new values within ±1% of the previous default, or document the deviation in CHANGELOG with a justified MAJOR-or-MINOR bump.

### Rationale

The RC34 1972 baseline from spec 001 R1 fixed LOA (10.35 m) and beam (3.20 m) as citation-grade. Deck proportions scale from those plus era-typical motor-yacht conventions (Swedish semi-displacement, fixed-bridge layout, modest aft cockpit). The values above produce a recognizably-RC34 silhouette in default form and a valid (geometrically possible, constraint-satisfying) deck for the validator tests.

These values are codified as the field defaults on `DeckParameters` and as a class constant `REFERENCE_STOREBRO_DECK_RC34_1972` in the deck module.

### Alternatives considered

- **Pin only the four citation-grade params (cabin/hardtop length, railing height, pillar diameter) and leave the rest unparametrized**: rejected — every deck dimension needs to be a named parameter (constitution I + FR-002), and "unparametrized" is not a permitted state.
- **Defer ALL deck defaults to v0.4.0 once we have primary source data**: rejected — v0.3.0-alpha cannot ship a default deck without numerical values, and an inferior estimate is better than no default.
- **Use generic motor-yacht averages instead of RC34-specific estimates**: rejected — principle IV requires fidelity to a specific reference, not a fictional average.

---

## R2. Per-Body construction strategy

### Decision

Six Bodies, each built by a private `_build_<element>` helper, all PartDesign-target (Part-workbench for v0.3.0-alpha matching spec 001/002's tracked v0.2.0 upgrade):

**`DeckPlate`** — Sketch a perimeter polygon offset inward from the hull's sheer line by 0 (deck plate sits flush with hull's top edge) on the Z = sheer_height_amidships plane. Pad downward by `deck_plate_thickness`. The result is a 3D solid that geometrically caps the hull. Implementation: sample the hull's sheer curve at 5 stations matching spec 001's lofted-stations strategy, build a sketch through those points, close the curve, pad.

**`CabinTrunk`** — Sketch a rounded-corner rectangle (fillet radius `cabin_trunk_corner_radius`) of dimensions `cabin_trunk_length × cabin_trunk_width` at position `(cabin_trunk_fwd_offset + cabin_trunk_length/2, 0, deck_plate_top_z)` on the X-Y plane. Pad upward by `cabin_trunk_height`. Result: a rounded-rectangle prism.

**`Windshield`** — Sketch a trapezoid from the cabin trunk's forward face top edge, raked aft by `windshield_rake` degrees, with the bottom edge at the deck plate top and the top edge at the cabin trunk top. Pad the trapezoid through a small extrusion thickness (~30 mm) to give the windshield substance. Mirror about centerline.

**`Hardtop`** — Sketch a rounded-corner rectangle of dimensions `hardtop_length × (cabin_trunk_width + 2 × small_margin)` at position derived from cabin_trunk_fwd_offset minus `hardtop_overhang_fwd`, on the Z = cabin_trunk_top + `hardtop_height` plane. Pad upward by 0.05 m (a small fixed hardtop slab thickness — internal constant, not a public parameter for v1.0). Result: a flat roof slab.

**`HardtopPillars`** — Two cylinders of diameter `hardtop_pillar_diameter` running from the deck plate top to the hardtop underside, positioned at the hardtop's aft corners (X = cabin_trunk_fwd_offset + cabin_trunk_length + hardtop_overhang_aft, Y = ±(cabin_trunk_width/2 + small_clearance)). Use a single Body containing both cylinders, built by Part::Compound of two `Part::Cylinder` features. FR-009 symmetry preserved because the two pillars are mirror-image-placed.

**`Railings`** — Sketch the perimeter of the deck (offset inward by ~deck_side_walkway/2 from hull sheer line) and use `Part::Pipe` (Sweep) with a small circular cross-section of diameter `railing_pipe_diameter` (~25 mm internal constant) along the perimeter at height Z = deck_plate_top + `railing_height`. Result: a continuous rail loop following the deck edge.

### Rationale

Each sub-Body uses the simplest FreeCAD construction that produces a parametric, editable result. Decisions trade off:
- **Editability** (FR-007): every sub-Body has a sketch + a single primary feature (Pad or Pipe). GUI edits to either ripple through cleanly.
- **Determinism** (FR-005): every helper builds in a fixed feature order. Same inputs → same Bodies.
- **Composition** (FR-001): six independent Bodies in the same document. They don't fuse with each other — composition is the user's job.

### Alternatives considered

- **Build the deck as a single Body** containing all six elements: rejected — destroys the per-element editability the spec promises (FR-007 + acceptance scenario 1).
- **Use PartDesign::AdditiveLoft for the cabin trunk**: rejected for v0.3.0-alpha — same reason as spec 001's loft choice (Part workbench is simpler and works today; PartDesign loft is the v0.2.0 upgrade target).
- **Build railings as a swept pipe along the full hull sheer**: rejected — would put the rail outside the deck plate's edge. Use the deck edge inset instead.
- **Build hardtop pillars as Part::Cone tapering at the bottom**: rejected — RC34 hardtop pillars are uniform-diameter stainless tubing per period photos. Constant-diameter cylinder is correct.

### Determinism considerations

The hull's sheer line is sampled at five stations (matching spec 001's loft station positions) to build the deck plate perimeter. The sampling positions are fixed; the sampled values are reproducible because spec 001 guarantees structural determinism. Therefore `_build_deck_plate` is deterministic given a fixed hull.

---

## R3. Exception API (resolves clarify Q5)

### Decision

Two custom exception classes, both public, both importable from `storebro.deck`. Independent of spec 001's classes (clarify Q5):

```python
class DeckParameterError(ValueError):
    parameter_name: str
    parameter_value: float | None  # None for cross-field violations
    valid_range: str

class DeckConstructionError(RuntimeError):
    parameters: DeckParameters | None
    hull: Hull | None
    underlying: BaseException | None
    detected_version: tuple[int, int] | None
    supported_range: str | None
```

Both classes fully exported via `storebro.deck.__all__` and re-exported from `storebro/__init__.py`.

### Rationale

Mirrors spec 001's two-class taxonomy. Clarify Q5 chose independence: no shared base class with spec 001's `HullParameterError`. Callers wanting to catch any-module validation error use the standard library bases (`except ValueError`).

### Alternatives considered

See clarify Q5 audit list — three alternatives considered and rejected.

---

## R4. Document handling (FR-016)

### Decision

`build_deck(hull, parameters=None, *, document=None, name="Deck")` resolves the target document strictly:

1. If `document` is `None`: use `hull.document`.
2. If `document` is not `None` and `document is hull.document`: use that document.
3. If `document` is not `None` and `document is not hull.document`: raise `DeckParameterError("document", "must equal hull.document for cross-module consistency", repr(document))`.

The strict-rejection is a deliberate API choice. Allowing the deck to attach to a different document would mean the hull's Body and the deck's Bodies could disagree about the underlying geometry (e.g., the document with the hull might have been edited since the `Hull` object was created), and the deck plate's sheer-line alignment (FR-010, SC-009) becomes unverifiable.

### Rationale

Cross-document deck building is a footgun: the caller would silently get geometry that's measured against one hull but lives in another document. The strict reject surfaces the mistake immediately with a typed error.

### Alternatives considered

- **Silently use `hull.document` when there's a mismatch**: rejected — masks the caller's error and produces surprising behavior.
- **Allow cross-document but warn**: rejected — `storebro` has no logging in v1.0 (clarify Q4); warnings have nowhere to go.
- **Permit cross-document, validate that hull was built from same parameters as current document state**: rejected — too expensive; would need to re-derive the hull from parameters to check.

---

## R5. Body labeling (FR-017)

### Decision

`build_deck(hull, parameters, *, name="Deck")` assigns labels:
- `Deck` (the aggregate's `.label`)
- `Deck_DeckPlate`, `Deck_CabinTrunk`, `Deck_Windshield`, `Deck_Hardtop`, `Deck_HardtopPillars`, `Deck_Railings` (the six sub-Body labels)

If a user passes `name="StarboardDeck"`, the sub-Bodies become `StarboardDeck_DeckPlate`, etc.

FreeCAD's standard label auto-numbering applies on collision: a second call with the same name produces `Deck001`, `Deck001_DeckPlate`, etc.

### Rationale

Matches FR-017 directly. The `{name}_<element>` prefix keeps the document tree organized when multiple decks exist (variant studies). The auto-numbering means callers don't need to manage uniqueness themselves.

### Alternatives considered

- **No prefix, just bare element names**: rejected — collisions across decks in the same document would force opaque auto-numbering (`DeckPlate001`, `DeckPlate002`) without naming which deck owns which Body.
- **Prefix with hull label instead of deck name**: rejected — the spec asks for a `name` kwarg on the deck builder; using `hull.label` would make the deck label depend on the hull which complicates the API.

---

## R6. Lazy version check (FR-013)

### Decision

The deck module reuses spec 001's `storebro._freecad_check.ensure_supported_freecad()` (the same lazy first-call cache that hull and export already share). On `HullConstructionError` from the helper, `build_deck` catches duck-typed (just like spec 002's `_ensure_freecad_supported`) and re-raises as `DeckConstructionError`.

### Rationale

Single source of truth for the supported range (in `pyproject.toml`); single cache shared across all writers and builders; consistent first-call timing.

### Alternatives considered

- **Each module owns its own version-check cache**: rejected — three caches drift, three Imports of `tomllib`, three places to fix when the supported range expands.

---

## R7. Rollback discipline (FR-018, SC-008)

### Decision

`build_deck` maintains a `_added_objects: list[FreeCAD.DocumentObject]` inside its body. Each `_build_<element>` helper appends its created Bodies to the list immediately after `target_doc.addObject(...)` returns. If any helper raises, the outer try-except:

```python
added: list = []
try:
    deck_plate = _build_deck_plate(hull, parameters, target_doc, added)
    cabin = _build_cabin_trunk(hull, parameters, deck_plate, target_doc, added)
    # ... etc
except BaseException as exc:
    for obj in reversed(added):
        with contextlib.suppress(Exception):
            target_doc.removeObject(obj.Name)
    target_doc.recompute()  # clean up dangling references
    raise DeckConstructionError(
        f"build_deck failed during {type(exc).__name__}: {exc}",
        parameters=parameters,
        hull=hull,
        underlying=exc,
    ) from exc
```

Reversed iteration removes the latest objects first to avoid dependency-order issues.

### Rationale

The user's FreeCAD document must end up in either of two states after `build_deck` returns: (a) successful — all six Bodies present, (b) failed — no Bodies added, document otherwise unchanged. Partial decks are a worse state than no deck.

### Alternatives considered

- **Use a FreeCAD transaction (`document.openTransaction` / `commitTransaction` / `abortTransaction`)**: considered seriously. FreeCAD has transaction support but the API is GUI-oriented; in headless mode the rollback behavior varies by version. Manual `removeObject` is portable across the supported range.
- **Pre-build all six Bodies in a scratch document, then transfer on success**: rejected — `FreeCAD.copyObject` between documents is brittle and loses the parametric history.
- **Let the caller catch and clean up**: rejected — SC-008 explicitly says the builder MUST roll back; pushing it to the caller is a public-API regression.

---

## R8. Deck plate ↔ hull sheer alignment (FR-010, SC-009)

### Decision

The deck plate's perimeter is sampled from the hull's sheer line at the same five station positions spec 001 used for hull construction. The sample procedure:

1. Read the hull's `body.Shape` and walk its faces to identify the "sheer face" (the topmost face, identifiable by its outward normal pointing upward in Z, at maximum Z).
2. For each station X position `x_i ∈ {0, 0.25·loa, 0.50·loa, 0.75·loa, loa}`, intersect the sheer face with a Y-Z plane at X = x_i, take the resulting curve, find its highest point on the positive-Y side (port half by symmetry).
3. Build the deck plate sketch through these 5 sampled points (plus their mirror images on the negative-Y side via Part::Mirroring later).
4. The deck plate's underside Z at each sampled X equals the hull's sheer Z at that X by construction.

SC-009 (1 µm sheer alignment tolerance) is verified by the test: re-sample the hull's sheer line independently of the deck builder, and assert each sampled point's Z matches the deck plate's underside Z within 1 µm.

### Rationale

Sampling the hull's actual Shape (not re-deriving from `HullParameters`) means the alignment is robust against future changes to the hull construction (e.g., the v0.2.0 PartDesign loft upgrade). The five-station sampling matches the hull's own discretization, so no extrapolation between station positions is needed.

### Alternatives considered

- **Re-derive the sheer line analytically from HullParameters** (using the same math the hull module used to construct it): rejected — duplicates spec 001's internal math in the deck module, breaks if the hull module changes its station strategy. The two modules would drift.
- **Use Part::Section to intersect the hull with a horizontal plane**: rejected — the resulting curve is the waterline, not the sheer line. Wrong feature.
- **Boolean-cut the deck plate from a horizontal extrusion of the hull's top face**: considered — more "correct" topologically. But spec 001's hull doesn't expose a clean "top face" extraction yet; the sampled-stations approach is simpler and matches the SC-009 tolerance with margin.

---

## R9. Testing strategy

### Decision

Two-tier pytest layout matching spec 001/002, with new cross-module test categories:

- **Unit tier** (`tests/unit/test_deck_*.py`):
  - `test_deck_parameters.py`: defaults, per-field validation, cross-field validation, frozen behavior, REFERENCE_STOREBRO_DECK_RC34_1972 constant matches defaults.
  - `test_deck_errors.py`: exception class hierarchy, attribute shapes, message formats.
  - `test_deck_leaf_dependencies.py`: AST scan of `src/storebro/deck.py` verifies imports only `storebro.hull` + `storebro._freecad_check` from the storebro namespace, NOT `interior`/`export`/`cli`.

- **Geometry tier** (`tests/geometry/test_deck_*.py`, marker `requires_freecad`):
  - `test_deck_default_call.py`: `build_deck(build_hull())` produces 6 sub-Bodies with correct labels, volumes > 0, build_duration < 45 s (SC-002).
  - `test_deck_default_dimensions.py`: cabin trunk length / hardtop length / railing height within ±1% of REFERENCE constants (SC-001).
  - `test_deck_sheer_alignment.py`: deck plate underside Z at 5 sampled stations matches hull sheer Z within 1 µm (SC-009).
  - `test_deck_symmetric.py`: each of 6 Bodies has bbox YMin/YMax symmetric about 0 (FR-009).
  - `test_deck_parametricity.py`: each of 14 named params ±10% → corresponding measurement changes monotonically (SC-004).
  - `test_deck_determinism.py`: two back-to-back `build_deck(hull, params)` produce per-Body identical volume/bbox/topology (SC-003).
  - `test_deck_construction_rollback.py`: forced failure during 4th sub-Body (after first 3 succeed) → no orphan Bodies, no partial document state (SC-008).
  - `test_deck_document_mismatch.py`: `build_deck(hull, document=different_doc)` raises `DeckParameterError` (FR-016).
  - `test_deck_visual_signoff.py`: produces `/tmp/storebro_deck_signoff_003.FCStd` with hull + deck for manual GUI review.

### Rationale

Mirrors the spec 001/002 testing convention with two new test categories: leaf-dependencies (verifying the cross-module import pattern) and rollback (verifying SC-008). Every FR/SC maps to ≥1 test (per SC-006).

### Alternatives considered

- **Add a third tier for "integration" tests covering hull → deck wiring**: rejected — the geometry tier already does this naturally because every geometry test calls `build_hull()` then `build_deck(hull)`. An "integration" label adds taxonomy without adding signal.

---

## Summary of decisions

| ID | Decision | Resolves |
|---|---|---|
| R1 | RC34 1972 estimate-grade defaults for 14 deck parameters | OQ1 / SC-001 / FR-003 |
| R2 | Per-Body construction strategy (pad/loft/pipe by sub-Body) | FR-006 / FR-007 / FR-009 |
| R3 | Two independent exception classes per clarify Q5 | FR-015 |
| R4 | Strict document matching (raise on mismatch) | FR-016 |
| R5 | `{name}_<Element>` labeling with FreeCAD auto-numbering | FR-017 |
| R6 | Reuse `storebro._freecad_check` (shared lazy cache) | FR-013 |
| R7 | Manual `removeObject` rollback in reversed order | FR-018 / SC-008 |
| R8 | Sample hull Shape's sheer face at 5 stations for deck plate | FR-010 / SC-009 |
| R9 | Two-tier pytest with leaf-dependencies + rollback categories | SC-005 / SC-006 / SC-007 |

All NEEDS CLARIFICATION markers resolved. Ready for Phase 1.
