# Quickstart: Deck Superstructure Refresh

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-05-18

How a library consumer (scale modeler, FreeCAD scripter, or CLI user) gets a properly-shaped Storebro superstructure after spec 008 lands.

## Prerequisites

- Python 3.11+
- FreeCAD 1.1+ installed (Homebrew, AppImage, or .app)
- `uv` for dependency management
- `freecad-storebro` v1.0.2+ (this spec)

```bash
git clone https://github.com/johanolofsson72/freecad-storebro.git
cd freecad-storebro
uv sync
```

## Option A — CLI (default parameters)

```bash
uv run storebro build --layout 3 --out /tmp/storebro_rc34.FCStd
open /tmp/storebro_rc34.FCStd     # macOS — opens in FreeCAD GUI
```

You should see, in side view:

- A near-flat sheer hull with blunt stem (from spec 007).
- A trapezoidal cabin trunk forward of amidships (forward face narrower than aft, both rake-tilted).
- A forward-curving windshield rising from the cabin trunk top.
- A hardtop slab spanning from the windshield top aft, with a downward curl on its leading edge and a slight aft taper.
- Four pillars (2 port, 2 starboard) holding the hardtop, seated flush on the deck plate top — **not** piercing into the hull cavity.
- A calf-height railing around the cockpit perimeter with 6 posts per side.

Open the Model Tree (`View → Tree view`). Every superstructure element should appear as an editable `PartDesign::Body` with named sketches and features. No raw `Part::Compound` or `Mesh::Feature` nodes.

## Option B — Python API (default parameters)

```python
from storebro import build_hull, build_deck
from storebro.export import export_fcstd

hull = build_hull()
deck = build_deck(hull)               # uses default DeckParameters
export_fcstd(hull.document, "/tmp/storebro_rc34.FCStd")
```

Identical output to Option A.

## Option C — Python API (custom per-component parameters)

```python
from storebro import build_hull, build_deck
from storebro.deck import (
    DeckSuperstructureParameters,
    CabinTrunkParameters,
    WindshieldParameters,
    HardtopParameters,
    PillarParameters,
    RailingParameters,
)
from storebro.export import export_fcstd

# Build with a taller cabin trunk and 3 pillars per side.
params = DeckSuperstructureParameters(
    cabin_trunk=CabinTrunkParameters(height=1300.0),
    pillars=PillarParameters(count_per_side=3, forward_x=5400.0, aft_x=8200.0),
)

hull = build_hull()
deck = build_deck(hull, parameters_superstructure=params)
export_fcstd(hull.document, "/tmp/storebro_custom.FCStd")
```

## Option D — Python API (legacy DeckParameters, backward-compatible)

```python
from storebro import build_hull, build_deck, DeckParameters
from storebro.export import export_fcstd

hull = build_hull()
deck = build_deck(hull, DeckParameters(railing_height=0.80))  # 14-field legacy form
export_fcstd(hull.document, "/tmp/storebro_legacy.FCStd")
```

This is the v1.0.1 form and continues to work in v1.0.2 unchanged. The legacy `DeckParameters` is silently translated to a `DeckSuperstructureParameters` internally via `to_superstructure_parameters()`.

## Verifying the fix manually

1. Build the default model: `uv run storebro build --layout 3 --out /tmp/check.FCStd`.
2. Open `/tmp/check.FCStd` in FreeCAD.
3. Switch to side view (`View → Standard views → Right`).
4. Zoom to the hardtop area.
5. Confirm: every pillar starts at the deck plate top edge and ends at the hardtop underside. **No pillar pokes through the sheer line into the hull cavity.**
6. Open `docs/references/Alternativ3.JPG` next to FreeCAD.
7. Overlay (mentally or with a screenshot tool) the model side view on the reference photo. Principal silhouette features (cabin trunk shape, windshield rake, hardtop overhang + curl, railing height) should match within visual inspection.

## Verifying programmatically (developers)

```bash
# Run all 344 existing tests + ~25 new tests
uv run pytest

# Only the spec 008 acceptance tests
uv run pytest tests/geometry/test_deck_pillar_seating.py \
              tests/geometry/test_deck_silhouette.py \
              tests/geometry/test_deck_partdesign_feature_types.py \
              tests/geometry/test_deck_layout_invariance.py \
              tests/geometry/test_deck_reproducibility.py

# Lint + types
uv run ruff check .
uv run mypy src/
```

All should pass.

## When something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| `DeckParameterError: pillar_forward_x<>cabin_trunk_length` | Pillars positioned inside the cabin trunk footprint | Increase `pillars.forward_x` to ≥ `cabin_trunk.length` |
| `DeckParameterError: railing_height<>hardtop_height` | Railing taller than hardtop clearance | Lower `railings.height_above_deck` to less than `hardtop.height_above_deck` |
| `DeckParameterError: windshield_curvature_radius` | Windshield rake delta too tight for the height — spline would self-intersect | Widen rake delta or increase windshield height |
| `DeckConstructionError: unsupported FreeCAD version` | FreeCAD older than 1.1 | Install FreeCAD 1.1+ |
| Pillars appear to pierce hull in GUI | Stale FCStd from v1.0.1 still cached | Re-run `storebro build`; clear `~/Library/Application Support/FreeCAD/Mod/*Cache*` if needed |
| `mypy --strict` complains about `parameters_superstructure: DeckSuperstructureParameters | None` | mypy version older than 1.5 | Upgrade mypy via `uv sync --upgrade-package mypy` |
