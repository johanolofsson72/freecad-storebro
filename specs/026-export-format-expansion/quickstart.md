# Quickstart: Export Format Expansion

## Export the whole boat (assembly), not just the hull

```python
from storebro import (
    build_hull, build_deck, build_interior, build_propulsion,
    export_step, export_obj, export_iges,
)

hull = build_hull()
deck = build_deck(hull)
build_interior(hull, deck, layout="Alternativ3")
prop = build_propulsion(hull, deck)

bodies = [hull.body, deck.deck_plate.body, *(c.body for c in interior.compartments), ...]
art = export_step(bodies, "boat_assembly.step")   # every body, deterministic order
print(art.format, art.byte_count, art.sha256)
```

## New formats

```python
export_obj(bodies, "boat.obj")           # Wavefront OBJ (mesh)
export_iges(bodies, "boat.iges")         # IGES B-rep
# export_dxf_profile(bodies, "boat.dxf")  # 2D X-Z profile (if shipped by the spike)
```

## Single body unchanged

```python
export_step(hull.body, "hull.step")      # byte-identical to spec 002
```

## gzip any format

```python
export_stl(bodies, "boat.stl.gz", gzip=True)   # deterministic gzip (mtime 0)
import gzip
assert gzip.decompress(open("boat.stl.gz","rb").read()) == open("boat.stl","rb").read()
```

## CLI

```bash
storebro build --layout Alternativ3 --format step --out boat.step    # full assembly
storebro build --layout Alternativ3 --format obj  --out boat.obj
storebro build --layout Alternativ3 --format iges --out boat.iges
storebro build --layout Alternativ3 --format stl --gzip --out boat.stl.gz
```

## Verify (Definition of Done)

```bash
# Unit (no FreeCAD): extension validation, gzip determinism, DXF bytes
uv run pytest tests/unit/test_export_extension_validation.py \
              tests/unit/test_export_gzip_determinism.py \
              tests/unit/test_export_dxf_bytes.py

# Geometry (FreeCAD 1.1+ via bundled-python PYTHONPATH)
PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \
  uv run pytest -m requires_freecad \
    tests/geometry/test_export_assembly.py \
    tests/geometry/test_export_obj.py \
    tests/geometry/test_export_iges.py \
    tests/geometry/test_export_gzip_roundtrip.py \
    tests/geometry/test_export_single_body_unchanged.py

uv run ruff check . && uv run mypy src/
```

Two identical exports of any shipped format have equal SHA-256; a gzipped export decompresses to the un-gzipped one; the assembly contains every body.
