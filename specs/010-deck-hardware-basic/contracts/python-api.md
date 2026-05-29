# Public API Contract: Basic Deck Hardware

All additions are **additive** (PATCH 1.0.3 → 1.0.4). No existing public name is removed or has its signature broken.

## New public names (exported from `storebro`)

```python
from storebro import (
    RubrailParameters,
    BowPulpitParameters,
    LifelineParameters,
    AnchorLockerParameters,
    CleatParameters,
    DeckHardwareParameters,
)
```

Added to `storebro.deck.__all__` and `storebro.__init__.__all__`, kept alphabetically sorted (matches existing ordering convention).

## Modified signature

```python
build_deck(
    hull: Hull,
    parameters: DeckParameters | None = None,
    *,
    parameters_superstructure: DeckSuperstructureParameters | None = None,
    parameters_hardware: DeckHardwareParameters | None = None,   # NEW, keyword-only
    document: Any = None,
    name: str = "Deck",
) -> Deck
```

**Contract**:
- `parameters_hardware=None` → built with `DeckHardwareParameters()` defaults. Existing callers passing no new args receive hardware automatically.
- The returned `Deck` now also carries: `rubrail`, `bow_pulpit`, `lifelines`, `anchor_locker`, `cleats`, `parameters_hardware`.
- `parameters_hardware` is **independent** of the `parameters` ⊕ `parameters_superstructure` mutual-exclusivity rule (that guard is unchanged).

## Behavioral contract

| Guarantee | Assertion |
|---|---|
| Hardware on by default | `build_deck(build_hull())` returns a `Deck` with all 5 hardware wrappers non-null |
| Rubrail follows sheer | rubrail body top-Z at each station within ±1% of the sampled sheer Z (≤ `sheer_seating_tolerance_mm`) |
| Symmetry | `port` and `starboard` rubrail/cleat counts equal; bodies mirror across Y=0 |
| Cleat seating | each cleat body `BoundBox.ZMin >= deck_top_z_at_x - 1.0 mm` |
| Anchor locker placement | body `BoundBox` within deck footprint and `XMax <= cabin_trunk.forward_x` |
| Lifelines need posts | railing post_count_per_side == 0 → `lifelines.body` is an empty compound, `lifelines.line_count` semantics preserve `0` built |
| Zero counts | zero cleats / zero lifelines / zero pulpit stanchions build empty/omit without raising |
| Reproducibility | two builds with identical inputs → byte-identical exported geometry |
| Rollback | any FreeCAD failure mid-hardware-build rolls back ALL added bodies (deck + hardware) |
| FreeCAD-idiomatic | every hardware solid is a PartDesign feature (Pad/Loft), no raw mesh |
| Validation | each parameter dataclass raises `DeckParameterError` (subclass of `ValueError`) naming the field, BEFORE any FreeCAD call |
| Leaf imports | `deck.py` imports only `storebro.hull` + `storebro._freecad_check` (no new edges) |

## Error contract

`DeckParameterError(parameter_name, parameter_value, valid_range)` — unchanged class, raised for all hardware validation failures (per-field + cross-deck collisions). `isinstance(err, ValueError) is True`.

## Versioning

- `storebro.__version__ == "1.0.4"` (corrected from stale `"1.0.2"`).
- `pyproject.toml` `version == "1.0.4"`.
- Both MUST match (asserted by a test).
