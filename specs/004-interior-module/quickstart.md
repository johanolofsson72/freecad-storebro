# Quickstart: storebro.interior

**Spec**: [spec.md](./spec.md) | **Contract**: [contracts/python-api.md](./contracts/python-api.md) | **Date**: 2026-05-17

A 5-minute walkthrough of the interior module's public API. Assumes FreeCAD 1.1+ on `PATH` and `freecad-storebro >= 0.4.0`.

---

## 1. Build a complete Storebro boat

```python
from storebro import build_hull, build_deck, build_interior

hull = build_hull()
deck = build_deck(hull)
interior = build_interior(hull, deck)  # default layout = "Alternativ3"

print(f"Whole boat: {hull.label} + {deck.label} + {interior.label}")
print(f"  Layout: {interior.layout.layout_name}")
print(f"  Compartments: {len(interior.compartments)}")
for c in interior.compartments:
    pos = c.spec.position
    dim = c.spec.dimensions
    print(f"    {c.spec.name:15} ({c.spec.compartment_type:14}) "
          f"at ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f}) m, "
          f"{dim.length:.1f}x{dim.width:.1f}x{dim.height:.1f} m")
print(f"  Built in: {interior.build_duration_seconds:.2f} s")
```

---

## 2. Save the whole boat to .FCStd

```python
from storebro import build_hull, build_deck, build_interior, export_fcstd

hull = build_hull()
deck = build_deck(hull)
build_interior(hull, deck)

art = export_fcstd(hull.document, "/tmp/storebro_complete.FCStd")
print(f"Saved {art.byte_count} bytes, SHA-256 {art.sha256[:12]}...")
```

Open `/tmp/storebro_complete.FCStd` in FreeCAD: hull, six deck Bodies, and four compartment Bodies all appear in the tree.

---

## 3. Compare all five canonical layouts

```python
import FreeCAD
from storebro import build_hull, build_deck, build_interior, export_fcstd

for name in ["Alternativ1", "Alternativ2", "Alternativ3", "Alternativ4", "Alternativ5"]:
    doc = FreeCAD.newDocument(f"Boat_{name}")
    try:
        hull = build_hull(document=doc)
        deck = build_deck(hull)
        interior = build_interior(hull, deck, layout=name)
        export_fcstd(doc, f"/tmp/storebro_{name}.FCStd")
        print(f"{name}: {len(interior.compartments)} compartments")
    finally:
        FreeCAD.closeDocument(doc.Name)
```

---

## 4. Custom YAML layout

Create `/tmp/my_layout.yaml`:

```yaml
schema_version: 1
layout_name: MyLayout
source: hand-crafted for this example
compartments:
  - name: BigCabin
    type: forward_cabin
    position: { x: 0.5, y: 0, z: 0.6 }
    dimensions: { length: 6.0, width: 2.5, height: 1.6 }
    description: One huge cabin
  - name: AftSalon
    type: salon
    position: { x: 6.8, y: 0, z: 0.5 }
    dimensions: { length: 2.5, width: 2.6, height: 1.8 }
```

Then:

```python
from storebro import build_hull, build_deck, build_interior

hull = build_hull()
deck = build_deck(hull)
interior = build_interior(hull, deck, layout="/tmp/my_layout.yaml")
print(f"Custom: {interior.layout.layout_name}, {len(interior.compartments)} compartments")
```

---

## 5. Error handling

```python
from storebro import build_hull, build_deck, build_interior, InteriorParameterError

hull = build_hull()
deck = build_deck(hull)

try:
    build_interior(hull, deck, layout="Alternativ99")
except InteriorParameterError as e:
    print(f"refused: {e}")
```

Output:

```
refused: InteriorParameterError: in Alternativ99 — layout: must be one of the five canonical names or a path to a valid YAML file
```

Out-of-envelope and overlap errors raise similar typed messages naming the offending compartment and the violated constraint. Construction failures mid-build roll back any partial Bodies before raising `InteriorConstructionError` (SC-008).

---

## What's NOT in this module

- Engine room, aft cabin, dinette, wet locker — deferred to v1.1+
- Furniture (bunks, settees, galley fittings) — deferred
- Curved bulkheads following hull — deferred (boxes in v1.0)
- Asymmetric layouts (`position.y != 0`) — deferred
- Glazing / window cutouts — coordinated v1.1+ with spec 003

---

## Where to next

- **Verify your install**: `uv run pytest tests/unit/test_interior_*.py`
- **Run geometry tests**: `uv run pytest tests/geometry/test_interior_*.py -m requires_freecad`
- **Read the formal spec**: [spec.allium](./spec.allium)
- **Read the full contract**: [contracts/python-api.md](./contracts/python-api.md)
