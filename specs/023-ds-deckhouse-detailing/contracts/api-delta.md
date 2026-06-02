# Library Contract Delta — DS Deckhouse Detailing

Additive only. No public type/field/function removed. Existing spec 016/019 DS
callers (`build_deck(superstructure_variant="ds", ...)`) build unchanged.

## deck.py — `DsWindowParameters` (additive fields)

```python
DsWindowParameters(
    count_per_side=3, length=1000.0, height=500.0, recess_depth=15.0,
    glass_panes=True, glass_thickness=6.0,                              # existing
    front_window=True, front_length=1400.0, front_height=420.0,        # NEW
    mullions_per_window=1, mullion_width=40.0,                          # NEW
    helm_door=True, helm_door_length=650.0, helm_door_height=1100.0,   # NEW
    helm_door_side="Starboard",                                        # NEW
)
```

## interior.py — `build_interior` (additive keyword)

```python
build_interior(
    layout, hull, *, parameters_furniture=None, document=None, name="Interior",
    apply_render_attributes=True,
    superstructure_variant="standard",   # NEW: "standard" | "ds"
)
```

- `superstructure_variant="ds"` builds the bundled `DsSaloon` enclosed-saloon
  layout, furnished (incl. a `helm` console+seat), with the DS headroom budget.
- `"standard"` (default) is byte-identical to the pre-spec-023 behaviour.

`FurnitureParameters` gains a `helm: HelmParameters` field (defaulted).

## CLI

No new flags required for the deckhouse detailing (it rides the existing
`storebro build --superstructure ds`). DS-interior CLI exposure is out of scope.

## Behavioural contract

- Deckhouse stays `Solids == 1 && isValid()` with any recess/boss combination.
- Front recess is skipped deterministically if it would break the manifold.
- Hull + deck plate identical with vs without the detailing.
- `"standard"` interior unchanged; `"ds"` adds the DS layout + helm furniture.
