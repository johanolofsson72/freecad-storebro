# Phase 1 Data Model — Deck Hardware Detailing

All additions are **additive, defaulted, validated** fields on the five existing
frozen dataclasses in `src/storebro/deck.py`. Existing fields/semantics are
unchanged. All lengths in mm. Each invalid value raises `DeckParameterError(name,
value, expected)`.

## RubrailParameters (existing fields: height, thickness, forward_x, aft_x)

| New field | Type | Default | Range / rule | Meaning |
|---|---|---|---|---|
| `outboard_fillet` | float | `12.0` | `0 < v <= min(height, thickness)/2` | rounded outboard-face radius |
| `chamfer_width` | float | `12.0` | `0 < v <= min(height, thickness)/2` | fallback chamfer width when the rounded loft fails the manifold gate |
| `chrome_insert` | bool | `True` | — | emit the chrome insert strip |
| `insert_height` | float | `18.0` | `0 < v < height` | chrome insert strip height |
| `insert_thickness` | float | `8.0` | `0 < v <= thickness` | chrome insert strip thickness (must fit the rubrail) |

## BowPulpitParameters (existing: tube_diameter, height, forward_extent, stanchion_count)

| New field | Type | Default | Range / rule | Meaning |
|---|---|---|---|---|
| `bend_radius` | float | `40.0` | `>= 0` (0 → straight corners) | radius of the swept tube corner arcs |
| `weld_beads` | bool | `True` | — | emit a torus weld-bead body at each joint |
| `weld_bead_radius` | float | `1.6 * (tube_diameter/2)` via default `18.0` | `0 < v` | torus minor radius (sits proud of the tube) |

## LifelineParameters (existing: line_count, tube_diameter, height_fraction)

| New field | Type | Default | Range / rule | Meaning |
|---|---|---|---|---|
| `sag_depth` | float | `25.0` | `>= 0` (0 → straight tube) | catenary mid-span dip |

## CleatParameters (existing: count_per_station, station_count, length, height)

| New field | Type | Default | Range / rule | Meaning |
|---|---|---|---|---|
| `base_taper` | float | `0.7` | `0 < v <= 1` | top-footprint fraction of the base footprint (1 = no taper) |
| `horn_rise` | float | `0.4 * height` via default `32.0` | `> 0` | how high the curved horn arcs above the base top |

## AnchorLockerParameters (existing: length, width, height, center_x)

| New field | Type | Default | Range / rule | Meaning |
|---|---|---|---|---|
| `cavity_depth` | float | `90.0` | `0 <= v < height` (0 → solid box, no cavity, no lid) | recessed cavity depth (must leave a floor) |
| `cavity_inset` | float | `40.0` | `0 < v < min(length, width)/2` | wall thickness around the cavity |
| `lid` | bool | `True` | — | emit a separate lid body (only when `cavity_depth > 0`) |
| `lid_thickness` | float | `20.0` | `0 < v` | lid slab thickness |

## New bodies produced

| Body label prefix | Construction | Render role |
|---|---|---|
| `Deck_RubrailChromeInsert_Port` / `_Starboard` | thin `Ruled=True` AdditiveLoft strip along the sheer | `metal` (chrome) |
| `Deck_BowPulpit_WeldBead_*` | `PartDesign::Revolution` torus at each joint (or fused into pulpit body) | `metal` (chrome) — inherited from `Deck_BowPulpit*` |
| `Deck_AnchorLockerLid` | separate `PartDesign::Body` slab over the cavity | `trim` (teak) |

## render.py `_ROLE_RULES` delta (ordering matters — most-specific first)

```
+ ("Deck_RubrailChromeInsert", "metal"),   # BEFORE ("Deck_Rubrail", "trim")
+ ("Deck_AnchorLockerLid", "trim"),        # BEFORE ("Deck_AnchorLocker", "superstructure")
```

(Weld beads need no rule — `Deck_BowPulpit*` already → `metal`.)

## Wrapper / aggregate changes

- `Rubrail` wrapper: gains `has_chrome_insert: bool` (and the insert body lives in
  the compound's `SideBodyLabels` or a parallel field). No removals.
- `BowPulpit` wrapper: unchanged shape (weld beads are children of the body / its
  compound). Optionally a `has_weld_beads: bool`.
- `AnchorLocker` wrapper: gains `has_cavity: bool` and an optional `lid` body
  reference. No removals.
- `Cleats` / `Lifelines` wrappers: unchanged shape (count/structure identical;
  only the per-body geometry is contoured/sagged).

## Invariants (from spec.allium)

- Every produced/modified body: `Solids == 1 && isValid()` (FR-009).
- Hull + deck plate identical with vs without hardware (FR-007 NOBOOL).
- Swept refinements (pulpit, lifeline) fall back to spec 010 construction on
  sweep failure, still emitting a valid body (FR-008).
- Rubrail profile ∈ {rounded, chamfered}, never the plain rectangle (FR-001).
- Locker cavity leaves a floor: `cavity_depth < height` (FR-006).
