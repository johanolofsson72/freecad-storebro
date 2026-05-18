# Phase 0 Research: Deck Superstructure Refresh

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-05-18

Resolves the unknowns / best-practice choices flagged by `/plan` Technical Context.

## R1 — Reference geometry extraction from `docs/references/Alternativ3.JPG`

**Decision**: Treat `Alternativ3.JPG` as the canonical RC34 1972 reference and extract principal superstructure dimensions by visual measurement at the scale established by the known LOA = 10.36 m (10360 mm).

**Extracted measurements** (side view, port-side facing camera, LOA scale):

| Component | Dimension | Reference (mm) | Method |
|---|---|---|---|
| Cabin trunk | length | 4600 | side-profile length from fore-cabin bulkhead to cockpit bulkhead |
| Cabin trunk | height above deck | 1100 | base of side wall to top of side wall (excluding crown) |
| Cabin trunk | forward width | 1900 | half-beam × 2 at cabin fwd station, narrower at the forward face per the tapered house |
| Cabin trunk | aft width | 2150 | half-beam × 2 at cabin aft station |
| Cabin trunk | forward rake angle | 8° | aft-leaning forward face |
| Cabin trunk | aft rake angle | 2° | near-vertical aft face |
| Cabin trunk | wall inset from sheer | 350 | port-side walkway width |
| Windshield | base Z above cabin top | 0 | windshield seats on cabin trunk top edge |
| Windshield | top Z above cabin top | 750 | windshield height |
| Windshield | rake angle at base | 35° | from vertical, aft-leaning |
| Windshield | rake angle at top | 38° | slight increase toward top — curving B-spline |
| Windshield | base width | 2050 | matches cabin aft width less ~50 mm trim |
| Windshield | top width | 1800 | top edge narrower by ~12% per the reference |
| Windshield | thickness | 25 | reasonable laminated-glass + frame thickness |
| Hardtop | length | 3700 | from windshield top to hardtop aft edge |
| Hardtop | forward width | 2200 | matches cabin aft + small outboard overhang |
| Hardtop | aft width | 2000 | aft taper per the reference |
| Hardtop | thickness | 60 | thin slab |
| Hardtop | height above deck | 2050 | from deck plate top to hardtop underside |
| Hardtop | leading-edge curl depth | 80 | downward curl at forward edge |
| Hardtop | leading-edge curl length | 250 | longitudinal extent of curl |
| Pillar | count per side | 2 | 4 visible total in side view |
| Pillar | diameter | 35 | small-diameter cantilevered post per reference |
| Pillar | forward X | 5400 | aft of windshield base |
| Pillar | aft X | 7800 | forward of cockpit aft edge |
| Pillar | inboard offset from sheer | 80 | clearance for railing posts outside pillars |
| Railing | post count per side | 6 | even spacing along the cockpit perimeter |
| Railing | post diameter | 25 | thinner than pillars |
| Railing | top rail diameter | 30 | slightly larger than posts |
| Railing | height above deck | 720 | calf-height per the reference |
| Railing | forward X | 0 | sweeps from bow back |
| Railing | aft X | 9800 | stops short of transom by 560 mm |
| Railing | inboard offset from sheer | 60 | inset from outboard edge |

**Rationale**: Visual extraction from the side-profile photo is the practical method given the constitution principle IV bar (±1% on principal dimensions). LOA scaling is exact (10.36 m is a confirmed RC34 1972 spec). Heights and lengths are read in pixels and converted at the scale. Out-of-plane dimensions (e.g., crown of cabin trunk roof) accept ~±2% measurement noise — outside the principal-dimension contract.

**Alternatives considered**:

- *3D scan of an actual Storebro RC34 1972*: out of project scope; no scan available. Future spec if a hull becomes available for scanning.
- *Naval architect drawings from Storebro AB archives*: project-tracking issue but no access today. Future spec if archives surface.
- *Synthetic CAD reverse-engineering from a model boat kit*: kit dimensions are themselves derived from photo measurements — adds an indirection layer without gaining fidelity.

## R2 — PartDesign idiom: which features for each component

**Decision**:

| Component | Sketch(es) | Feature(s) | Reason |
|---|---|---|---|
| Cabin trunk | 2 sketches: fwd-face rect, aft-face rect (on two datum planes at fwd_x and aft_x) | `PartDesign::AdditiveLoft` between the two | Trapezoidal+tapered prism with rake angles handled by the datum plane orientation; loft interpolates linearly across the four station vertices. |
| Windshield | 2 sketches: port-edge B-spline through 3 control points (base, mid, top), starboard-edge B-spline (mirrored or independently drawn) | `PartDesign::AdditiveLoft` between port and starboard edges | Lofting between two B-spline profiles produces the lateral interpolation that gives the windshield its surface; the B-spline cross-section gives the rake-changing vertical curve. |
| Hardtop | 2–3 sketches: forward outline rect, aft outline rect, optional curl profile | `PartDesign::AdditiveLoft` (forward → aft, taper) + `PartDesign::Pocket` or `PartDesign::SubtractiveLoft` for the leading-edge curl | Aft taper handled by the loft from a wider forward rect to a narrower aft rect; curl handled by a subtractive feature on the leading edge or by a separate curl-loft body that combines via `PartDesign::Boolean` (preferred). |
| Pillars | 1 sketch per pillar: circular cross-section on a deck-plate-top datum | `PartDesign::Pad` (height = hardtop underside Z – deck plate top Z, looked up per pillar X station) | One PartDesign Body per pillar keeps the model tree navigable; alternatively a single Body with a `PartDesign::PolarPattern` or `PartDesign::LinearPattern` consolidating all per-side pillars. Decision: **separate Body per pillar** to make individual selection easy in the GUI for future spec 010 (rubrail) work that may need to align with specific pillar X stations. |
| Railings | 2 sketches: rail-loop path wire (top view) + post circular profile | `PartDesign::AdditivePipe` (sweep the post profile along a rail-loop path) + multiple `PartDesign::Pad` per post | Top rail = single sweep along the perimeter path. Vertical posts = one Pad per post. Both inside a single `RailingsPortBody` (port-side rail + posts) and a mirrored `RailingsStarboardBody`. |

**Rationale**: This matches the spec 006 pattern where the hull was migrated from `Part::Loft` to `PartDesign::AdditiveLoft`. The same FreeCAD 1.1+ feature types apply here. PartDesign features keep the model tree editable in the GUI (constitution III) and produce the structural-determinism scrub-friendly artifact (spec 002).

**Alternatives considered**:

- *Single body containing the entire superstructure via `PartDesign::Boolean`*: rejected — collapsing the model tree into one super-body harms editability for downstream specs (010 hardware, 011 cutouts, 015 colors) that target individual components.
- *Pillars as `PartDesign::PolarPattern`*: rejected — pillars are mirror-symmetric across XZ, not radial. `Mirrored` is correct but per-pillar Bodies give individual handles for spec 010 to attach hardware to specific pillars.
- *Windshield as a thin shell via `PartDesign::Thickness`*: rejected for v1.1 — solid lofted prism is simpler and the eventual transparent-glass treatment in spec 011 can subtract a thinner inner solid. Stretch goal noted in spec 008's deferred markers.

## R3 — Sourcing deck-plate top Z from the actual hull body (not analytical)

**Decision**: After the deck plate Body is recomputed, read its `Shape.BoundBox.ZMax` to get the actual deck plate top Z at amidships, and read `Shape.BoundBox.XMin`/`XMax` for the deck plate longitudinal extent. For per-X-station deck top Z (used by pillar seating), compute by linearly interpolating the bounding box if the deck plate is approximately planar, OR by sampling the deck plate's top face wire vertices and lerping.

The v1.0.1 deck.py uses `hp.sheer_height_aft + t * (hp.sheer_height_fwd - hp.sheer_height_aft)` (deck.py:462–463, 531/586/627/680/732) which is the *analytical* sheer formula. Since spec 007 introduced `stem_rake_angle` that tilts the forward station forward, the analytical formula no longer matches the *actual* hull sheer at the forward end. This drift is the root cause of the pillars-piercing-the-hull bug.

The fix: a new private helper `_resolve_deck_top_z_at(deck_plate: DeckPlate, x: float) -> float` reads the actual built body's geometry. All five subsequent builders (cabin trunk, windshield, hardtop, pillars, railings) call this helper instead of the analytical formula.

**Rationale**: Aligns the superstructure with the *truth* (the constructed hull body) instead of a *prediction* (the analytical sheer formula). Insulates the deck module from any future hull parameter that changes the sheer shape without breaking deck construction. Matches the spec 003 §R8 v0.2.0 refinement note ("the 'true' Shape-face walk per research R8 is tracked as a v0.2.0 refinement alongside the PartDesign loft upgrade") — finally cashed in by this spec.

**Alternatives considered**:

- *Keep the analytical formula and update it whenever the hull changes*: rejected — couples the deck module to internal hull math, requires editing deck.py on every hull spec, brittle.
- *Have the hull module expose a `sheer_z_at(x)` method*: appealing but expands the hull module's public surface (FR-024 forbids that — PATCH-level constraint applies to hull too).
- *Re-derive the sheer from the hull parameters in deck.py*: same as v1.0.1, same bug — rejected.

## R4 — Back-compat for the existing `DeckParameters` (14-field flat dataclass)

**Decision**: Keep `DeckParameters` unchanged in field count, names, and types. Add a method `to_superstructure_parameters() -> DeckSuperstructureParameters` that maps the 14 legacy fields onto the 6 new dataclasses. The `build_deck()` function detects which form was passed and constructs the new dataclasses transparently:

```python
def build_deck(hull, parameters=None, *, parameters_superstructure=None, document=None, name="Deck"):
    if parameters is not None and parameters_superstructure is not None:
        raise DeckParameterError("parameters<>parameters_superstructure", None, "pass only one")
    if parameters_superstructure is None:
        legacy = parameters if parameters is not None else DeckParameters()
        parameters_superstructure = legacy.to_superstructure_parameters()
    # ... use parameters_superstructure throughout
```

The 14 legacy fields map onto the new dataclasses (with sensible defaults for the fields the legacy didn't have):

| Legacy field | New location |
|---|---|
| `deck_plate_thickness` | not in new dataclasses (deck plate is separate from superstructure) |
| `cabin_trunk_length` | `CabinTrunkParameters.length` (* meters→mm at the shim boundary) |
| `cabin_trunk_fwd_offset` | derived to `CabinTrunkParameters.wall_inset` + forward offset on the build path |
| `cabin_trunk_width` | both `CabinTrunkParameters.forward_width` and `.aft_width` set to this value (legacy = rectangular) |
| `cabin_trunk_height` | `CabinTrunkParameters.height` |
| `cabin_trunk_corner_radius` | dropped (the new trapezoid uses rake angles, not corner radii) — silently ignored on shim |
| `windshield_rake` | `WindshieldParameters.rake_angle_base` AND `.rake_angle_top` (legacy = single rake) |
| `hardtop_length` | `HardtopParameters.length` |
| `hardtop_height` | `HardtopParameters.thickness` (legacy meant "thickness of the slab", not height-above-deck) |
| `hardtop_overhang_fwd` / `_aft` | computed into `HardtopParameters.forward_x`/`aft_x` derived from cabin trunk position |
| `hardtop_pillar_diameter` | `PillarParameters.diameter` |
| `railing_height` | `RailingParameters.height_above_deck` |
| `deck_side_walkway` | derived to `PillarParameters.inboard_offset_from_sheer` ≈ `RailingParameters.inboard_offset_from_sheer` |

**Rationale**: Preserves the v1.0.0/v1.0.1 public API (constitution VI, semver PATCH). Existing CLI invocations and fixture-driven Alternativ1–5 builds continue to work unchanged. The shim is a deterministic mapping (no I/O, no time, no env) — preserves byte-identical reproducibility (constitution II).

**Alternatives considered**:

- *Deprecate `DeckParameters` and force callers to migrate*: rejected — that's a MINOR bump per semver, breaking back-compat. PATCH is the right shape for a same-API quality improvement.
- *Have `DeckParameters` inherit / proxy the new composite*: rejected — composition over inheritance, and the dataclass `frozen=True` + `__post_init__` validators already do the right thing. A shim method is simpler.
- *Add ALL the new fields onto the legacy `DeckParameters`*: rejected — would balloon the legacy dataclass to 32+ fields, defeating the readability gain that motivated splitting in the first place.

## R5 — Test strategy: silhouette, seating, layout invariance, reproducibility

**Decision**: Five categories of geometry tests, plus per-dataclass unit-test files:

1. **Silhouette overlay** (`test_deck_silhouette.py`): For each superstructure body, assert the bounding box dimensions match the R1 reference table within ±1% on principal dimensions. This is an automated, non-visual check that catches geometry drift without requiring image-overlay comparison.

2. **Pillar seating invariant** (`test_deck_pillar_seating.py`): For each layout in {1..5}, build the deck, then for every pillar Body assert `pillar.Shape.BoundBox.ZMin >= deck_plate.Shape.BoundBox.ZMax - 1.0`. Failure mode: the v1.0.1 regression.

3. **PartDesign idiom** (`test_deck_partdesign_feature_types.py`): For each superstructure body, assert `body.TypeId == "PartDesign::Body"`. For each body's `Group` (or its features), assert no `Part::Feature` raw shapes are present. Failure mode: regression to the v1.0.1 `Part.makeCylinder` etc.

4. **Layout invariance** (`test_deck_layout_invariance.py`): Build the same hull + same `DeckSuperstructureParameters` against layouts 1..5; assert `CabinTrunkBody.Shape.hashCode()` is identical across all five layouts. The Alternativ system varies *interior*, not *superstructure* (until spec 016 introduces the DS variant).

5. **Byte-identical reproducibility** (extend existing `test_deck_reproducibility.py`): Build twice with identical inputs; assert SHA-256 of the FCStd matches (same as v1.0.0/v1.0.1 reproducibility tests).

Unit tests (no FreeCAD runtime needed):

- `test_cabin_trunk_parameters.py` — 7 fields × validation paths (positive, range, rake angle bounds, taper invariant)
- `test_windshield_parameters.py` — 7 fields × validation paths (positive, top_z > base_z, top_width ≤ base_width)
- `test_hardtop_parameters.py` — 7 fields × validation paths (positive, aft_width ≤ forward_width, curl bounded by length + height)
- `test_pillar_parameters.py` — 5 fields × validation paths (count ≥ 0, diameter > 0, forward_x < aft_x, offset ≥ 0)
- `test_railing_parameters.py` — 7 fields × validation paths (count ≥ 0, diameters > 0, height > 0, ordering)
- `test_deck_superstructure_parameters.py` — composite construction + cross-component invariants (railing height < hardtop height)
- `test_deck_back_compat.py` — `DeckParameters.to_superstructure_parameters()` mapping correctness + `build_deck` accepts both legacy and new

**Rationale**: Matches the testing discipline established in specs 001–007. Unit tests are fast (no FreeCAD) and cover all parameter-validation paths. Geometry tests target the specific FRs that need a built body. Hash baselines refresh via spec 002's `refresh_hashes.py` — same pattern as 006/007.

## R6 — Hash baselines refresh procedure

**Decision**: After implementation completes and all 5 silhouette tests pass on the new geometry, run `uv run python scripts/refresh_hashes.py --module deck` to regenerate `tests/geometry/fixtures/expected_hashes.toml` for the `Deck_*` body entries. Commit the refresh in a separate commit (`chore(test-baselines): refresh deck hash baselines for spec 008 v1.0.2`) so the diff is easy to audit.

Hull hash baselines are NOT touched — spec 008 does not change `src/storebro/hull.py`.

**Rationale**: Same pattern as spec 006 (PartDesign hull upgrade refresh) and spec 007 (hull fidelity refresh). Separate-commit isolation lets the constitution V audit trail show "geometry changed → hashes regenerated" cleanly.

## R7 — CLI integration: does `storebro build --layout N` need changes?

**Decision**: No. `storebro build` calls `build_deck()` with no parameters (uses defaults), so the new shaped superstructure ships transparently to CLI users. The `--layout N` flag continues to drive interior variation only; superstructure is layout-invariant per spec 008 (and spec 016 will add the DS variant flag later).

**Rationale**: FR-024 + Assumption (PartDesign-Body idiom preserved; `build_deck` signature stable) guarantees this is true if the implementation respects them. The CLI module is unchanged.

## R8 — FreeCAD version & supported-range impact

**Decision**: Supported FreeCAD range stays at `>=1.1, <2.0` (declared in `pyproject.toml`). All PartDesign features used (`AdditiveLoft`, `AdditivePipe`, `Pad`, `Mirrored`, `Sketcher::Sketch` with `Part.BSplineCurve`) are present in 1.1.0+ and stable through 1.1.x. No 1.1.0 → 1.1.x compatibility shim needed.

**Rationale**: Confirmed against the FreeCAD 1.1 release notes (`https://wiki.freecad.org/Release_notes_1.1`) — none of the targeted feature types changed semantics in any 1.1.x patch release. Same conclusion as specs 006/007. No constitution VII action required.

---

**All NEEDS CLARIFICATION resolved. Ready for Phase 1 design.**
