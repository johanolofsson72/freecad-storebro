# Quickstart: Interior Detail — Alternativ3, 4 & 5

## All five canonical layouts are now furnished

```python
from storebro import build_hull, build_deck, build_interior

hull = build_hull()
deck = build_deck(hull)

for layout in ("Alternativ3", "Alternativ4", "Alternativ5"):
    interior = build_interior(hull, deck, layout=layout)
    print(layout, [c.is_furnished for c in interior.compartments])
# Alternativ3 [True, True, True, True]
# Alternativ4 [True, True, True, True]
# Alternativ5 [True, True, True]   # 3 compartments, no galley
```

## Alt5 has no galley — graceful

```python
interior = build_interior(hull, deck, layout="Alternativ5")
types = [c.spec.compartment_type for c in interior.compartments]
assert "galley" not in types   # no galley compartment, no galley furniture, no error
```

## Custom YAML layouts stay boxy

```python
interior = build_interior(hull, deck, layout="/path/to/custom.yaml")
assert all(not c.is_furnished for c in interior.compartments)
```

## Verify

```bash
uv run pytest -m "not requires_freecad"
uv run pytest -m requires_freecad        # needs FreeCAD 1.1+
uv run ruff check src/ tests/ && uv run mypy src/
```
