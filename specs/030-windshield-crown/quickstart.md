# Quickstart — windshield crown

## Build a crowned windshield (default)

```bash
uv run storebro build --layout Alternativ3 --out boat.FCStd
```

The windshield now ships with a 60 mm transverse crown — its top edge arches upward at the
centerline. Open `boat.FCStd` in FreeCAD and view head-on (front view): the windshield top reads as
a gentle upward bow rather than a flat bar.

## Tune or disable the crown (library)

```python
from storebro.deck import WindshieldParameters

crowned = WindshieldParameters()                  # crown_height = 60.0 (default)
taller  = WindshieldParameters(crown_height=90.0) # more pronounced arch
flat    = WindshieldParameters(crown_height=0.0)  # OFF — byte-identical to pre-030
```

Invalid values fail fast:

```python
WindshieldParameters(crown_height=-5.0)     # DeckParameterError: [0, top_width/2) mm
WindshieldParameters(crown_height=1000.0)   # DeckParameterError (>= top_width/2 = 900)
WindshieldParameters(crown_height=float("nan"))  # DeckParameterError (non-finite)
```

## Verify

```bash
# Unit (no FreeCAD) — parameter validation:
uv run pytest tests/unit/test_windshield_crown.py -q

# Geometry (maintainer, needs FreeCAD) — crown shape, manifold, frame margin, reproducibility:
uv run pytest -m requires_freecad -k windshield_crown -q

# Full gates:
uv run pytest -m "not requires_freecad" -q && uv run ruff check . && uv run mypy src/
```

Then GUI-eyeball in FreeCAD (constitution V) and record the signoff `.FCStd` size + SHA-256 in the
register entry.
