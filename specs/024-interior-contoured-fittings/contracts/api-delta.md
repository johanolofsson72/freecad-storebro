# Library Contract Delta — Interior Contoured Fittings

Additive only. No public type/field/function removed. `build_interior` signature
unchanged. Each furniture dataclass gains contour + fabric fields (all defaulted,
`contoured=True`). `contoured=False` reproduces the spec 012/013 furniture.

```python
BerthParameters(..., contoured=True, cushion_segments=2, seam_gap=15.0,
                cushion_fillet=25.0, buttons_per_row=4, button_rows=2,
                button_radius=35.0, piping=True, piping_radius=12.0, fold_creases=2)
SalonParameters(..., contoured=True, seat_fillet=25.0, buttons_per_row=6,
                button_rows=1, button_radius=35.0, piping=True, piping_radius=12.0,
                fold_creases=2)
HeadParameters(..., contoured=True, toilet_fillet=30.0, bowl_radius=170.0,
               faucet=True, faucet_height=200.0)
GalleyParameters(..., contoured=True, edge_fillet=12.0, fascia=True,
                 fascia_thickness=18.0)
BulkheadParameters(..., contoured=True, corner_fillet=40.0, doorway=True,
                   doorway_width=600.0, doorway_height=1500.0)
```

## Behavioural contract
- Default furnished build → contoured fittings; each piece a single valid solid
  or a deterministic box fallback.
- `contoured=False` → byte-identical to specs 012/013.
- All contour ops byte-reproducible (furniture-determinism tests stay green).
