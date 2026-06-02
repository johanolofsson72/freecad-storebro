# Library Contract Delta — Deck Hardware Detailing

The public surface shape is **unchanged**: callers still call
`build_deck(hull, ..., parameters_hardware=DeckHardwareParameters(...))`. This
spec only adds **additive, defaulted fields** to the five hardware dataclasses
(re-exported from `storebro.deck`). No public type, field, or function is
removed or renamed. Existing callers compile and build unchanged (they simply
get the refined geometry by default).

## Additive public fields

```python
RubrailParameters(
    height=60.0, thickness=40.0, forward_x=300.0, aft_x=10000.0,   # existing
    outboard_fillet=12.0, chamfer_width=12.0,                       # NEW
    chrome_insert=True, insert_height=18.0, insert_thickness=8.0,   # NEW
)

BowPulpitParameters(
    tube_diameter=25.0, height=600.0, forward_extent=400.0, stanchion_count=2,  # existing
    bend_radius=40.0, weld_beads=True, weld_bead_radius=18.0,                    # NEW
)

LifelineParameters(
    line_count=1, tube_diameter=12.0, height_fraction=1.0,  # existing
    sag_depth=25.0,                                          # NEW
)

CleatParameters(
    count_per_station=1, station_count=2, length=200.0, height=80.0,  # existing
    base_taper=0.7, horn_rise=32.0,                                    # NEW
)

AnchorLockerParameters(
    length=500.0, width=400.0, height=150.0, center_x=8500.0,  # existing
    cavity_depth=90.0, cavity_inset=40.0, lid=True, lid_thickness=20.0,  # NEW
)
```

## Validation contract (each raises `DeckParameterError(name, value, expected)`)

- `outboard_fillet`, `chamfer_width` ∈ `(0, min(height, thickness)/2]`
- `insert_height` ∈ `(0, height)`; `insert_thickness` ∈ `(0, thickness]`
- `bend_radius >= 0`; `weld_bead_radius > 0`
- `sag_depth >= 0`
- `base_taper` ∈ `(0, 1]`; `horn_rise > 0`
- `cavity_depth` ∈ `[0, height)`; `cavity_inset` ∈ `(0, min(length, width)/2)`;
  `lid_thickness > 0`

## Behavioural contract

- **Back-compat**: `build_deck(...)` with no `parameters_hardware` builds the
  refined hardware by default; same call signature as spec 010.
- **Fallback**: bow pulpit + lifelines revert to the spec 010 straight
  construction on sweep failure, always emitting a valid body.
- **NOBOOL**: hull + deck plate shapes are identical with vs without hardware.
- **Manifold**: every produced/modified body has `Solids == 1 && isValid()`.

## CLI contract

No CLI flag changes. The existing `storebro build` produces the refined hardware
automatically. (Per-field CLI exposure is out of scope — same posture as spec
010, which exposed no hardware flags.)
