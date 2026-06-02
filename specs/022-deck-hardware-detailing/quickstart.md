# Quickstart — Deck Hardware Detailing

## Build

```bash
# Default build — refined hardware is on by default.
uv run storebro build --layout 3 --out boat.FCStd

# Or in Python:
uv run python -c "
from storebro.hull import build_hull, HullParameters
from storebro.deck import build_deck
import FreeCAD as App
doc = App.newDocument('demo')
hull = build_hull(HullParameters(), document=doc)
deck = build_deck(hull, document=doc)
print('rubrail insert:', deck.rubrail.has_chrome_insert)
print('locker cavity:', deck.anchor_locker.has_cavity)
"
```

## What to eyeball in FreeCAD (constitution V)

Open the `.FCStd` and check, against `docs/references/Alternativ3.JPG`:

1. **Rubrail** — the sheer strip has a rounded (not flat) outboard face, with a
   thin bright chrome insert running its length.
2. **Bow pulpit** — the tube bends around radiused corners (no hard right-angle
   gaps); a small bead sits at each joint.
3. **Lifelines** — the wires sag gently between the railing posts.
4. **Cleats** — each cleat has a tapered base and curved horns (casting look).
5. **Anchor locker** — the box top is recessed (open locker) with a lid sitting
   over it.

## Verify

```bash
uv run pytest -m "not requires_freecad"        # unit (params, validation, roles)
PYTHONPATH=/Applications/FreeCAD.app/Contents/Resources/lib \
  uv run pytest -m requires_freecad -k hardware # geometry tier (manifold, fallback)
uv run ruff check . && uv run mypy src/
```

## Force the fallbacks (manual)

```python
# Sweep failure → straight tube. Set a pathological bend/ sag to exercise the
# manifold-or-fallback gate, or monkeypatch the sweep to raise; the body must
# still build valid.
BowPulpitParameters(bend_radius=0.0)   # degenerate → straight corners
LifelineParameters(sag_depth=0.0)      # flat → straight tube (spec 010 exact)
AnchorLockerParameters(cavity_depth=0.0)  # solid box, no lid (spec 010 exact)
```
