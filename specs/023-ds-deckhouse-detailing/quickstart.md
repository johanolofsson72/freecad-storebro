# Quickstart — DS Deckhouse Detailing

## Build

```bash
# DS deckhouse with the finished detailing (front window, mullions, helm door).
uv run storebro build --superstructure ds --out ds.FCStd

# DS interior in Python:
uv run python -c "
from storebro.hull import build_hull
from storebro.interior import build_interior
import FreeCAD as App
doc = App.newDocument('ds')
hull = build_hull(document=doc)
interior = build_interior('Alternativ3', hull, superstructure_variant='ds')
print('compartments:', [c.label for c in interior.compartments])
"
```

## Eyeball in FreeCAD (constitution V)

Against `docs/references/storo34_side_lines.png`:

1. The raked front screen has a framed window recess with glass.
2. Each side window has vertical mullion bar(s).
3. One side wall has a tall helm-door recess.
4. In `--superstructure ds` the interior is the enclosed-saloon layout with a
   helm console + seat.

## Verify

```bash
uv run pytest -m "not requires_freecad"          # params, variant, helm
PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \
  uv run pytest -m requires_freecad -k "deckhouse or ds_interior"
uv run ruff check . && uv run mypy src/
```
