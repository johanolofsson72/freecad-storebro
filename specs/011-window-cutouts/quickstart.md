# Quickstart: Window & Porthole Cutouts

## Default — glazing comes for free

```python
from storebro import build_hull, build_deck

hull = build_hull()           # portholes cut into the topsides by default
hull.portholes.count          # 6 (3 per side)

deck = build_deck(hull)       # cabin windows + framed windshield by default
deck.cabin_windows.count      # 2 (1 per side)
deck.windshield.glass_pane    # a distinct glass-pane body
```

## Customizing glazing

```python
from storebro import (
    build_hull, HullGlazingParameters, PortholeParameters,
)

hg = HullGlazingParameters(portholes=PortholeParameters(count_per_side=4, diameter=180.0))
hull = build_hull(parameters_glazing=hg)   # 8 smaller portholes
```

```python
from storebro import (
    build_deck, DeckGlazingParameters, CabinWindowParameters, WindshieldGlazingParameters,
)

dg = DeckGlazingParameters(
    cabin_windows=CabinWindowParameters(count_per_side=2, length=700.0),
    windshield=WindshieldGlazingParameters(frame_border=80.0),
)
deck = build_deck(hull, parameters_glazing=dg)
```

## Turning glazing off

```python
from storebro import (
    build_hull, build_deck,
    HullGlazingParameters, PortholeParameters,
    DeckGlazingParameters, CabinWindowParameters, WindshieldGlazingParameters,
)

hull = build_hull(parameters_glazing=HullGlazingParameters(
    portholes=PortholeParameters(count_per_side=0)))         # no portholes

deck = build_deck(hull, parameters_glazing=DeckGlazingParameters(
    cabin_windows=CabinWindowParameters(count_per_side=0),    # no windows
    windshield=WindshieldGlazingParameters(enabled=False),    # solid slab windshield
))
```

## Validation example

```python
from storebro import CabinWindowParameters
from storebro.deck import DeckParameterError

try:
    CabinWindowParameters(corner_radius=500.0, height=350.0)  # 2*r > height
except DeckParameterError as e:
    print(e.parameter_name)   # "cabin_window_corner_radius"
```

## Verify

```bash
uv run pytest -m "not requires_freecad"   # unit (validation) tests, no FreeCAD
uv run pytest -m requires_freecad         # geometry tests (needs FreeCAD 1.1+)
uv run ruff check src/ tests/ && uv run mypy src/
```
