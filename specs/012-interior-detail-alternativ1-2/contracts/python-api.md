# Public API Contract: Interior Detail — Alternativ1 & 2

All additions are **additive** (PATCH 1.0.5 → 1.0.6). No existing public name removed or signature broken.

## New public names (exported from `storebro`)

```python
from storebro import (
    BerthParameters,
    GalleyParameters,
    HeadParameters,
    SalonParameters,
    BulkheadParameters,
    FurnitureParameters,
)
```

Added to `storebro.interior.__all__` and `storebro.__init__.__all__`, alphabetical.

## Modified signature

```python
build_interior(
    hull, deck, layout="Alternativ3", *,
    parameters_furniture: FurnitureParameters | None = None,
    document=None, name=None,
) -> Interior
```

`parameters_furniture=None` → defaults. Furniture is built only for `layout in {"Alternativ1","Alternativ2"}`; other layouts keep the existing boxy placeholders.

## Behavioral contract

| Guarantee | Assertion |
|---|---|
| Furniture on by default (Alt1/Alt2) | `build_interior(h, d, "Alternativ1")` → each compartment `is_furnished`, `body` is a `Part::Compound` |
| Type-keyed | forward_cabin→berth+cushion; galley→counter+recesses; head→toilet+sink; salon→seating+table; +bulkhead each |
| Galley manifold | galley counter `len(Solids) == 1` and `isValid()` after sink/stove cuts |
| Within envelope | every furniture piece BoundBox inside its compartment envelope |
| Gate | Alternativ3/4/5 → compartments remain single boxy `Part::Feature` (unfurnished), no error |
| Recess guard | sink/stove recess depth ≥ counter_thickness → `InteriorParameterError` before cut |
| Oversized guard | furniture larger than compartment → `InteriorParameterError` |
| Zero-count | zero cushions / galley cutouts disabled build the rest, no error |
| Reproducibility | identical layout + params → byte-identical exported geometry |
| Rollback | any furniture failure rolls back ALL added objects |
| B-rep idiomatic | furniture is `Part::Feature` (Part workbench), no raw mesh |
| Validation | each dataclass raises `InteriorParameterError` naming the field, before FreeCAD |
| STL unaffected | `export_stl` of a furnished model still yields a watertight mesh |

## Out of scope (other specs)

Alternativ3/4/5 furniture (spec 013). Transparency/material/color of furniture (spec 015). Contoured fittings, upholstery, faucet hardware (later).

## Versioning

`storebro.__version__ == "1.0.6"` == `pyproject.toml` version (guarded by the spec 010 version-consistency test).
