# Quickstart: Interior Detail — Alternativ1 & 2

## Default — furniture comes for free (Alt1/Alt2)

```python
from storebro import build_hull, build_deck, build_interior

hull = build_hull()
deck = build_deck(hull)
interior = build_interior(hull, deck, layout="Alternativ1")

for c in interior.compartments:
    print(c.spec.name, c.is_furnished, len(c.furniture))
# ForwardCabin True 2   (berth + cushion)
# Galley       True 1   (counter, sink/stove recessed)
# Head         True 2   (toilet + sink)
# Salon        True 2   (settee + table)
```

## Alt3-5 stay boxy in this spec (spec 013 furnishes them)

```python
interior = build_interior(hull, deck, layout="Alternativ3")
interior.compartments[0].is_furnished   # False — boxy placeholder
```

## Customizing furniture

```python
from storebro import (
    build_interior, FurnitureParameters, BerthParameters, GalleyParameters,
)

fp = FurnitureParameters(
    berth=BerthParameters(base_height=400.0, cushion_count=2),
    galley=GalleyParameters(counter_height=920.0),
)
interior = build_interior(hull, deck, layout="Alternativ1", parameters_furniture=fp)
```

## Turning galley cutouts off

```python
from storebro import build_interior, FurnitureParameters, GalleyParameters

fp = FurnitureParameters(galley=GalleyParameters(cutouts_enabled=False))
interior = build_interior(hull, deck, layout="Alternativ1", parameters_furniture=fp)
# galley counter is a plain worktop, no recesses
```

## Validation example

```python
from storebro import GalleyParameters
from storebro.interior import InteriorParameterError

try:
    GalleyParameters(sink_recess_depth=50.0, counter_thickness=40.0)  # recess >= thickness
except InteriorParameterError as e:
    print(e)   # InteriorParameterError: ... 'galley_sink_recess_depth' ...
```

## Verify

```bash
uv run pytest -m "not requires_freecad"   # unit (validation) tests, no FreeCAD
uv run pytest -m requires_freecad         # geometry tests (needs FreeCAD 1.1+)
uv run ruff check src/ tests/ && uv run mypy src/
```
