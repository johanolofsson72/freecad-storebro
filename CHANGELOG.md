# Changelog

All notable changes to `freecad-storebro` are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Version numbers
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-05-17

Spec 007 — hull fidelity refresh. The default hull now reads as a
recognizable Storebro Royal Cruiser 34 (1972) in profile rather than a
faceted wedge. Parameter surface is additive only; the only new field
is `stem_rake_angle`. All other changes are default-value tweaks based
on the storebropassion.de RC34 1972 reference.

### Changed

- `HullParameters.draft` default: `0.95` → `1.10` m (matches the RC34 1972
  reference; the v1.0.0 value was estimate-grade and read low).
- `HullParameters.sheer_height_aft` default: `0.85` → `0.95` m.
- `HullParameters.sheer_height_fwd` default: `1.30` → `1.16` m. Sheer
  differential drops from `0.45` m to `0.21` m so the deck line reads
  near-flat from above, matching the reference.
- `HullParameters.deadrise_amidships` default: `16.0` → `8.0` degrees.
  The hull is semi-displacement, not planing; the new value flattens
  the bottom accordingly.
- `HullParameters.transom_angle` default: `12.0` → `5.0` degrees.
  Near-vertical transom per the Alternativ side-profile drawings.
- Stem station: was a single degenerate vertex at LOA; is now a finite
  80mm-wide blunt stem face with a small forefoot, so the bow has
  substance instead of a knife edge. Topologically a 5-vertex pentagon
  matching the other four stations, which lets `PartDesign::AdditiveLoft`
  map vertices 1:1 across the hull without twisting.

### Added

- `HullParameters.stem_rake_angle`: new field, default `6.0` degrees,
  range `[0, 30]`. Tilts the Stem datum forward around the support's
  local Y axis so the bow has the slight forward lean visible on the
  reference. Surfaces a corresponding `Body.StemRakeAngle` property
  in the FreeCAD GUI (the 9th named hull property).

### Deferred

- Smooth B-spline loft (`AdditiveLoft.Ruled=False`) — with only five
  stations the B-spline interpolation overshoots between the wide
  amidships and the narrow stem (port bbox extends past +3000 mm
  instead of +1600 mm). Awaits a denser station set in a future
  PATCH; tracked as `deferred Hull.b_spline_loft` in the Allium spec.
- Quarter-circle bilge arc transition — requires the B-spline loft
  to be in place first so the sketch wire topology stays consistent
  between rounded non-stem stations and the rectangular stem. Tracked
  as `deferred Hull.bilge_arc` in the Allium spec.

### Tests

- `tests/geometry/test_hull_silhouette.py` — bbox dimensions match the
  reference within tolerance: LOA `10.35` m ±1%, beam `3.20` m ±2%,
  Z-envelope `1.5–2.3` m, hull is a closed manifold solid.
- `tests/geometry/test_hull_bspline_loft.py` — the loft produces a
  positive-volume closed solid (regardless of Ruled mode).
- `tests/unit/test_hull_parameters_stem_rake.py` — range validation
  on the new `stem_rake_angle` field.

### Hashes

`tests/geometry/fixtures/expected_hashes.toml` refreshed against
FreeCAD 1.1.1 with the new defaults. Source hash key changed from
`b8fac77b0986` to `b0380b2cc068` because `HullParameters.__repr__`
now includes the new `stem_rake_angle` field.

## [1.0.0] - 2026-05-17

Initial public release. Hull + deck + interior + export/CLI usable
end-to-end. All four v1.0 modules shipped per spec 001 (hull), spec 002
(export), spec 003 (deck), spec 004 (interior), spec 005 (CLI), and
spec 006 (PartDesign rebuild making the hull editable in the FreeCAD GUI).
