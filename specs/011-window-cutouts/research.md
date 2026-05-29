# Phase 0 Research: Window & Porthole Cutouts

All "NEEDS CLARIFICATION" items were resolved during `/clarify` (spec.md → Clarifications). This records the construction decisions, grounded in `hull.py` / `deck.py` and the spec 009 non-manifold lesson.

## R1 — Why blind recesses, not through-holes

The hull (`hull.py` AdditiveLoft of filled cross-sections) and the cabin trunk (`deck.py` AdditiveLoft of trapezoids) are **solid** lofts, not thin shells — there is no interior cavity for a through-hole to enter. A through-cut into a solid either produces a port↔starboard tunnel (visually wrong, lets you see through the boat) or, mishandled, a non-manifold result — exactly the spec 009 failure that broke STL export. A **blind `PartDesign::Pocket`** of small depth into a solid is manifold by construction. Decision: portholes and cabin windows are blind recesses; only the thin windshield slab gets a clean through-opening.

## R2 — Porthole construction (hull.py)

**Decision**: For each porthole, a circular `Sketcher` profile on an XZ-parallel datum (normal = global Y) positioned at the station's topside outer-Y, then a `PartDesign::Pocket` with `Length = recess_depth` cutting inboard. The pocket features are appended to the existing `HullBody` after the Mirror feature, becoming the new body Tip — so they cut the full mirrored solid and keep the parametric history editable (constitution III).

**Manifold guard**: `recess_depth < local_half_beam_at_station` (the recess cannot reach the centerline / far side). Trivially satisfied by the 20 mm default vs. ~1 m half-beam, but enforced so a pathological depth is rejected before construction (FR-007).

**Placement**: 3 per side by default, evenly spaced over the cabin-trunk longitudinal extent (`forward_x..aft_x`), centered at `height_above_waterline` taken as mid-freeboard. Above-waterline guard on the resolved `center_z`.

**Symmetry**: one pocket at `+Y`, one at `−Y` per longitudinal station → port/starboard symmetric.

**Alternatives rejected**: separate `Part::Cut` with a cylinder tool (loses PartDesign editability); through-hole (no cavity, non-manifold risk).

## R3 — Cabin-trunk side window construction (deck.py)

**Decision**: A rounded-rectangle `Sketcher` profile (4 line segments + 4 arc fillets, or `Sketcher` rounded-rect) on a datum at the trunk side outer-Y, then a blind `PartDesign::Pocket` `Length = recess_depth` into each side wall, per side. Appended to the cabin-trunk body's feature tree after its loft.

**Manifold guard**: `recess_depth < cabin-trunk half-width at the window station`; the opening (length × height) must fit within the wall extents at its sill height (FR-007).

## R4 — Windshield frame + glass (deck.py)

**Decision**: Rework `_build_windshield`. After the existing 3-section AdditiveLoft slab is built, add a `PartDesign::Pocket` (`Type = ThroughAll`) of a smaller rectangle centered on the slab, leaving `frame_border` on all sides → the frame body. Then build a separate thin `PartDesign::Body` glass pane: a Pad of the opening rectangle with `Length = glass_thickness`, seated at the slab mid-plane. `Deck.windshield` now exposes both the frame body and the glass-pane body.

**Guard**: `2 * frame_border < slab_width` and `2 * frame_border < slab_height` (a positive opening must remain) — else `DeckParameterError` (FR-007).

**Fallback**: `WindshieldGlazingParameters.enabled = False` → the spec 008 solid slab is kept unchanged (FR-011, back-compat escape hatch).

**Behavior change**: `Deck.windshield` gains a `glass_pane` body alongside the (now framed) `body`. Existing windshield tests that assume a single solid slab will be updated (expected, additive — documented in spec Assumptions).

## R5 — Manifold / watertight assertion (FR-008)

After all cuts on a body, assert `len(body.Shape.Solids) == 1` and `body.Shape.isValid()`. On failure raise the module's `*ConstructionError` (triggers rollback). This is the spec 009 regression guard made explicit; blind recesses should never trip it, so a trip means a genuine bug.

## R6 — Parameter API surface

**Decision**: `PortholeParameters` → `HullGlazingParameters` composite → new `build_hull(..., parameters_glazing=None)` kwarg. `CabinWindowParameters` + `WindshieldGlazingParameters` → `DeckGlazingParameters` composite → new `build_deck(..., parameters_glazing=None)` kwarg. `None` → defaults (glazing on by default, FR-009). Independent of existing mutual-exclusivity guards (FR-010). Validation in each dataclass `__post_init__` raising the module's existing error type.

## R7 — Default dimensions (RC34 1972, estimate-grade)

| Item | Field | Default (mm) | Source |
|---|---|---|---|
| Porthole | count/side, diameter, recess depth | 3, 220, 20 | small round ports over the cabin |
| Porthole | height above waterline | mid-freeboard (derived) | centered in topside |
| Cabin window | count/side, length, height | 1, 900, 350 | long low cabin window |
| Cabin window | corner radius, recess depth | 80, 15 | rounded corners, shallow recess |
| Windshield | frame border, glass thickness | 60, 6 | frame border, glass pane |

Estimate-grade, refinable in later PATCH bumps (same posture as specs 007–010).

## R8 — Version bump

`pyproject.toml` 1.0.4 → 1.0.5 and `storebro.__version__` → 1.0.5 (spec 010 already aligned the dunder; the version-consistency test added in spec 010 guards it).
