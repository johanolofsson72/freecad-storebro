# Phase 0 Research — Deck Hardware Detailing

All risk in this spec is geometric: can the refined constructions stay manifold
(`Solids == 1 && isValid()`) on FreeCAD 1.1.1, given the specs 009/011/018
lessons that lofts/fillets can silently produce non-watertight meshes? A spike
(`/tmp/spike_022.py`) answered each before any production code, following the
spec 018/020 precedent.

## Decision 1 — Rubrail moulded profile: rounded fillet with chamfer fallback

- **Decision**: Build a rounded outboard face by adding two Sketcher arcs to the
  rubrail section, lofted `Ruled=True`. Guard with a manifold-or-fallback gate
  to a chamfered (straight-line) section.
- **Rationale**: Spike probe 1 — a rounded section lofted `Ruled=True` between
  two stations yields `Solids=1, valid=True, closed=True`. The rounded face is
  the authentic moulded-teak look; the chamfer is a proven-trivial fallback
  (straight lines never fail). `Ruled=True` (not `Ruled=False`) per the spec 018
  wall.
- **Alternatives**: chamfer-only (rejected — user promoted the rounded fillet);
  `Ruled=False` smooth loft (rejected — spec 018 overshoot wall).

## Decision 2 — Bow pulpit: AdditivePipe along an arc-filleted spine + torus beads

- **Decision**: Sweep a circular profile along a path whose corners are arcs
  (`PartDesign::AdditivePipe`, spec 020 idiom). Add a `PartDesign::Revolution`
  torus weld-bead body at each joint. Manifold-or-fallback to the spec 010
  straight `_pd_circle_pad` cylinders.
- **Rationale**: Spike probe 2 — a bent tube (vertical → quarter-arc → forward)
  swept via `makePipeShell` is `Solids=1, valid=True`. Probe 3 — a torus fused
  onto a cylinder is `Solids=1, valid=True`. The PartDesign `AdditivePipe`
  equivalent is the spec 020 swept-rail construction, already in `deck.py`.
- **Alternatives**: union of cylinders + spheres at joints (rejected — more
  bodies, hard right-angle reading); single fillet via `Part.makeFillet` on the
  union (rejected — fillet on a boolean union is the spec 018 non-manifold risk).

## Decision 3 — Lifelines: true catenary AdditivePipe

- **Decision**: Sample the catenary `z(x) = a·cosh(x/a) − a` with
  `a = span² / (8·sag)` into ≤ 12 points, sweep a circle along the B-spline
  spine. Manifold-or-fallback to the straight tube.
- **Rationale**: Spike probe 4 — the catenary path with `a = span²/8·sag`
  produced a computed mid-span dip of exactly 25.0 mm against the 25 mm target,
  and the swept tube is `Solids=1, valid=True`. `a = L²/8·sag` is the standard
  shallow-catenary approximation for the sag coefficient and is exact enough at
  these depths.
- **Alternatives**: parabolic B-spline (rejected — user promoted the true
  catenary; the cosh form is barely more code and is the physically correct
  curve); straight tube (kept only as the fallback).

## Decision 4 — Cleats: tapered loft base + curved horns that penetrate the base

- **Decision**: Loft the base `Ruled=True` between a larger bottom rectangle and
  a smaller top rectangle (taper). Sweep each horn as an `AdditivePipe` arc whose
  neck-posts drop **into** the base solid so the union merges.
- **Rationale**: Spike probe 5 first returned `Solids=2` because the horn floated
  above the base (gap between base-top z=40 and horn-end z=56). Re-running with
  the horn ends dropped to z=20 (inside the base) gave `Solids=1, valid=True`
  (`/tmp/spike_022b.py`). **Build rule: the horn neck must overlap the base by a
  positive margin.**
- **Alternatives**: separate horn body in the cleat compound (rejected — the spec
  wants a single manifold body per cleat); revolved horn (rejected — a swept arc
  is simpler and matches the AdditivePipe helper).

## Decision 5 — Anchor locker: Pocket cavity on the locker + separate lid body

- **Decision**: Cut a blind `PartDesign::Pocket` into the locker top (leaving a
  floor + walls), then emit a separate lid `PartDesign::Body` seated over the
  cavity (teak role). The hull and deck are never touched.
- **Rationale**: Spike probe 6 — a box minus an inset cavity box is
  `Solids=1, valid=True`; the separate lid slab is also `Solids=1`. The Pocket
  acts only on the locker body, so FR-007 (NOBOOL) holds trivially.
- **Alternatives**: hinged/ajar lid (out of scope — flat seated lid for v1 of
  this detailing pass); cavity-only, no lid (rejected — user promoted the lid).

## Render-role research

- `PALETTE["metal"]` → chrome material; `PALETTE["trim"]` → teak.
- `_ROLE_RULES` is **ordered, most-specific-first**, matched by `startswith`.
- Therefore: a `Deck_RubrailChromeInsert*` rule (→ `metal`) MUST precede the
  existing `("Deck_Rubrail", "trim")` rule, else the insert inherits teak.
- A `Deck_AnchorLockerLid*` rule (→ `trim`) MUST precede
  `("Deck_AnchorLocker", "superstructure")`, else the lid inherits gelcoat white.
- Weld beads labelled `Deck_BowPulpit*` already resolve to `metal` — no new rule.

## Summary

6/6 constructions manifold-safe; one build rule (cleat horn must overlap base).
No NEEDS CLARIFICATION remain. Proceed to design + tasks.
