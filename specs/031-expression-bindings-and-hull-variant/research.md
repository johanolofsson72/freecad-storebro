# Phase 0 Research — hull variant + deferred expression bindings

FreeCAD is unavailable on the dev machine, so this is a design spike on paper grounded in the actual
`hull.py` geometry; the maintainer's `requires_freecad` run confirms empirically.

## D1 — Hard-chine reshaping: move the v1 chine vertex (loft-safe, 5 vertices)

**The current section** (`_create_pentagon_legacy_station_sketch`, hull.py:673) is a 5-vertex
half-section:

```
v0 keel-centerline   (0,                 -keel_depth)
v1 bottom-outer/chine (half_beam_bottom,  -keel_depth * 0.6)   <-- the chine knuckle
v2 topside-turn      (half_beam_top,       0)
v3 outer-sheer       (half_beam_top,       freeboard)
v4 deck-centerline   (0,                   freeboard)
```

**Decision**: `hull_variant="hard_chine"` moves **only v1**: outboard toward `half_beam_top` and up
toward z=0. Two named constants:

- `_HARD_CHINE_BEAM_BLEND = 0.5` — `half_beam_bottom' = half_beam_bottom + (half_beam_top -
  half_beam_bottom) * blend`. Pushes the chine outboard → flatter bottom panel (v0→v1) and a
  sharper chine angle at v1.
- `_HARD_CHINE_CHINE_Z_FACTOR = 0.35` — replaces the `0.6` chine-depth factor, raising the chine
  (shallower), reinforcing the flatter bottom + more vertical topside read.

v0, v2, v3, v4 are untouched; **vertex count stays 5**, so the `Ruled=True` `AdditiveLoft` stays
vertex-compatible across every station including the thin stem (the spec 009 lesson — a 4-vertex
section breaks loft compatibility). `"standard"` leaves v1 at today's position.

**Alternatives considered**: new `SHARP_CHINE_QUADRILATERAL` topology (4 vertices) — rejected, spec
009 already proved it breaks stem loft compatibility; deadrise-angle recompute of all vertices —
more invasive, no clearer chine, rejected.

## D2 — `chine_z_factor` as an additive `_StationProfile` field (byte-identical standard)

The `0.6` chine-depth multiplier is currently a literal in the sketch builder. **Decision**: add
`_StationProfile.chine_z_factor: float = 0.6` and have the sketch builder use
`-keel_depth_mm * profile.chine_z_factor`. With the default 0.6, the standard path is **byte-identical**
to pre-031 (same literal value, now named). `_compute_stations` sets it to
`_HARD_CHINE_CHINE_Z_FACTOR` for hard-chine non-stem stations only.

The reshaping is applied in `_compute_stations` to `PENTAGON_LEGACY` **non-stem** stations only; the
thin stem (≈5 mm half-beam) is left alone (reshaping a near-point is meaningless and risks the loft).

## D3 — `hull_variant` keyword on `build_hull` (mirror `superstructure_variant`)

**Decision**: `build_hull(..., hull_variant: Literal["standard","hard_chine"] = "standard")`, exactly
mirroring `build_deck`'s `superstructure_variant`. NOT a `HullParameters` field — that keeps the
frozen dataclass and its fixtures byte-identical and matches the established variant pattern. Unknown
values raise `HullParameterError("hull_variant", value, "standard|hard_chine")` before any FreeCAD
call. `_compute_stations(resolved_params, hull_variant)` gains the param (default `"standard"`).

## D4 — SC-002 metric: amidships chine-beam ratio

At the amidships station (`s=0.50`): standard `half_beam_bottom = half_beam_max*0.40`,
`half_beam_top = half_beam_max` → `chine_beam_ratio = 0.40`. Hard-chine blends bottom halfway to top:
`0.40 + (1.0-0.40)*0.5 = 0.70` → ratio `0.70`. So `hard_chine ratio (~0.70) > standard ratio (0.40)`
by a clear margin — the asserted, measurable difference (verifiable from the station profile and the
built geometry's amidships cross-section).

## D5 — Manifold-or-fallback (FR-006)

**Decision**: factor the station→loft→mirror build inside `build_hull` so it can run twice. Build
the requested variant; after `recompute`, if `hull_variant=="hard_chine"` and
`not _is_single_valid_solid(body.Shape)`, remove the variant station/loft/mirror objects (from the
doc and the rollback list), reset `body.Tip`, and rebuild with `"standard"` stations; set
`variant_applied=False`. Then continue with the existing porthole cut + `_assert_hull_manifold`.
The reshaping is a mild, still-convex pentagon move, so the fallback is a safety net; the maintainer's
`requires_freecad` test exercises the happy path (manifold hard-chine) and reproducibility.

## D6 — DEFERRED: FreeCAD expression-engine bindings (no code ships)

**Design (recorded, not implemented):** FreeCAD expressions bind a feature property to an expression
string evaluated by the document's expression engine, e.g.
`feature.setExpression("Length", "Hull.loa * 1000")`. `build_hull` already mirrors parameters onto
body properties (`_bind_parameters_to_body_properties`), which would be the natural binding targets:
station datum offsets, loft section dims, and porthole placements would `setExpression` against those
properties so a GUI edit of `loa`/`beam_max` re-drives the parametric history (constitution III).

**Why deferred (user decision 2026-06-13):**

1. **No spike possible here.** FreeCAD is absent on the dev machine; expressions are a runtime engine
   feature that can only be validated by building, editing, and recomputing in a real document.
2. **Reproducibility risk on the spec 028 surface.** Expression strings serialize into
   `Document.xml`. Spec 028 established that `Document.xml` ordering/IDs are determinism-sensitive and
   that the topological-naming maps already resist cross-invocation parity. Adding expression strings
   (and the `ExpressionEngine` bookkeeping they create) could reintroduce per-session nondeterminism.
   This MUST be proven byte-reproducible before shipping (constitution II), and that proof needs
   FreeCAD.
3. **The hull is not one parametric sketch.** It is built from N computed station profiles, so there
   is no single sketch to bind — the binding surface is the per-feature property set, a larger design
   than a one-liner.

**Action:** tracked as `deferred HullBody.expression_bindings` + an `open question` in `spec.allium`;
revisit in a FreeCAD-equipped session. No `setExpression` code is written in spec 031.

## Open items

None for item 1 (all decisions resolved on paper; empirical confirmation is the maintainer's
`requires_freecad` run + GUI eyeball). Item 2 is explicitly deferred per the user decision above.
