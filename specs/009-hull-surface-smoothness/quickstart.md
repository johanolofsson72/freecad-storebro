# Quickstart: Hull surface smoothness (spec 009)

How to exercise the spec 009 changes once they ship in v1.0.3.

## Build the default smooth hull (CLI)

The CLI surface is unchanged; the new defaults take effect automatically.

```bash
uv run storebro build --layout 3 --out boat.FCStd
```

Open `boat.FCStd` in FreeCAD 1.1.1+. The hull surface reads as a smooth B-spline curve with no visible polygon facets between adjacent stations. The amidships cross-section shows a quarter-circle bilge transition between bottom and topside.

## Build a custom hull (Python API)

```python
from storebro.hull import HullParameters, build_hull

# Default v1.0.3 — 9 stations, B-spline loft, 200 mm bilge arc, zero-forefoot stem.
params_default = HullParameters()
hull_default = build_hull(params_default)

# Higher station count for tighter cross-sections.
params_high = HullParameters(station_count=15)
hull_high = build_hull(params_high)

# Tighter bilge for a more chiselled cross-section.
params_tight_bilge = HullParameters(bilge_radius=0.10)
hull_tight = build_hull(params_tight_bilge)

# Legacy 5-station + Ruled=True + pentagon stem (escape hatch).
params_legacy = HullParameters(station_count=5)
hull_legacy = build_hull(params_legacy)

# Sharp-chine cross-section (no bilge arc).
params_chine = HullParameters(bilge_radius=0.0)
hull_chine = build_hull(params_chine)
```

## Validation errors

```python
from storebro.hull import HullParameters, HullParameterError

# station_count out of range.
try:
    HullParameters(station_count=50)
except HullParameterError as e:
    print(e)  # "station_count out of range: got 50, valid [3, 21]"

# bilge_radius exceeds geometric maximum.
try:
    HullParameters(bilge_radius=5.0)
except HullParameterError as e:
    print(e)  # "bilge_radius out of range: got 5.0, valid [0, 1.10]"

# B-spline overshoot detected at build time.
from storebro.hull import build_hull, HullConstructionError

extreme_params = HullParameters(station_count=21, bilge_radius=1.0)
try:
    build_hull(extreme_params)
except HullConstructionError as e:
    print(e)
    # "B-spline loft overshoots hull height envelope at X=2070mm by 12.4mm —
    #  increase station_count, reduce bilge_radius, or set station_count < 8
    #  for legacy piecewise-linear behavior"
```

## Reproducibility check

```python
import hashlib
from pathlib import Path
from storebro.hull import HullParameters, build_hull
from storebro.export import write_step

params = HullParameters()

# Build + export twice.
hull_1 = build_hull(params)
write_step(hull_1, Path("hull_1.step"))
hash_1 = hashlib.sha256(Path("hull_1.step").read_bytes()).hexdigest()

hull_2 = build_hull(params)
write_step(hull_2, Path("hull_2.step"))
hash_2 = hashlib.sha256(Path("hull_2.step").read_bytes()).hexdigest()

assert hash_1 == hash_2, "STEP reproducibility broken!"
```

## Pillar seating regression check

The deck/superstructure pipeline continues to work with the smoother hull — pillars seat on the actual deck top Z via `deck._resolve_deck_top_z_at()`.

```python
from storebro.hull import HullParameters, build_hull
from storebro.deck import build_deck_superstructure, _resolve_deck_top_z_at

hull_params = HullParameters()
hull = build_hull(hull_params)

bundle = build_deck_superstructure(layout=3, hull=hull)

for pillar in bundle.pillars:
    deck_top_z = _resolve_deck_top_z_at(bundle.deck_plate, pillar.x_position_mm)
    delta = abs(pillar.lower_endpoint_z_mm - deck_top_z)
    assert delta <= 1.0, f"Pillar seating regression: {delta} mm > 1.0 mm tolerance"
```

## Visual signoff workflow

After making changes to `src/storebro/hull.py`:

```bash
# 1. Run the test suite — must be green before opening the GUI.
uv run pytest
uv run ruff check .
uv run mypy src/

# 2. Build the signoff fixture.
uv run storebro build --layout 3 --out tests/fixtures/signoff/storebro_v1_0_3_signoff.FCStd

# 3. Open in FreeCAD 1.1.1 GUI on macOS Darwin arm64.
open tests/fixtures/signoff/storebro_v1_0_3_signoff.FCStd

# 4. Compare against docs/references/Alternativ3.JPG side-by-side. Verify:
#    - smooth-curved hull surface (no visible polygon facets between stations)
#    - quarter-circle bilge transition at amidships cross-section
#    - blunt stem with zero forefoot
#    - near-vertical transom + ~6 deg stem rake (preserved from spec 007)
#    - pillars seated cleanly on the deck plate (no clipping into hull)

# 5. Record the signoff SHA-256 + visual-verified-by line in the spec 009
#    closure note in specs/INDEX.md.
shasum -a 256 tests/fixtures/signoff/storebro_v1_0_3_signoff.FCStd
```

## What changed at a glance

| Thing | v1.0.2 | v1.0.3 |
|---|---|---|
| Default station count | 5 (hard-coded) | 9 (parameter, default) |
| Loft type at default | `Ruled=True` (piecewise-linear) | `Ruled=False` (B-spline) |
| Stem topology at default | 5-vertex pentagon w/ 80 mm forefoot | degenerate vertex (zero forefoot) |
| Non-stem cross-section at default | sharp-chine quadrilateral | pentagon-with-arc (200 mm bilge) |
| `HullParameters.station_count` | (does not exist) | `int`, default 9, range [3, 21] |
| `HullParameters.bilge_radius` | (does not exist) | `float`, default 0.20, range [0, min(beam/2, draft)] |
| CLI flags | (no station/bilge flags) | (no station/bilge flags — clarification 3) |
| FCStd byte equivalence | n/a (within-document deterministic) | n/a (within-document deterministic, cross-invocation still deferred) |
| STEP/STL/BREP SHA-256 | deterministic across runs | deterministic across runs (+ across CI matrix) |
