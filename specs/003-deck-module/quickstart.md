# Quickstart: storebro.deck

**Spec**: [spec.md](./spec.md) | **Contract**: [contracts/python-api.md](./contracts/python-api.md) | **Date**: 2026-05-17

A 5-minute walkthrough of the deck module's public API. Assumes FreeCAD 1.1+ on `PATH` and `freecad-storebro >= 0.3.0`.

---

## 1. Build a default Storebro deck on top of a default hull

```python
from storebro import build_hull, build_deck

hull = build_hull()
deck = build_deck(hull)

print(f"Built {deck.label} with {hull.label}")
print(f"  Deck plate thickness: {deck.deck_plate.thickness * 1000:.0f} mm")
print(f"  Cabin trunk:          {deck.cabin_trunk.length:.2f} m x {deck.cabin_trunk.width:.2f} m x {deck.cabin_trunk.height:.2f} m")
print(f"  Hardtop:              {deck.hardtop.length:.2f} m")
print(f"  Hardtop pillars:      {deck.hardtop_pillars.pillar_diameter * 1000:.0f} mm diameter (2x)")
print(f"  Railings:             {deck.railings.height * 100:.0f} cm tall")
print(f"  Built in:             {deck.build_duration_seconds:.2f} s")
```

Expected output (within ±1% on citation-grade dims):

```
Built Deck with Hull
  Deck plate thickness: 25 mm
  Cabin trunk:          4.50 m x 2.20 m x 1.20 m
  Hardtop:              3.50 m
  Hardtop pillars:      40 mm diameter (2x)
  Railings:             65 cm tall
  Built in:             ~ 12.0 s
```

---

## 2. Save the whole boat to .FCStd for FreeCAD GUI inspection

```python
from storebro import build_hull, build_deck, export_fcstd

hull = build_hull()
deck = build_deck(hull)

art = export_fcstd(hull.document, "/tmp/storebro_whole_boat.FCStd")
print(f"Saved {art.byte_count} bytes, SHA-256 {art.sha256[:12]}...")
```

In FreeCAD: open `/tmp/storebro_whole_boat.FCStd`, expand the document tree. You'll see the hull's Body plus the six deck Bodies (`Deck_DeckPlate`, `Deck_CabinTrunk`, ..., `Deck_Railings`). Each has named editable properties.

---

## 3. Custom deck dimensions

```python
from storebro import build_hull, build_deck, DeckParameters

hull = build_hull()

custom = DeckParameters(
    cabin_trunk_height=1.00,
    hardtop_height=0.15,
    hardtop_overhang_aft=0.60,
    railing_height=0.80,
    windshield_rake=35.0,
)
deck = build_deck(hull, custom)
print(f"Sportfish silhouette: cabin {deck.cabin_trunk.height:.2f} m, hardtop {deck.hardtop.height_above_cabin:.2f} m")
```

---

## 4. Variant studies on the same hull

```python
from storebro import build_hull, build_deck, DeckParameters

hull = build_hull()

for rake in (15.0, 25.0, 40.0):
    params = DeckParameters(windshield_rake=rake)
    deck = build_deck(hull, params, name=f"DeckRake{int(rake):02d}")
    print(f"rake={rake:.0f} deg -> {deck.label}")
```

---

## 5. Error handling

```python
from storebro import build_hull, build_deck, DeckParameters, DeckParameterError

hull = build_hull()

try:
    bad = DeckParameters(cabin_trunk_length=11.0)  # > hull.parameters.loa
    build_deck(hull, bad)
except DeckParameterError as e:
    print(f"refused: {e}")
```

Output:

```
refused: DeckParameterError: invalid cabin_trunk_length — cabin_trunk_length must be less than hull.parameters.loa
```

Construction failures mid-build roll back any partial Bodies before raising `DeckConstructionError` — see SC-008 and the `test_deck_construction_rollback` test for the exact contract.

---

## 6. Whole-boat pipeline

```python
from storebro import build_hull, build_deck, export_fcstd, export_step, export_stl

hull = build_hull()
deck = build_deck(hull)

step  = export_step(hull.body, "/tmp/boat.step")
stl   = export_stl(hull.body, "/tmp/boat.stl")
fcstd = export_fcstd(hull.document, "/tmp/boat.FCStd")

for art in (step, stl, fcstd):
    print(f"{art.format:6} {art.byte_count:>10} bytes  {art.sha256[:12]}...")
```

---

## What's NOT in this module

- Glazing / window cutouts (deferred to v1.1+ — clarify Q1)
- Stanchion + rail railings (deferred to v1.1+)
- Fly bridge / swim platform / anchor pulpit / transom door (deferred)
- Cross-document deck building (explicitly rejected per FR-016)
- Reading a deck back from .FCStd (write-only)

---

## Where to next

- **Verify your install**: `uv run pytest tests/unit/test_deck_*.py`
- **Run geometry tests**: `uv run pytest tests/geometry/test_deck_*.py -m requires_freecad`
- **Read the formal spec**: [spec.allium](./spec.allium)
- **Read the full contract**: [contracts/python-api.md](./contracts/python-api.md)
