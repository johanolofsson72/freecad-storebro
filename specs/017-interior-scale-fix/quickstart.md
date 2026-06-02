# Quickstart: Verifying the Interior Scale Fix

No public API change — existing callers are unaffected. This recipe verifies the corrected scale.

## Build an interior and check the scale (requires FreeCAD 1.1+)

```python
from storebro import build_hull, build_deck, build_interior

hull = build_hull()
deck = build_deck(hull)
interior = build_interior(hull, deck, layout="Alternativ1")

cabin = next(c for c in interior.compartments if c.spec.compartment_type == "forward_cabin")
bb = cabin.body.Shape.BoundBox
print(bb.XLength)  # ~2400.0 (mm) for a 2.4 m cabin  — was ~2.4 before the fix

# Interior nests inside the hull (shared mm coordinate system):
hull_bb = hull.body.Shape.BoundBox
assert hull_bb.XMin <= bb.XMin and bb.XMax <= hull_bb.XMax
```

## CLI (unchanged surface)

```bash
uv run storebro build --layout 1 --out boat.FCStd
# Open boat.FCStd in FreeCAD — the interior now sits inside the hull at true scale.
```

## Verification gates

```bash
uv run pytest -m "not requires_freecad"   # unit tier (no FreeCAD): validation/overlap/manifold logic
uv run pytest -m requires_freecad         # geometry tier (FreeCAD host): scale + containment + envelope
uv run ruff check .
uv run mypy src/
```

On a FreeCAD host, also eyeball the generated `.FCStd` in the GUI (constitution V): the compartments and furniture should sit inside the hull at realistic real-world sizes.
