# Phase 0 Research — windshield crown (crowned-section + frame-cut spike)

FreeCAD is unavailable on the dev machine, so this is a **design spike on paper** grounded in the
existing `deck.py` geometry; the maintainer runs the `requires_freecad` tests to empirically
confirm. Each decision below maps to a `/clarify` answer and an FR.

## D1 — Arc realisation: deterministic polyline, NOT a Sketcher circular arc

**Decision**: Approximate the upward arch of the top edge with a polyline of straight
`Part.LineSegment`s (a named, even segment count so a vertex lands exactly at the apex Y=0).

**Rationale**: The windshield sketches are byte-reproducibility-sensitive (their geometry lands in
`Document.xml` — the spec 028 surface). A `Sketcher` circular arc would invoke the constraint
solver, whose output can drift between runs (the spec 018/021 reproducibility lesson). Spec 021's
NACA foils set the precedent: straight-segment polylines loft cleanly and are byte-deterministic.

**Alternatives considered**: (a) single `Part.ArcOfCircle` — solver-nondeterminism risk, rejected;
(b) `Part.BSplineCurve` top edge — overkill and overshoot risk (spec 018 killed B-spline skins),
rejected.

**Arc geometry**: a circular arc of half-width `hw` (section half-width along Y) and apex rise
`r = crown_height` has radius `R = (hw² + r²) / (2r)` and profile
`y(x) = sqrt(R² − x²) − (R − r)` for `x ∈ [−hw, +hw]`. This is exact at the ends: `y(±hw) = 0`
(corners keep the flat-top Z) and at the apex `y(0) = r`. Requires `r < hw` (else `R ≤ r`,
degenerate) → the validity bound (D5). Polyline samples this `y(x)` at `N+1` evenly spaced x.

## D2 — Apply the arch to all three sections (uniform rise), not the top section only

**Decision**: All three loft sections (base/mid/top) receive the arched top edge with the **same**
apex rise `crown_height`; only the per-section half-width `hw` differs (base 1025, mid ≈962.5,
top 900 mm). Every section sketch then has identical vertex topology (2 bottom corners + N+1 arch
points).

**Rationale**: `AdditiveLoft Ruled=False` skins most robustly when consecutive profiles share
vertex count/structure. Matching profiles → a smooth fore-aft crowned cap and a well-behaved
B-spline skin. Arching only the top section (4-vertex base/mid vs N+3-vertex top) risks a twisted
or failed loft. Uniform rise also keeps the crown reading consistently along the rake.

**Alternatives considered**: top-section-only arch (mismatched profiles, loft-fragility) — rejected;
rise scaled per section — no visual benefit, extra magic, rejected.

## D3 — Narrowest section binds the validity check

The `top` section is the narrowest (`top_width = 1800 < base_width = 2050`). With a uniform rise,
`crown_height < top_width/2` guarantees `r < hw` for **every** section (base and mid are wider, so
their `hw` is larger and the inequality holds a fortiori). So a single check against `top_width/2`
is correct and conservative.

## D4 — Frame opening + glass pane: unchanged, margin preserved by construction

**Decision**: Leave the spec 011 `WindshieldFrameOpening` Pocket and `Deck_WindshieldGlass` pane
exactly as they are — a centered rectangle, `ThroughAll` along X, opening top at `top_z − frame_border`.

**Rationale**: The crown raises only the centerline; at the corners the arch rise is 0, so the
panel's corner top stays at the pre-030 flat-top Z. The frame opening is centered and rectangular,
so the solid margin above it equals `frame_border` at the corners (unchanged from the valid
flat-top config) and `frame_border + crown_height` at the center. The crown therefore only **adds**
material above the opening — it can never eat into the frame border. No new frame-margin computation
is needed; the invariant (FR-005) holds by construction. The frame/glass code runs after the panel
is finalised (crowned or fallen-back), so it is agnostic to which path produced the solid.

## D5 — Validity bound + fail-fast

**Decision**: `WindshieldParameters.__post_init__` rejects `crown_height` unless
`0.0 ≤ crown_height < top_width / 2`, after the existing `_reject_nonfinite_floats(self)` guard
(spec 029) already rejects NaN/±inf. Out-of-range → `DeckParameterError("windshield_crown_height",
value, "[0, top_width/2) mm")`.

**Rationale**: `< top_width/2` excludes the degenerate over-arch (`r ≥ hw` → semicircle/inversion).
`0.0` is the OFF sentinel (accepted). Mirrors every other `WindshieldParameters` field validation.

## D6 — Manifold-or-fallback (FR-009)

**Decision**: Factor the three section sketches + the `AdditiveLoft` into an inner helper
`_make_sections_and_loft(crowned: bool)` that returns the loft and the list of objects it created.
Build flow:

1. Create body + the three shared YZ datums (independent of crown).
2. `want_crown = ws.crown_height > 0.0`.
3. Build `_make_sections_and_loft(want_crown)`; recompute.
4. If `want_crown and not _is_single_valid_solid(body.Shape)`: remove the crowned sketches + loft
   from the doc and the `added` rollback list (the pulpit idiom, deck.py ~3403), restore Tip, then
   rebuild `_make_sections_and_loft(False)`; mark `fell_back = True`.
5. Run the spec 011 frame/glass code on the finalised body (unchanged).

`crown_height == 0.0` takes the flat path directly via the existing `_slab_sketch` (4-segment
rectangle) — the arched builder is **never** invoked at 0.0, guaranteeing byte-identical pre-030
output (FR-006). The arched builder at `crown_height → 0⁺` would emit N collinear top segments,
which is *not* the 4-segment rectangle, so the explicit branch is mandatory, not an optimisation.

**Reproducibility**: the polyline arc uses only `crown_height`, per-section `hw`, and a fixed named
segment count — all deterministic floats, no timestamps/random. Two builds in one process →
byte-identical (FR-010), as the maintainer's `requires_freecad` reproducibility test will pin.

## Open items

None. All five `/clarify` decisions and the spike questions are resolved on paper; empirical
confirmation (manifold, reproducible, frame-margin) is the maintainer's `requires_freecad` run +
GUI eyeball (constitution V).
