# Phase 0 Research: Basic Deck Hardware

All "NEEDS CLARIFICATION" items were resolved during `/clarify` (see spec.md → Clarifications). This document records the construction-technique decisions for each hardware item, grounded in the existing `deck.py` patterns and the spec 008 / spec 009 deferral history.

## R1 — Rubrail construction

**Decision**: Build each side's rubrail as a `PartDesign::AdditiveLoft` (`Ruled=True`) between rectangular cross-section sketches placed on YZ-parallel datums at the sampled sheer stations, then mirror/repeat for port + starboard (one `PartDesign::Body` per side, wrapped in a `Part::Compound`).

**Rationale**: The sheer line is already sampled at 5 stations by `_sample_hull_sheer` and the deck-top Z is resolved by `_resolve_deck_top_z_at`. Lofting between per-station sketches reuses the hull/deck-plate loft idiom and follows the sheer exactly. `Ruled=True` is mandated because spec 009 proved `Ruled=False` (B-spline) is unstable on the Storebro profile (overshoots 22 mm–1900 mm), and spec 008 deferred the swept-pipe-along-perimeter approach for the same fragility reason.

**Alternatives considered**:
- *Sweep a profile along a sheer wire (`PartDesign::AdditivePipe`)* — rejected: spec 008 explicitly deferred `Railing.swept_top_rail_along_perimeter` due to AdditivePipe fragility on this geometry.
- *`Ruled=False` B-spline loft* — rejected per spec 009 overshoot evidence.

## R2 — Bow pulpit construction

**Decision**: Model the pulpit as straight tubular segments — small-diameter circular sketches padded along their axes (`PartDesign::Pad`): two vertical stanchions rising from the foredeck near the stem, plus horizontal/angled top-rail segments connecting them and wrapping forward. One `PartDesign::Body`, symmetric about the centerline.

**Rationale**: Mirrors how spec 008 modeled the railing top rail (a straight cylinder Pad) and posts. "Basic" hardware does not require bent-tube radii (deferred `BowPulpitBody.bent_tube_radii_and_welded_joints`). The stanchion bases seat on the actual deck-top Z via `_resolve_deck_top_z_at` at the bow station.

**Alternatives considered**:
- *Swept bent tube loop* — deferred (bent_tube_radii). Same AdditivePipe fragility concern as R1.

## R3 — Lifeline construction

**Decision**: One horizontal small-diameter tube per side per line, built as a `PartDesign::Pad` of a circular sketch on a YZ-parallel datum at the forward railing post, extruded along X from the forward post to the aft post. Height = `railing.height_above_deck * lifeline.height_fraction`. Lateral Y = the railing post Y (so the line sits on the posts). Default `line_count = 1`.

**Rationale**: Reuses the exact railing top-rail Pad technique from spec 008's `_build_railings`. The railing post stations are already computed there; lifelines mirror that geometry one rung down. Straight tubes (no catenary sag — deferred `LifelineBody.catenary_sag`).

**Zero-post fallback**: when the resolved `RailingParameters.post_count_per_side == 0`, no lifelines are built (FR-017, rule `SkipLifelinesWithoutPosts`). The lifeline builder reads the railing parameters that `build_deck` already resolved.

## R4 — Anchor locker construction

**Decision**: A raised low box/hatch built as its own `PartDesign::Body`: a rectangular sketch (`length × width`) on an XY-parallel datum at the foredeck top Z near the bow, padded up by `height`. Centered on the centerline at `center_x`.

**Rationale**: Clarified as a raised box, NOT a boolean recess. A `PartDesign::SubtractiveBox`/pocket into the deck plate risks the non-manifold tessellation that broke STL export for spec 009's bilge arc. A raised additive box is robust and still reads as a recognizable foredeck hatch. Footprint is validated to sit within the deck plate and forward of the cabin trunk (rules `RejectAnchorLockerOverlappingCabinTrunk`, `RejectAnchorLockerPastDeckEdge`).

**Alternatives considered**:
- *Boolean recess into deck plate* — deferred `AnchorLockerBody.functional_recessed_cavity` (non-manifold risk).

## R5 — Cleat construction

**Decision**: Each cleat is a `PartDesign::Body`: a base pad (small rectangle padded up) plus a horizontal horn bar (a circle/rounded-rect padded along Y) forming a simple horn-cleat proxy. Cleats are placed at `station_count` longitudinal stations, `count_per_station` per station, mirrored port/starboard, each seated on `_resolve_deck_top_z_at` at its X. All cleat bodies wrapped in a `Part::Compound`.

**Rationale**: Simple, robust additive geometry. Default layout: `count_per_station=1` (per side), `station_count=2`, every cleat mirrored port↔starboard → 1 × 2 × 2 = 4 cleats total (2 fwd, 2 aft) — matching the clarified default. Contoured castings deferred (`CleatBody.contoured_casting`).

**Note on default count math (per-side semantics)**: `count_per_station` is cleats *per side* at each station; `total_cleats = count_per_station * station_count * 2`. This matches the spec.allium `expected_cleat_total` formula exactly, so port/starboard symmetry is automatic and no even-count rule is required. Default 1 × 2 × 2 = 4.

## R6 — Parameter API surface

**Decision**: New frozen dataclasses `RubrailParameters`, `BowPulpitParameters`, `LifelineParameters`, `AnchorLockerParameters`, `CleatParameters`, bundled in a new frozen composite `DeckHardwareParameters` (all `field(default_factory=...)`). `build_deck` gains a new keyword-only argument `parameters_hardware: DeckHardwareParameters | None = None`. When `None`, defaults are used → existing callers get hardware automatically (FR-011).

**Rationale**: Clarified as a separate composite orthogonal to `DeckSuperstructureParameters`, keeping spec 008's composite untouched and the change purely additive. Validation lives in each dataclass `__post_init__` (raising `DeckParameterError`), mirroring spec 008's per-component dataclasses.

**Mutual exclusivity**: `parameters_hardware` is independent of the legacy-vs-superstructure mutual exclusivity — it can be combined with either. The existing `parameters` ⊕ `parameters_superstructure` guard is preserved unchanged.

## R7 — Default dimensions (RC34 1972, Alternativ3.JPG, estimate-grade)

| Item | Field | Default (mm) | Source |
|---|---|---|---|
| Rubrail | height / thickness | 60 / 40 | strip ~6 cm tall, ~4 cm proud — visual estimate at LOA 10360 |
| Rubrail | forward_x / aft_x | 300 / 10000 | near-stem to near-transom |
| Bow pulpit | tube_dia / height | 25 / 600 | matches railing post diameter; guard-rail height |
| Bow pulpit | forward_extent / stanchions | 400 / 2 | wraps ~0.4 m past deck edge |
| Lifeline | count / dia / height_fraction | 1 / 12 | single upper line at full railing height |
| Anchor locker | L/W/H / center_x | 500/400/150 / 8500 | foredeck hatch near bow (bow=XMax) |
| Cleat | count_per_station / stations / L / H | 1 / 2 / 200 / 80 | 4 total (per-side × stations × 2), 2 fwd 2 aft |

All estimate-grade, refinable in later PATCH bumps when a primary source surfaces (same posture as specs 003/007/008).

## R8 — Version bump + dunder fix

**Decision**: Bump `pyproject.toml` 1.0.3 → 1.0.4 and correct `src/storebro/__init__.py` `__version__` from the stale `1.0.2` to `1.0.4` (it was never bumped to 1.0.3 in spec 009).

**Rationale**: FR-019. The dunder drift is a pre-existing latent bug surfaced during this spec's grounding; fixing it here aligns the runtime `storebro.__version__` with the packaged version.
