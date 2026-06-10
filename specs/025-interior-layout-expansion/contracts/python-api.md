# Public API Contract Delta: Interior Layout Expansion

Library; the contract is the public Python API + the YAML layout schema. Spec 025 is additive (MINOR, 1.11.0 → 1.12.0).

## Unchanged (back-compat guarantee)

- `build_interior(deck=None, *, hull=None, layout, document=None, name=None, parameters_furniture=None, ...)` — signature unchanged.
- `Interior`, `Compartment` — existing fields unchanged.
- `BerthParameters`, `GalleyParameters`, `HeadParameters`, `SalonParameters`, `HelmParameters`, `BulkheadParameters`, `FurnitureParameters` — existing fields unchanged.
- `InteriorParameterError`, `InteriorConstructionError` — unchanged.
- **SC-005 contract**: Alternativ1–4 and the DS layout produce byte-identical geometry to their pre-025 output.

## Added — YAML layout schema

- Compartment `type` now accepts `aft_cabin`, `dinette`, `engine_room`, `wet_locker`, `salon_galley` in addition to the existing five.
- Compartment `position.y` may now be non-zero (asymmetric placement), bounded by `|y| + width/2 <= beam_max/2`.

## Added — parameters

- **NEW** `EngineRoomParameters` (block dims + raised top + wall inset, all defaulted).
- **NEW** `WetLockerParameters` (wall thickness + shelf count/thickness + inset, all defaulted).
- `FurnitureParameters` gains `engine_room: EngineRoomParameters` and `wet_locker: WetLockerParameters` (defaulted).
- Both new dataclasses are exported from `storebro` and added to `interior.__all__`.

## Behavior contract

- **Furnish by type**: a compartment whose `type` is furnishable is furnished (`is_furnished == true`) in ANY layout — canonical, DS, or custom. Custom layouts no longer get placeholder boxes for furnishable types (FR-002).
- **salon_galley**: such a compartment's body is a `Part::Compound` containing settee + table + a galley counter (sink + stove recesses); the galley counter is a single valid solid (FR-001, FR-008).
- **New types**: `aft_cabin`→berth, `dinette`→settee+table, `engine_room`→engine-block-like solid, `wet_locker`→locker+shelves (FR-004); the furniture-fit envelope guard applies to each (FR-005).
- **Asymmetric**: `position.y != 0` is accepted and shifts the compartment + furniture transversely; a compartment past the half-beam raises `InteriorParameterError` before geometry (FR-006/FR-007).

## Invariants preserved

- Every furniture piece: single valid solid (`Solids==1`, `isValid()`); the galley counter manifold guard holds (FR-008).
- Identical inputs → byte-identical output (FR-009).
- No-overlap + hull-containment validation still hold for new types + asymmetric layouts (FR-013).
