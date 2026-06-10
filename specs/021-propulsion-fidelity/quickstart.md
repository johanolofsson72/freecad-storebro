# Quickstart: Propulsion Fidelity

## Build the CAD-faithful train (default)

```python
from storebro import build_hull, build_deck, build_propulsion

hull = build_hull()
deck = build_deck(hull)
prop = build_propulsion(hull, deck)          # detail ON by default → foils, diesel, struts

assert prop.hull_modified is False            # hull never booleaned
for p in prop.propellers:
    assert p.airfoil_applied                  # foil blades (or False if the gate fell back)
    assert p.root_to_tip_twist_deg != 0.0
for r in prop.rudders:
    assert r.naca_applied                     # NACA foil rudder
for s in prop.shafts:
    assert s.has_coupling_flange and s.has_shaft_log_fairing
print(len(prop.struts), "strut bodies")       # separate top-level bodies
```

## Reproduce the spec 014 placeholder (all detail off)

```python
from storebro import (
    build_propulsion, PropulsionParameters,
    EngineParameters, ShaftParameters, PropellerParameters, RudderParameters,
)

plain = PropulsionParameters(
    engine=EngineParameters(detailed=False),
    shaft=ShaftParameters(coupling_flange=False, strut_bearing=False, shaft_log_fairing=False),
    propeller=PropellerParameters(airfoil_blades=False),
    rudder=RudderParameters(naca_foil=False),
)
prop = build_propulsion(hull, deck, parameters=plain)   # byte-identical to spec 014 (SC-006)
assert prop.struts == []
```

## CLI

```bash
storebro build --layout Alternativ3 --out boat.FCStd          # detailed propulsion
storebro build --layout Alternativ3 --no-propulsion-detail    # spec 014 placeholder fidelity
storebro build --engine-count 1                               # single screw, detailed
```

## Verify (Definition of Done)

```bash
# Unit (no FreeCAD): foil math + new parameter validation
uv run pytest tests/unit/test_propulsion_foil_math.py tests/unit/test_propulsion_detail_params.py

# Geometry (FreeCAD 1.1+ via bundled-python PYTHONPATH)
PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \
  uv run pytest -m requires_freecad tests/geometry/test_propulsion_propeller_foil.py \
                                     tests/geometry/test_propulsion_rudder_foil.py \
                                     tests/geometry/test_propulsion_shaft_detail.py \
                                     tests/geometry/test_propulsion_engine_detail.py \
                                     tests/geometry/test_propulsion_detail_determinism.py \
                                     tests/geometry/test_propulsion_placeholder_equiv.py

uv run ruff check . && uv run mypy src/
```

Then open `boat.FCStd` in the FreeCAD GUI and eyeball: twisted foil propeller, NACA rudder, coupling flange + strut + faired shaft exit, articulated diesel block (constitution V manual signoff).

## What to look for in the GUI

- **Propeller**: blades are leaf-shaped foils that visibly twist root→tip, not flat paddles.
- **Rudder**: rounded leading edge tapering to a fine trailing edge (a foil, not a plate).
- **Shaft**: a bolted collar at the gearbox end; a P-bracket bearing supporting the shaft below the hull; a smooth faired boss where the shaft exits the hull bottom.
- **Engine**: a stepped diesel block — sump hanging below, head/valve-cover on top, a row of exhaust stubs on one side.
- **Hull**: unchanged — no recess or cut where the shaft exits.
