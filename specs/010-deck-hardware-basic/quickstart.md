# Quickstart: Basic Deck Hardware

## Default — hardware comes for free

```python
from storebro import build_hull, build_deck

hull = build_hull()
deck = build_deck(hull)        # rubrail, bow pulpit, lifelines, anchor locker, cleats included

deck.rubrail.height            # 0.06  (m)
deck.cleats.count              # 4
deck.lifelines.line_count      # 1
deck.anchor_locker.length      # 0.5   (m)
```

## Customizing hardware

```python
from storebro import (
    build_hull, build_deck,
    DeckHardwareParameters, RubrailParameters, CleatParameters,
)

hw = DeckHardwareParameters(
    rubrail=RubrailParameters(height=80.0, thickness=50.0),   # taller, prouder strip (mm)
    cleats=CleatParameters(count_per_station=1, station_count=3),  # 6 cleats (1/side × 3 stations × 2)
)
deck = build_deck(build_hull(), parameters_hardware=hw)
```

## Turning hardware off (zero counts)

```python
from storebro import build_deck, build_hull, DeckHardwareParameters, CleatParameters, LifelineParameters

hw = DeckHardwareParameters(
    cleats=CleatParameters(count_per_station=0, station_count=0),  # no cleats
    lifelines=LifelineParameters(line_count=0),                    # no lifelines
)
deck = build_deck(build_hull(), parameters_hardware=hw)  # builds the rest, no error
```

## Combining with a custom superstructure

```python
from storebro import build_deck, build_hull, DeckSuperstructureParameters, DeckHardwareParameters

deck = build_deck(
    build_hull(),
    parameters_superstructure=DeckSuperstructureParameters(),  # spec 008 composite
    parameters_hardware=DeckHardwareParameters(),              # spec 010 composite — independent
)
```

## Validation example

```python
from storebro import RubrailParameters
from storebro.deck import DeckParameterError

try:
    RubrailParameters(forward_x=5000.0, aft_x=1000.0)   # forward >= aft
except DeckParameterError as e:
    print(e.parameter_name)   # "rubrail_forward_x<>aft_x"
```

## Verify

```bash
uv run pytest -m "not requires_freecad"   # unit (validation) tests, no FreeCAD
uv run pytest -m requires_freecad         # geometry tests (needs FreeCAD 1.1+)
uv run ruff check . && uv run mypy src/
```
