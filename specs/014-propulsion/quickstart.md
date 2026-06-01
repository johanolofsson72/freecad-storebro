# Quickstart: Propulsion Module

## Build the full boat with propulsion (CLI)

```bash
# Twin-screw (default) Alternativ3, full model with engine, shafts, props, rudders
uv run storebro build --layout Alternativ3 --out boat.FCStd

# Single-screw variant
uv run storebro build --layout Alternativ3 --engine-count 1 --out boat_single.FCStd

# Skip propulsion (pre-1.1.0 output: hull + deck + interior only)
uv run storebro build --layout Alternativ3 --no-propulsion --out boat_bare.FCStd
```

Open the `.FCStd` in FreeCAD 1.1+: the engine bed, engine block, shaft(s), propeller(s), and rudder(s) appear in the document tree with full sketch + feature history.

## Build propulsion from Python

```python
import FreeCAD
from storebro.hull import build_hull
from storebro.deck import build_deck
from storebro.propulsion import build_propulsion, PropulsionParameters

doc = FreeCAD.newDocument("storebro")
hull = build_hull(document=doc)
deck = build_deck(hull)

# Twin-screw default
prop = build_propulsion(hull, deck)
assert len(prop.shafts) == 2 and len(prop.propellers) == 2
assert prop.hull_modified is False

# Single-screw with a custom shaft angle and 4-blade prop
from storebro.propulsion import ShaftParameters, PropellerParameters
params = PropulsionParameters(
    engine_count=1,
    engine_offset_y_mm=0.0,
    shaft=ShaftParameters(angle_deg=12.0),
    propeller=PropellerParameters(blade_count=4),
)
prop1 = build_propulsion(hull, deck, parameters=params)
assert len(prop1.propellers) == 1
assert prop1.propellers[0].blade_count == 4
```

## Hull-only (no deck) — ceiling falls back to the sheer

```python
hull = build_hull(document=doc)
prop = build_propulsion(hull)          # deck omitted; engine ceiling = hull sheer
```

## Verify

```bash
uv run pytest -m "not requires_freecad"     # unit (param validation, version, CLI wiring)
uv run pytest -m requires_freecad           # geometry (needs FreeCAD 1.1+)
uv run ruff check .
uv run mypy src/
```

## Export

Propulsion bodies live in the same document as hull/deck/interior, so every exporter includes them automatically:

```python
from storebro.export import export_fcstd, export_step, export_stl, export_brep
export_fcstd(hull.document, "boat.FCStd")   # whole model incl. propulsion
```
