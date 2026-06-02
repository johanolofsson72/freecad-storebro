# Quickstart: Render Attributes

## Build a colored model (default)

```bash
uv run storebro build --layout 3 --out boat.FCStd
```

Open `boat.FCStd` in the FreeCAD GUI: hull gelcoat-white, rubrail + interior joinery teak-brown, railings/pulpit/cleats chrome-grey, windshield glass translucent, propeller bronze, engine dark grey-green.

> Note: render colors are stored as durable App data properties (`RenderColor` / `RenderMaterial` / `RenderMaterialName` in the `Render` group) that persist headless. GUI-visible color is set via the ViewObject when a GUI session is present (the maintainer's signoff step); a purely headless build still carries the color data on every body.

## Build a neutral (uncolored) model

```bash
uv run storebro build --layout 3 --out boat_neutral.FCStd --no-colors
```

Geometry is byte-identical to a build that never applied attributes; bodies keep FreeCAD's default appearance.

## Library use

```python
import FreeCAD
from storebro import build_hull, build_deck, apply_render_attributes, PALETTE, role_for_label

doc = FreeCAD.newDocument("demo")
hull = build_hull(document=doc)                         # colored by default
deck = build_deck(hull, apply_render_attributes=False)  # opt out for this body

# Inspect / re-apply manually
print(role_for_label(hull.body.Label))                  # "hull"
print(PALETTE["glass"].color)                            # (..., alpha<1.0)
apply_render_attributes([deck.deck_plate.body], enabled=True)  # color one object
print(hull.body.RenderColor)                             # persisted RGBA data property
```

## Verify

```bash
PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib uv run pytest -k render
uv run pytest -m "not requires_freecad" -k render        # palette/role unit tests only
uv run ruff check . && uv run mypy src/
```
