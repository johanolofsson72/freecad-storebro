# Research — Spec 016 DS-Variant Superstructure

Phase 0 design decisions. Each resolves a Technical-Context choice or a clarified spec point.

## R1 — Variant selection mechanism

**Decision**: A new keyword `superstructure_variant: Literal["standard", "ds"] = "standard"` on `build_deck`, plus `--superstructure {standard,ds}` (default `standard`) on the CLI build subcommand.

**Rationale**: Mirrors the existing selector idiom — `build_interior(..., layout=...)` and the CLI `--layout` / `--engine-count` flags. A keyword with a literal default keeps every existing call site byte-identical (FR-002) and reads naturally. A `Literal` gives mypy --strict an exhaustive check and argparse `choices=` gives the CLI free validation + non-zero exit on a bad value (FR-015).

**Alternatives considered**:
- A separate `build_ds_deck()` function — rejected: duplicates the deck-plate/hardware/rollback/render wiring, two functions to keep in sync, and the CLI would still need a selector.
- An enum type `SuperstructureVariant` exported publicly — rejected for now: a 2-value string literal is lighter and matches how `layout` is a string; can promote to an enum later without breaking callers.

## R2 — Deckhouse geometry construction

**Decision**: Build the deckhouse as a single `PartDesign::AdditiveLoft` (Ruled=True) between two trapezoidal sketches — a lower trapezoid on an XY datum at the sampled deck-plate top Z, and an upper trapezoid on an XY datum at `deck_top + height_above_deck`. The upper forward edge is shifted aft by `height * tan(front_rake_angle)` to rake the front wall; the side taper comes from `forward_width <= aft_width`. The result is a **filled solid** whose top face is the flat roof and whose four side faces are the walls — no separate roof/wall bodies.

**Rationale**: This is exactly the proven `_build_cabin_trunk` idiom (deck.py:1539), grown to wheelhouse height and length. A Ruled=True loft between two closed trapezoids is a manifold solid by construction → `Solids == 1`, `isValid()` (FR-004, the spec 009 guard) with zero new failure modes. The clarified topology decision (single filled solid, not a hollowed shell) makes this direct. Reusing the idiom means the seating math (`_resolve_deck_top_z_at`), datum helpers (`_pd_make_datum_xy`), and loop-closure constraints (`_pd_close_loop_constraints`) are all shared.

**Alternatives considered**:
- Hollowed shell (Pad the footprint, Pocket the interior, separate roof slab) — rejected in /clarify: more features, more recompute, reintroduces the spec 009 non-manifold risk at the interior pocket walls, and the interior cavity is invisible behind the (opaque) walls anyway. The interior module already provides the visible inside volume.
- Multi-section loft for a curved front (like the windshield's 3-section B-spline) — rejected: the DS front in the reference is a near-planar raked screen; a single raked face is faithful within ±1% and avoids B-spline overshoot (the spec 008/009 lesson).
- `Part.makeBox` + boolean union of walls — rejected: violates constitution III (must stay PartDesign-editable) and risks non-manifold unions.

## R3 — DS window modeling

**Decision**: Side and front windows are blind `PartDesign::Pocket` recesses cut into the filled deckhouse solid, mirroring `_cut_cabin_windows` (deck.py:1815). `DsWindowParameters` carries `count_per_side`, `length`, `height`, `recess_depth`. An invariant requires `recess_depth < wall_inset` so a recess can never pierce through to split the solid.

**Rationale**: Blind recesses are manifold-by-construction — the spec 011 lesson ("the hull and cabin trunk are SOLID lofts, so cuts are blind recesses, not through-holes"). Reuses the existing pocket-cut helper pattern. Keeps STL export safe (SC-003). Clarified out of scope: separate translucent glass panes, mullions (deferred markers in spec.allium).

**Alternatives considered**:
- Through-cut windows with separate glass inserts (like the windshield frame+pane) — rejected in /clarify: through-cuts on a closed solid risk non-manifold tessellation (spec 009), and panes add bodies/scope beyond the light track. Deferred.

## R4 — `Deck` aggregate restructuring

**Decision**: Change `Deck.cabin_trunk`, `Deck.windshield`, `Deck.hardtop`, `Deck.hardtop_pillars` from required to `Optional[...] = None`; append `superstructure_variant: str` and `deckhouse: Deckhouse | None = None`. Standard variant: deckhouse None, the four slots populated as today. DS variant: the four slots None, deckhouse populated.

**Rationale**: Clarified decision. `Deck` is a frozen dataclass constructed only inside `build_deck`, so changing field types is non-breaking for external readers (standard-mode code reading `deck.cabin_trunk.length` still works because the slot is populated in standard mode). Appending fields preserves field order for the keyword-constructed aggregate. mypy --strict will force DS-mode consumers to None-guard, which is correct.

**Alternatives considered**:
- Keep all six slots always-populated and express the DS deckhouse *through* them (cabin_trunk = lower band, windshield = front screen, hardtop = roof, pillars count 0) — rejected: contorted, misleading field semantics, and the enclosed walls have no honest slot. The reference is genuinely a different topology.
- A separate `DsDeck` return type — rejected: forces callers to branch on type; the CLI/render/export pipeline wants one `Deck` shape.

## R5 — Parameter entry point + contradiction handling

**Decision**: DS inputs arrive via a new `parameters_deckhouse: DeckhouseParameters | None = None` keyword (default → `DeckhouseParameters()`), orthogonal to `parameters_superstructure` / `parameters_hardware` / `parameters_glazing`. Passing `variant="ds"` together with an explicit `parameters_superstructure` raises `DeckParameterError` (FR-014) before any FreeCAD call. The legacy `parameters` (DeckParameters) is still accepted in DS mode and drives the shared deck plate.

**Rationale**: Matches the established "one composite per concern, passed by keyword" pattern (hardware/glazing). The contradiction guard prevents silently ignoring a caller's open-flybridge intent. The deck plate is variant-independent, so legacy `parameters` stays meaningful.

**Alternatives considered**: silently ignore `parameters_superstructure` in DS mode — rejected: violates fail-fast (a caller who passed it expects it to matter).

## R6 — Reference measurements (storo34_side_lines.png) → defaults

Visual-extraction estimate-grade defaults at the canonical RC34 LOA (~10360 mm), consistent with how spec 008 sourced cabin-trunk defaults. Refinable in a PATCH bump if a primary source surfaces.

| Parameter | Default (mm / deg) | Basis (side-lines image proportion) |
|---|---|---|
| `length` | 6200 | Deckhouse spans ~60% LOA, amidships-to-aft of helm. |
| `forward_width` | 2000 | Slightly narrower front (sided-in screen). |
| `aft_width` | 2200 | Full beam-in at the aft saloon (taper invariant: fwd ≤ aft). |
| `height_above_deck` | 1500 | Standing headroom wheelhouse, taller than the 1100 mm open cabin trunk. |
| `front_rake_angle` | 30 | Raked windscreen, between the 25–38° standard windshield band. |
| `roof_thickness` | 60 | Matches the hardtop slab thickness (cosmetic; top face of the filled solid). |
| `wall_inset` | 250 | Side decks / walkway, ≥ window recess depth. |
| `fwd_offset` | 2200 | Foredeck length forward of the deckhouse. |
| `windows.count_per_side` | 3 | Three large saloon lights per side in the reference. |
| `windows.length` | 1000 | Large wraparound lights. |
| `windows.height` | 500 | Tall glazing band. |
| `windows.recess_depth` | 15 | Same blind-recess depth as spec 011 cabin windows; < wall_inset. |

Cross-hull defaults check: `fwd_offset (2200) + length (6200) = 8400 ≤ LOA 10360` ✓; `aft_width (2200) + 2*wall_inset (500) = 2700 ≤ beam_max` (beam ≈ 3300 mm) ✓.

## R7 — Render attributes

**Decision**: The deckhouse top-level body is labeled so `render.role_for_label` resolves it to the superstructure-white role (same as cabin trunk / hardtop). No new palette role; windows are recesses (no separate glass body to colour this spec). Verify the label (`Deck_Deckhouse` / `Deckhouse`) maps correctly; if not, extend the role map minimally.

**Rationale**: Spec 015 resolves role by Name then Label. The deckhouse is a white GRP superstructure element, identical role to the cabin trunk. Keeps FR-017 satisfied with zero palette change.

## R8 — Testing strategy (no interactive UI → no browser tests)

This is a library/CLI feature; the `.claude/docs/testing.md` destructive-browser-test phase does not apply (no DOM, no forms). Coverage instead:
- **Unit (no FreeCAD)**: parameter validation (every invariant + boundary), selector default, contradiction rejection, CLI flag parse/default/bad-value, Deck field population via lightweight fakes.
- **Geometry (`requires_freecad`)**: deckhouse manifold (`Solids==1`, `isValid()`), seated on deck-plate top (Z origin ≈ sampled top), principal dims within ±1% of defaults, blind-recess window count, STL export succeeds, standard-variant back-compat (six bodies unchanged, fields populated), DS-variant field population (four slots None, deckhouse set).

The variant selector is a simple synchronous branch (single actor, no concurrency, no state machine) → **/tla skipped** per the light-track triviality gate, consistent with specs 010/012/013/014.
