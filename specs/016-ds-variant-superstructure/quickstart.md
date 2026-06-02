# Quickstart — DS-variant superstructure

## Library

```python
from storebro import build_hull, build_deck
from storebro.deck import DeckhouseParameters, DsWindowParameters

hull = build_hull()

# Standard open-flybridge superstructure (unchanged default).
deck_std = build_deck(hull)
assert deck_std.superstructure_variant == "standard"
assert deck_std.deckhouse is None
assert deck_std.cabin_trunk is not None

# DS enclosed deck-saloon variant.
deck_ds = build_deck(hull, superstructure_variant="ds")
assert deck_ds.superstructure_variant == "ds"
assert deck_ds.deckhouse is not None
assert deck_ds.cabin_trunk is None          # open-flybridge bodies absent
assert deck_ds.deckhouse.body.Shape.Solids.__len__() == 1   # single manifold solid
assert deck_ds.railings is not None         # shared hardware still present

# Custom deckhouse dimensions.
deck_tall = build_deck(
    hull,
    superstructure_variant="ds",
    parameters_deckhouse=DeckhouseParameters(
        height_above_deck=1600.0,
        aft_width=2300.0,
        windows=DsWindowParameters(count_per_side=4, length=900.0),
    ),
)
```

## CLI

```bash
# Standard (default)
uv run storebro build --layout 3 --out boat.FCStd

# DS enclosed deck saloon
uv run storebro build --layout 3 --superstructure ds --out boat_ds.FCStd
```

## Verify

```bash
uv run pytest tests/unit/test_deckhouse_validation.py tests/unit/test_cli_superstructure_flag.py -x
uv run pytest -m requires_freecad tests/geometry/test_deckhouse_build.py -x   # needs FreeCAD 1.1+
uv run ruff check . && uv run mypy src/
```

Then open `boat_ds.FCStd` in the FreeCAD GUI and eyeball the enclosed wheelhouse against `docs/references/storo34_side_lines.png` (constitution V).
