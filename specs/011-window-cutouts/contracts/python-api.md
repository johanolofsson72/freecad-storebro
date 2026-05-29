# Public API Contract: Window & Porthole Cutouts

All additions are **additive** (PATCH 1.0.4 → 1.0.5). No existing public name removed or signature broken.

## New public names (exported from `storebro`)

```python
from storebro import (
    PortholeParameters,
    HullGlazingParameters,
    CabinWindowParameters,
    WindshieldGlazingParameters,
    DeckGlazingParameters,
)
```

Added to `storebro.hull.__all__` (porthole/hull-glazing), `storebro.deck.__all__` (window/windshield/deck-glazing), and `storebro.__init__.__all__`, kept alphabetical.

## Modified signatures

```python
build_hull(parameters=None, *,
           parameters_glazing: HullGlazingParameters | None = None,
           document=None, name="Hull") -> Hull

build_deck(hull, parameters=None, *,
           parameters_superstructure=None, parameters_hardware=None,
           parameters_glazing: DeckGlazingParameters | None = None,
           document=None, name="Deck") -> Deck
```

`parameters_glazing=None` → defaults (glazing on by default). Independent of the existing `parameters` ⊕ `parameters_superstructure` mutual-exclusivity rule.

## Behavioral contract

| Guarantee | Assertion |
|---|---|
| Portholes on by default | `build_hull()` → `hull.portholes.count == 6` (3/side × 2) |
| Hull stays manifold | after porthole cuts, `len(hull.body.Shape.Solids) == 1` and `Shape.isValid()` |
| Portholes above waterline | every porthole center Z > waterline Z |
| Windows on by default | `build_deck()` → `deck.cabin_windows.count == 2` (1/side × 2) |
| Cabin trunk stays manifold | after window cuts, trunk solid count == 1 |
| Windshield framed + glazed | `deck.windshield.body` has a through-opening; `deck.windshield.glass_pane` is a distinct body |
| Windshield fallback | `WindshieldGlazingParameters(enabled=False)` → solid slab, `glass_pane is None` |
| Zero-count | zero portholes / zero windows / windshield disabled build the un-cut solid, no error |
| Recess guard | recess depth ≥ local solid half-extent → parameter error before cut |
| Manifold guard | a cut that yields non-manifold → `*ConstructionError`, rolled back |
| Reproducibility | identical params → byte-identical exported geometry |
| Rollback | any cut/pane failure rolls back ALL added objects |
| FreeCAD-idiomatic | every cut is a `PartDesign::Pocket`; glass pane is a PartDesign body; no raw mesh |
| Validation | each dataclass raises its module's parameter error naming the field, before FreeCAD |
| STL unaffected | `export_stl` of the default glazed model still produces a watertight mesh |

## Out of scope (spec 015)

Transparency, color, and material of the glass pane and the recess faces. Spec 011 produces geometry only; the glass-pane body exists so spec 015 can assign it a glass material.

## Versioning

`storebro.__version__ == "1.0.5"` == `pyproject.toml` version (guarded by the spec 010 version-consistency test).
