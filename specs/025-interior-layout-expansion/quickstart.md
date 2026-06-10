# Quickstart: Interior Layout Expansion

## Alternativ5 now shows its galley

```python
from storebro import build_hull, build_deck, build_interior

hull = build_hull()
deck = build_deck(hull)
interior = build_interior(deck, layout="Alternativ5")

galley_salon = next(c for c in interior.compartments if c.spec.compartment_type == "salon_galley")
assert galley_salon.is_furnished
# its compound carries settee + table AND a galley counter (sink + stove recesses)
```

## A custom layout now gets real furniture

```yaml
# my_boat.yaml
schema_version: 1
layout_name: MyCustomBoat
compartments:
  - name: VBerth
    type: forward_cabin
    position: { x: 0.5, y: 0, z: 0.6 }
    dimensions: { length: 2.4, width: 2.0, height: 1.2 }
  - name: PortHead          # off-centre to port
    type: head
    position: { x: 3.2, y: 0.6, z: 0.5 }
    dimensions: { length: 1.0, width: 1.0, height: 1.4 }
  - name: EngineRoom
    type: engine_room
    position: { x: 6.0, y: 0, z: 0.4 }
    dimensions: { length: 1.6, width: 1.8, height: 1.0 }
  - name: WetLocker         # off-centre to starboard
    type: wet_locker
    position: { x: 3.2, y: -0.7, z: 0.5 }
    dimensions: { length: 0.8, width: 0.8, height: 1.6 }
```

```python
interior = build_interior(deck, layout="path/to/my_boat.yaml")
for c in interior.compartments:
    assert c.is_furnished                  # furnished by type — not a box
    for piece in c.furniture:
        s = piece.Shape
        assert len(s.Solids) == 1 and s.isValid()
```

## Asymmetric placement

```python
# A head at y=0.6 (port) and a locker at y=-0.7 (starboard) build off-centre.
# A compartment with |y| + width/2 > beam_max/2 raises InteriorParameterError
# before any geometry is built.
```

## Verify (Definition of Done)

```bash
# Unit (no FreeCAD): type set, new-type params, asymmetric + transverse validators
uv run pytest tests/unit/test_interior_compartment_types.py \
              tests/unit/test_interior_asymmetric_validation.py

# Geometry (FreeCAD 1.1+ via bundled-python PYTHONPATH)
PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \
  uv run pytest -m requires_freecad \
    tests/geometry/test_interior_alt5_galley.py \
    tests/geometry/test_interior_custom_furnished.py \
    tests/geometry/test_interior_new_types.py \
    tests/geometry/test_interior_asymmetric_geometry.py \
    tests/geometry/test_interior_expansion_determinism.py \
    tests/geometry/test_interior_canonical_byte_identity.py

uv run ruff check . && uv run mypy src/
```

Then open a built `.FCStd` in the FreeCAD GUI and eyeball the Alternativ5 galley, the custom-layout furniture, and the off-centre compartments (constitution V).
