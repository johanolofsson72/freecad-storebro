# Quickstart: storebro.hull

**Spec**: [spec.md](./spec.md) | **Contract**: [contracts/python-api.md](./contracts/python-api.md) | **Date**: 2026-05-17

A 5-minute walkthrough of the hull module's public API. All examples assume FreeCAD 1.1+ is on `PATH` and `freecad-storebro` is installed via `uv pip install freecad-storebro`.

---

## 1. Build a default Storebro hull

```python
from storebro import build_hull

hull = build_hull()  # defaults: Storebro Royal Cruiser 34, 1972 model

print(f"Built {hull.label}")
print(f"  LOA:      {hull.bbox[0]:.2f} m")
print(f"  Beam:     {hull.bbox[1]:.2f} m")
print(f"  Height:   {hull.bbox[2]:.2f} m")
print(f"  Volume:   {hull.volume:.2f} m^3")
print(f"  Built in: {hull.build_duration_seconds:.2f} s")
```

Expected output (within ±1% — see SC-001):

```
Built Hull
  LOA:      10.35 m
  Beam:      3.20 m
  Height:   ~ 1.90 m
  Volume:   ~ 16.5 m^3
  Built in: ~ 8.0 s
```

No FreeCAD GUI required — this runs headless. The hull lives in an in-memory FreeCAD document.

---

## 2. Save the result and open in FreeCAD GUI

```python
from storebro import build_hull

hull = build_hull()
hull.document.saveAs("/tmp/storebro_default.FCStd")
print(f"Saved to /tmp/storebro_default.FCStd — open in FreeCAD to inspect.")
```

Then in the terminal:

```bash
freecad /tmp/storebro_default.FCStd
```

In the FreeCAD GUI, expand the document tree to see `Hull` → `Sketch_Transom`, `Sketch_Aft`, `Sketch_Amidships`, `Sketch_Fwd`, `Sketch_Stem`, `AdditiveLoft`, `Mirrored`. Click `Hull` and inspect its **Properties** panel — you'll see `LOA`, `BeamMax`, `Draft`, `Freeboard`, `DeadriseAmidships`, `SheerHeightAft`, `SheerHeightFwd`, `TransomAngle` as editable fields. Change one — say `BeamMax` from 3.4 to 4.0 — and FreeCAD recomputes the hull immediately.

This is the constitutional "editable in FreeCAD GUI" guarantee (FR-007, principle III) at work.

---

## 3. Custom parameters

```python
from storebro import build_hull, HullParameters

# A wider, shorter, deeper hull
custom = HullParameters(
    loa=10.0,
    beam_max=3.8,
    draft=1.3,
    freeboard=1.1,
    deadrise_amidships=20.0,
    sheer_height_aft=1.0,
    sheer_height_fwd=1.6,
    transom_angle=10.0,
)
hull = build_hull(custom)

print(f"Custom hull: {hull.bbox[0]:.2f} × {hull.bbox[1]:.2f} × {hull.bbox[2]:.2f} m")
```

---

## 4. Compose with your own FreeCAD geometry

```python
import FreeCAD
from storebro import build_hull

doc = FreeCAD.newDocument("MyYacht")

hull = build_hull(document=doc, name="StarboardHull")

# Add your own geometry to the same document
my_mast = doc.addObject("Part::Cylinder", "Mast")
my_mast.Radius = 0.05
my_mast.Height = 8.0
my_mast.Placement = FreeCAD.Placement(
    FreeCAD.Vector(5.5, 0.0, 1.5), FreeCAD.Rotation()
)

doc.recompute()
doc.saveAs("/tmp/my_yacht.FCStd")
```

The hull module never mutates your document outside of adding its own Body — your mast, fittings, or other geometry are untouched.

---

## 5. Variant studies (multiple hulls in one document)

```python
import FreeCAD
from storebro import build_hull, HullParameters

doc = FreeCAD.newDocument("VariantStudy")

for beam in (3.0, 3.4, 3.8, 4.2):
    params = HullParameters(beam_max=beam)
    hull = build_hull(params, document=doc)
    print(f"Hull at beam={beam}m → label={hull.label}, LOA bbox={hull.bbox[0]:.2f}")

doc.saveAs("/tmp/beam_study.FCStd")
```

Output:

```
Hull at beam=3.0m → label=Hull,     LOA bbox=10.35
Hull at beam=3.4m → label=Hull001,  LOA bbox=10.35
Hull at beam=3.8m → label=Hull002,  LOA bbox=10.35
Hull at beam=4.2m → label=Hull003,  LOA bbox=10.35
```

FreeCAD's auto-numbering kicks in on every label collision — no manual name management.

---

## 6. Error handling

### Invalid parameter

```python
from storebro import HullParameters, HullParameterError

try:
    bad = HullParameters(loa=-5.0)
except HullParameterError as e:
    print(f"{e.parameter_name}={e.parameter_value} outside {e.valid_range}")
```

Output:

```
loa=-5.0 outside > 0
```

### Geometric impossibility

```python
from storebro import HullParameters, HullParameterError

try:
    bad = HullParameters(loa=3.0, beam_max=5.0)
except HullParameterError as e:
    print(e)
```

Output:

```
HullParameterError: invalid parameter combination — loa must exceed beam_max
```

### FreeCAD construction failure

```python
from storebro import build_hull, HullConstructionError

# Imagine a parameter combination that passes validation but breaks the loft
# (rare — most failures are caught by HullParameters validation)
try:
    hull = build_hull(some_pathological_params)
except HullConstructionError as e:
    print(f"FreeCAD failed: {type(e.underlying).__name__}: {e.underlying}")
    print(f"Parameters were: {e.parameters}")
```

### Unsupported FreeCAD version

```python
# Running under FreeCAD 0.20 (out of supported range 1.1+)
try:
    hull = build_hull()
except HullConstructionError as e:
    print(f"Got FreeCAD {e.detected_version}, need {e.supported_range}")
```

Output:

```
Got FreeCAD (0, 20), need 1.1 to <2.0
```

---

## What's NOT in this module

- **Deck, cabin, hardtop, railings** — see `storebro.deck` (spec 003, not yet built).
- **Interior cabins, galley, heads, salon** — see `storebro.interior` (spec 004, not yet built).
- **STEP / STL / BREP export, `.FCStd` byte-determinism** — see `storebro.export` (spec 002, not yet built).
- **CLI (`storebro build --layout 3 --out boat.FCStd`)** — see `storebro.cli` (spec 005, not yet built).
- **Logging / telemetry / progress events** — out of scope for v1.0 (clarify Q4).
- **Appendages (keel fin, skeg, rudder mounts, propeller tunnel)** — out of scope for v1.0 (FR-010); v1.1+ scoping TBD.

---

## Where to next

- **Verify your install**: `uv run pytest tests/unit/` (no FreeCAD needed)
- **Run geometry tests**: `uv run pytest -m requires_freecad` (FreeCAD on PATH required)
- **Read the formal spec**: [spec.allium](./spec.allium)
- **Read the full contract**: [contracts/python-api.md](./contracts/python-api.md)
