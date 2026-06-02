# Phase 1 Data Model — DS Deckhouse Detailing

All additions are additive, defaulted, validated. Deckhouse lengths in mm;
interior dims in metres (the interior module's convention).

## DsWindowParameters (deck.py) — existing: count_per_side, length, height, recess_depth, glass_panes, glass_thickness

| New field | Type | Default | Rule | Meaning |
|---|---|---|---|---|
| `front_window` | bool | `True` | — | cut the raked front-face recess + glass |
| `front_length` | float | `1400.0` | `> 0` | front window width (mm) |
| `front_height` | float | `420.0` | `> 0` | front window height (mm) |
| `mullions_per_window` | int | `1` | `>= 0` | raised divider bars per side window |
| `mullion_width` | float | `40.0` | `> 0` | mullion bar width (mm) |
| `helm_door` | bool | `True` | — | cut the helm-door recess |
| `helm_door_length` | float | `650.0` | `> 0` | door width (mm) |
| `helm_door_height` | float | `1100.0` | `> 0` | door height (mm) |
| `helm_door_side` | str | `"Starboard"` | `in {Port, Starboard}` | which side wall |

(Validation lives on `DsWindowParameters.__post_init__`; the recess-vs-wall
manifold guard stays on `DeckhouseParameters` as today.)

## Interior (interior.py)

- `_COMPARTMENT_TYPES` gains `"helm"`.
- New furniture builder `_build_helm(spec, furniture, ...)` → a console box +
  a helm seat box (Part::Feature B-rep, the spec 012 idiom), trim role.
- `FurnitureParameters` gains a `helm: HelmParameters` sub-dataclass
  (`console_height`, `console_depth`, `seat_height`), defaulted + validated.
- `build_interior(..., superstructure_variant: Literal["standard","ds"] = "standard")`.
  - `"ds"` → loads the bundled `DsSaloon` layout (overriding `layout` for the
    fit-out), furnishes it (DsSaloon added to `_FURNISHED_LAYOUTS`), and passes a
    larger `headroom_budget_m` (the DS enclosed-saloon standing height).
  - `"standard"` → unchanged (original layout, 1.5 m headroom, no helm).
- `_validate_compartment_in_envelope(spec, hull, source, headroom_budget_m=1.5)`
  — the headroom check uses the budget; default 1.5 keeps standard unchanged.

## fixtures/DsSaloon.yaml

```yaml
schema_version: 1
layout_name: DsSaloon
source: docs/references/storo34_side_lines.png
compartments:
  - { name: ForwardCabin, type: forward_cabin, position: {x: 0.6, y: 0, z: 0.6}, dimensions: {length: 2.4, width: 2.0, height: 1.2} }
  - { name: Head,         type: head,          position: {x: 3.1, y: 0, z: 0.5}, dimensions: {length: 1.1, width: 1.0, height: 1.5} }
  - { name: Galley,       type: galley,        position: {x: 4.3, y: 0, z: 0.5}, dimensions: {length: 1.3, width: 1.1, height: 1.5} }
  - { name: HelmSaloon,   type: helm,          position: {x: 5.7, y: 0, z: 0.5}, dimensions: {length: 1.6, width: 2.3, height: 1.9} }
  - { name: Saloon,       type: salon,         position: {x: 7.4, y: 0, z: 0.5}, dimensions: {length: 2.4, width: 2.6, height: 1.9} }
```

(Heights up to ~1.9 m above the sole fit the DS standing-headroom budget; exact
values tuned during /implement to nest inside the deckhouse envelope.)

## New bodies / render roles

| Body | Render role | Note |
|---|---|---|
| Front glass pane (`Deck_DeckhouseWindowGlass*`) | glass | reuses spec 019 rule |
| Mullion bosses | superstructure | part of `Deck_Deckhouse` body |
| Helm-door recess | superstructure | recess in `Deck_Deckhouse` |
| Helm console + seat (`Interior_DsSaloon_HelmSaloon`) | trim | reuses `Interior_` rule |

No new render roles.

## Invariants

- Deckhouse `Solids == 1 && isValid()` after every recess/boss (FR-005).
- Hull + deck plate unchanged (FR-006 NOBOOL).
- Front recess skipped deterministically if it would break the manifold (FR-001).
- `"standard"` interior byte-identical to pre-spec-023 (FR-004).
