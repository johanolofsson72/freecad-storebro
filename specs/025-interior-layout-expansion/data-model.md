# Phase 1 Data Model: Interior Layout Expansion

All types live in `src/storebro/interior.py`. New fields are appended with defaults (back-compat). Lengths metres in the YAML/validators, converted to mm at the geometry boundary via `_M_TO_MM` (spec 017).

## Compartment types

`_COMPARTMENT_TYPES` (currently `{forward_cabin, galley, head, salon, helm}`) gains:
```
aft_cabin, dinette, engine_room, wet_locker, salon_galley
```
New module constant — one source of truth for the dispatch + furnish gate:
```python
_FURNISHABLE_TYPES = _COMPARTMENT_TYPES   # every type is furnishable in v1.12
```
(If a future structural-only type is added, it is excluded from `_FURNISHABLE_TYPES` and falls through to a box.)

## Furniture-builder dispatch (`_build_compartment`)

| `compartment_type` | builder(s) |
|---|---|
| forward_cabin | `_build_berth` (unchanged) |
| galley | `_build_galley_counter` (unchanged) |
| head | `_build_head_fittings` (unchanged) |
| salon | `_build_salon_furniture` (unchanged) |
| helm | `_build_helm` (unchanged) |
| **aft_cabin** | `_build_berth` (reuse) |
| **dinette** | `_build_salon_furniture` (reuse) |
| **engine_room** | `_build_engine_room_fitting` (NEW) |
| **wet_locker** | `_build_wet_locker` (NEW) |
| **salon_galley** | `_build_salon_furniture` + `_build_galley_counter` (both) |

A bulkhead is appended per furnished compartment as today. The galley manifold guard (`Solids==1` rebuild) runs for any compartment that builds a galley counter (galley AND salon_galley).

## New parameter dataclasses (frozen)

### `EngineRoomParameters`
```
block_length_m: float = 1.2
block_width_m: float = 0.7
block_height_m: float = 0.7
raised_top_height_m: float = 0.15   # stepped head/cover on top (engine-block read)
wall_inset_m: float = 0.05
```
Validation (`__post_init__`): all dims positive/finite; `raised_top_height_m < block_height_m`.

### `WetLockerParameters`
```
wall_thickness_m: float = 0.03
shelf_count: int = 2
shelf_thickness_m: float = 0.02
wall_inset_m: float = 0.05
```
Validation: positive/finite; `shelf_count >= 0`.

### `FurnitureParameters` (existing composite) — appended fields
```
engine_room: EngineRoomParameters = field(default_factory=EngineRoomParameters)
wet_locker: WetLockerParameters = field(default_factory=WetLockerParameters)
```
(`salon_galley` reuses `salon` + `galley`; `aft_cabin` reuses `berth`; `dinette` reuses `salon`.)

## Validation changes

- **`_parse_compartment_entry`**: remove the `position.y != 0` reject (FR-006). Keep all other position parsing.
- **`_validate_compartment_in_envelope`**: add the transverse bound (FR-007):
  ```
  if abs(spec.position.y) + spec.dimensions.width / 2 > hull.parameters.beam_max / 2:
      raise InteriorParameterError(source, name, "position.y",
          "compartment extends past the hull half-beam (|y| + width/2 > beam_max/2)")
  ```
- **`_validate_furniture_envelope`**: extend the height-fit checks to the new furnishable types (aft_cabin → berth height; dinette/salon_galley → salon seat / galley counter height; engine_room → block height; wet_locker → locker height), each rejecting a fitting taller than the compartment.

## Geometry change: `offset_y`

Every furniture builder centres its pieces on `offset_y = spec.position.y * _M_TO_MM` instead of the hardcoded `0`. E.g. `_build_berth` changes `FreeCAD.Vector(x0, -width/2, z0)` → `FreeCAD.Vector(x0, offset_y - width/2, z0)`. Canonical layouts (`y=0`) → `offset_y=0` → byte-identical (FR-011).

## Output wrappers / aggregate

No new public output types. `Compartment` (existing: `spec`, `body`, `furniture`, `is_furnished`) and `Interior` are unchanged in shape. `is_furnished` becomes true for furnishable-type compartments in ANY layout (was: only bundled-layout compartments).

## Compatibility

- `_COMPARTMENT_TYPES` widening is additive (more YAML values accepted).
- New param dataclasses + the two `FurnitureParameters` fields have defaults → existing construction unaffected.
- `build_interior` signature unchanged.
- Fixture change: `Alternativ5.yaml` combined compartment `type: salon` → `type: salon_galley` (the only data change; FR-011).
- Version 1.11.0 → 1.12.0.
