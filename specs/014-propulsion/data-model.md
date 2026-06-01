# Phase 1 Data Model: Propulsion Module

All units are millimetres (mm) and degrees (deg) unless noted. Coordinate convention (shared with hull/deck): **bow = XMax, stern = XMin, waterline = Z=0, port = +Y, starboard = −Y**. "Aft" = smaller X; "forward" = larger X.

## Parameter value types (frozen dataclasses, `__post_init__` validation → `PropulsionParameterError`)

### EngineBedParameters
| Field | Type | Default | Constraint |
|---|---|---|---|
| `length_mm` | float | 1400.0 | > 0 |
| `width_mm` | float | 120.0 | > 0 |
| `height_mm` | float | 200.0 | > 0 |

### EngineParameters
| Field | Type | Default | Constraint |
|---|---|---|---|
| `length_mm` | float | 1100.0 | > 0 |
| `width_mm` | float | 600.0 | > 0 |
| `height_mm` | float | 700.0 | > 0 |
| `station_x_mm` | float | 3500.0 | ≥ 0 |

### ShaftParameters
| Field | Type | Default | Constraint |
|---|---|---|---|
| `diameter_mm` | float | 45.0 | > 0 |
| `angle_deg` | float | 10.0 | 0 ≤ a ≤ 30 |
| `exit_x_mm` | float | 1800.0 | ≥ 0 |

### PropellerParameters
| Field | Type | Default | Constraint |
|---|---|---|---|
| `diameter_mm` | float | 450.0 | > 0 |
| `hub_diameter_mm` | float | 90.0 | > 0 AND < `diameter_mm` |
| `blade_count` | int | 3 | 2 ≤ n ≤ 6 |

### RudderParameters
| Field | Type | Default | Constraint |
|---|---|---|---|
| `chord_mm` | float | 300.0 | > 0 |
| `span_mm` | float | 500.0 | > 0 |
| `thickness_mm` | float | 40.0 | > 0 |
| `stock_diameter_mm` | float | 50.0 | > 0 |

### PropulsionParameters (composite)
| Field | Type | Default | Constraint |
|---|---|---|---|
| `engine_count` | int | 2 | ∈ {1, 2} |
| `engine_offset_y_mm` | float | 400.0 | ≥ 0 |
| `rudder_count` | int | `= engine_count` (resolved in `__post_init__` / factory) | ∈ {1, 2} |
| `engine_bed` | EngineBedParameters | factory default | — |
| `engine` | EngineParameters | factory default | — |
| `shaft` | ShaftParameters | factory default | — |
| `propeller` | PropellerParameters | factory default | — |
| `rudder` | RudderParameters | factory default | — |

**Composite cross-invariants** (raise `PropulsionParameterError`):
- `EngineCountSupported`: `engine_count ∈ {1, 2}`.
- `RudderCountSupported`: `rudder_count ∈ {1, 2}`.
- `SingleScrewIsCentred`: `engine_count == 1 ⟹ engine_offset_y_mm == 0`.
- `TwinScrewIsOffset`: `engine_count == 2 ⟹ engine_offset_y_mm > 0`.
- `ShaftExitForwardOfEngineStation`: `shaft.exit_x_mm < engine.station_x_mm` (shaft runs aft from engine to exit).

> `rudder_count` default-equals-`engine_count`: because `rudder_count` cannot reference another field in a plain dataclass default, the public factory / `build_propulsion` resolves `rudder_count=None` → `engine_count`. An explicitly-passed value is validated against `{1, 2}`.

## Build-context validation (checked in `build_propulsion`, raise `PropulsionParameterError`)
- `RejectEngineOffsetPastTopsides`: `engine_offset_y_mm + engine.width_mm/2 ≤ hull_half_beam_at(engine.station_x_mm)` — the engine must stay inboard of the sampled topside.
- Shaft exit must land in the aft underbody below the waterline: sampled `hull_bottom_z_at(shaft.exit_x_mm) < 0` and the computed shaft-exit Z ≤ 0.

## Output wrapper dataclasses (returned inside `Propulsion`)
Each wraps the produced `PartDesign::Body` plus the metadata the tests assert.

| Wrapper | Key fields |
|---|---|
| `EngineBed` | `body`, `parameters`, `is_port`, `volume_mm3`, `bbox_min_z_mm` |
| `EngineBlock` | `body`, `parameters`, `is_port`, `rests_on_bed: bool`, `within_hull_envelope: bool`, `pierces_hull_shell: bool`, `volume_mm3` |
| `Shaft` | `body`, `parameters`, `is_port`, `forward_z_mm`, `aft_z_mm`, `exit_x_mm`, `exit_z_mm`, `has_stern_tube_boss: bool`, `volume_mm3` |
| `Propeller` | `body`, `parameters`, `is_port`, `hub_x_mm`, `bbox_min_z_mm`, `blade_count`, `volume_mm3` |
| `Rudder` | `body`, `parameters`, `is_port`, `x_mm`, `bbox_min_z_mm`, `volume_mm3` |

## Aggregate: Propulsion
| Field | Type | Notes |
|---|---|---|
| `document` | Any | the FreeCAD document the bodies live in |
| `parameters` | PropulsionParameters | resolved parameters (rudder_count resolved) |
| `engine_beds` | list[EngineBed] | length == `engine_count` |
| `engines` | list[EngineBlock] | length == `engine_count` |
| `shafts` | list[Shaft] | length == `engine_count` |
| `propellers` | list[Propeller] | length == `engine_count` |
| `rudders` | list[Rudder] | length == `rudder_count` |
| `hull_modified` | bool | MUST be `False` (FR-007) |
| `build_duration_seconds` | float | metadata (excluded from determinism digest) |

## Invariants enforced at build / asserted in tests
1. **Manifold**: every wrapper's `body.Shape.Solids == 1` and `body.Shape.isValid()` (FR-008).
2. **FreeCAD-idiomatic**: every body is a `PartDesign::Body` with sketch+feature history (FR-009).
3. **Shaft down-and-aft**: `shaft.forward_z_mm > shaft.aft_z_mm`; `shaft.exit_z_mm ≤ 0`.
4. **Running-gear order**: `propeller.hub_x_mm < shaft.exit_x_mm` (prop aft of exit); `rudder.x_mm < propeller.hub_x_mm` (rudder aft of prop); both `bbox_min_z_mm < 0`.
5. **Engine containment**: `engine.within_hull_envelope == True`, `engine.pierces_hull_shell == False`.
6. **Counts**: beds/engines/shafts/propellers == `engine_count`; rudders == `rudder_count`.
7. **Twin symmetry**: with `engine_count == 2`, port count == starboard count; the starboard train is the +Y train mirrored to −Y.
8. **Hull untouched**: `propulsion.hull_modified == False`; hull `Solids` count unchanged before/after the call.
9. **Determinism**: two builds with identical params produce byte-identical exports (constitution II).
10. **Rollback**: a mid-build failure leaves zero orphaned objects in the document.

## State / lifecycle
No persistent state machine. The only lifecycle is the in-call build transaction: `start → (append bodies to `added`) → success | failure`. On failure, every object in `added` is removed in reverse order (mirrors `build_hull`/`build_deck`), and `PropulsionConstructionError` is raised (wrapping the underlying error); `PropulsionParameterError` passes through un-wrapped.
