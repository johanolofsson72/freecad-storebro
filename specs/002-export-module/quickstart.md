# Quickstart: storebro.export

**Spec**: [spec.md](./spec.md) | **Contract**: [contracts/python-api.md](./contracts/python-api.md) | **Date**: 2026-05-17

A 5-minute walkthrough of the export module's public API. Assumes FreeCAD 1.1+ on `PATH` and `freecad-storebro >= 0.2.0` installed.

---

## 1. Build a hull and export to all four formats

```python
from storebro import build_hull, export_fcstd, export_step, export_stl, export_brep

hull = build_hull()

step_art  = export_step(hull.body,        "/tmp/storebro.step")
stl_art   = export_stl(hull.body,         "/tmp/storebro.stl")
brep_art  = export_brep(hull.body,        "/tmp/storebro.brep")
fcstd_art = export_fcstd(hull.document,   "/tmp/storebro.FCStd")

for art in (step_art, stl_art, brep_art, fcstd_art):
    print(f"{art.format:6}  {art.byte_count:>10} bytes  {art.sha256[:12]}…  ({art.build_duration_seconds:.2f}s)")
```

Expected (numbers approximate, hashes pinned per FreeCAD version):

```
step       127344 bytes  3f4a1e9b2c8d…  (1.42s)
stl        382016 bytes  9b2c8d3f4a1e…  (3.71s)
brep        58122 bytes  1e9b2c8d3f4a…  (0.91s)
fcstd      192884 bytes  4a1e9b2c8d3f…  (1.05s)
```

---

## 2. Determinism check (the constitutional principle II invariant)

```python
from storebro import build_hull, export_step

hull = build_hull()
a1 = export_step(hull.body, "/tmp/run_a.step")
a2 = export_step(hull.body, "/tmp/run_b.step")

assert a1.sha256 == a2.sha256, "byte determinism broken — FILE A BUG"
print(f"SHA-256 {a1.sha256[:12]}… matches across both runs.")
```

If the assertion fails the project's most-important invariant has been violated. Bisect FreeCAD versions and the export module to find the regression.

---

## 3. Custom STL tessellation

```python
from storebro import build_hull, export_stl

hull = build_hull()

# Default 1mm chord deviation
default_art = export_stl(hull.body, "/tmp/default.stl")

# Tighter — for high-quality render or fine 3D-print detail
fine_art = export_stl(hull.body, "/tmp/fine.stl", tessellation_tolerance=0.0001)

# Looser — for quick previews
coarse_art = export_stl(hull.body, "/tmp/coarse.stl", tessellation_tolerance=0.005)

print(f"default: {default_art.byte_count} bytes")
print(f"fine:    {fine_art.byte_count} bytes   ({fine_art.byte_count / default_art.byte_count:.1f}x default)")
print(f"coarse:  {coarse_art.byte_count} bytes")
```

Each tolerance value produces a different STL — byte-identical for any two runs at the same tolerance.

---

## 4. Error handling

### Invalid path

```python
from storebro import build_hull, export_step, ExportInputError

hull = build_hull()
try:
    export_step(hull.body, "/does/not/exist/boat.step")
except ExportInputError as e:
    print(f"{e.field}: {e.reason}")
```

Output:

```
target_path: parent directory does not exist (got: /does/not/exist)
```

### Refuse to overwrite

```python
from storebro import build_hull, export_step, ExportInputError
from pathlib import Path

hull = build_hull()
out = Path("/tmp/precious.step")
export_step(hull.body, out)  # first write OK

try:
    export_step(hull.body, out, overwrite=False)
except ExportInputError as e:
    print(f"refused: {e.reason}")
```

Output:

```
refused: target exists and overwrite=False (got: /tmp/precious.step)
```

### FreeCAD-side write failure

```python
from storebro import build_hull, export_stl, ExportWriteError

hull = build_hull()
# Force a failure by passing a tessellation tolerance too tight for FreeCAD's mesher
try:
    export_stl(hull.body, "/tmp/will_fail.stl", tessellation_tolerance=1e-12)
except ExportWriteError as e:
    print(f"failed: format={e.format}, target={e.target_path}")
    print(f"  underlying: {e.underlying_message}")
```

---

## 5. Round-trip through `.FCStd`

```python
import FreeCAD
from storebro import build_hull, export_fcstd

hull = build_hull()
export_fcstd(hull.document, "/tmp/round_trip.FCStd")

# Later, in a fresh session:
doc = FreeCAD.openDocument("/tmp/round_trip.FCStd")
print(f"Reopened document has {len(doc.Objects)} objects")
print(f"Body Label: {doc.Objects[0].Label}")
```

Output:

```
Reopened document has 4 objects   # Hull body + loft + mirror + fusion
Body Label: Hull
```

The reopened document is fully parametric — open it in the FreeCAD GUI and edit `Hull.BeamMax` to see the geometry recompute.

---

## 6. Sharing hash baselines with collaborators

Every team member running the same FreeCAD version on the same source hull gets the same SHA-256. Store the expected hashes in `tests/geometry/fixtures/expected_hashes.toml` and your CI will alert anyone whose change breaks the constitutional principle II invariant.

```bash
# Initial baseline generation (run once per FreeCAD version):
uv run python tests/geometry/fixtures/refresh_hashes.py

# CI/local regression test:
uv run pytest tests/geometry/test_export_*.py
```

---

## What's NOT in this module

- **Reading exported files** (`import_step`, etc.) — round-trip is write-only in v1.0.
- **DXF / IGES / glTF / OBJ formats** — deferred to v1.1+.
- **Compressed output** (gzipped STL, `.FCStd.gz`) — deferred to v1.1+.
- **Windows support** — Ubuntu + macOS only in v1.0.
- **Multi-document export to one file** — each call handles one source object.
- **Logging / telemetry / progress events** — none in v1.0.

---

## Where to next

- **Run unit tests**: `uv run pytest tests/unit/test_export_*.py` (no FreeCAD needed)
- **Run geometry + hash tests**: `uv run pytest -m requires_freecad tests/geometry/test_export_*.py`
- **Read the formal spec**: [spec.allium](./spec.allium)
- **Read the full contract**: [contracts/python-api.md](./contracts/python-api.md)
