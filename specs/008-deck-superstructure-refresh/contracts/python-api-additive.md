# Contract: Python API — additive surface expansion

**Spec**: [spec.md](../spec.md) | **Data model**: [data-model.md](../data-model.md) | **Date**: 2026-05-18

Semver level: **PATCH** (v1.0.1 → v1.0.2). All v1.0.x public names + signatures preserved; net change is additive (5 new dataclasses + 1 composite + 1 new method + 1 new kwarg).

## Preserved surface (no changes)

These names exist in v1.0.0/v1.0.1 and continue to behave identically.

```python
from storebro.deck import (
    build_deck,             # function — signature stable (one new optional kwarg added below)
    Deck,                   # dataclass — field set stable + one additive field
    DeckPlate,              # dataclass — unchanged
    CabinTrunk,             # dataclass — field set stable; .body type is now PartDesign::Body
    Windshield,             # dataclass — field set stable; .body type is now PartDesign::Body
    Hardtop,                # dataclass — field set stable; .body type is now PartDesign::Body
    HardtopPillars,         # dataclass — field set stable; .body is now a Compound of PartDesign Bodies
    Railings,               # dataclass — field set stable; .body type is now PartDesign::Body
    DeckParameters,         # dataclass — 14-field shape unchanged; new method added below
    DeckParameterError,     # exception — unchanged
    DeckConstructionError,  # exception — unchanged
)
```

## New surface (additive)

```python
from storebro.deck import (
    CabinTrunkParameters,           # NEW — 7-field dataclass
    WindshieldParameters,           # NEW — 7-field dataclass
    HardtopParameters,              # NEW — 7-field dataclass
    PillarParameters,               # NEW — 5-field dataclass
    RailingParameters,              # NEW — 7-field dataclass
    DeckSuperstructureParameters,   # NEW — composite of the 5 above
    CabinTrunkBody,                 # NEW — typed wrapper for PartDesign cabin trunk
    WindshieldBody,                 # NEW — typed wrapper for PartDesign windshield
    HardtopBody,                    # NEW — typed wrapper for PartDesign hardtop
    PillarBody,                     # NEW — typed wrapper for a single PartDesign pillar
    RailingBody,                    # NEW — typed wrapper for one side's PartDesign railing
)
```

## Signature changes

### `build_deck` — one optional kwarg added

**Before** (v1.0.1):

```python
def build_deck(
    hull: Hull,
    parameters: DeckParameters | None = None,
    *,
    document: Any = None,
    name: str = "Deck",
) -> Deck: ...
```

**After** (v1.0.2):

```python
def build_deck(
    hull: Hull,
    parameters: DeckParameters | None = None,
    *,
    parameters_superstructure: DeckSuperstructureParameters | None = None,  # NEW
    document: Any = None,
    name: str = "Deck",
) -> Deck: ...
```

Contract:

- Existing callers (`build_deck(hull)`, `build_deck(hull, DeckParameters(...))`) behave identically.
- New callers pass `parameters_superstructure=DeckSuperstructureParameters(...)` for full per-component control.
- Passing both `parameters` and `parameters_superstructure` raises `DeckParameterError("parameters<>parameters_superstructure", None, "pass only one")`.
- When `parameters_superstructure` is None, the legacy path is used: if `parameters` is None, `DeckParameters()` defaults; otherwise the passed legacy dataclass is mapped via `parameters.to_superstructure_parameters()`.

### `DeckParameters` — one method added

```python
@dataclass(frozen=True)
class DeckParameters:
    # ... existing 14 fields unchanged ...

    def to_superstructure_parameters(self) -> DeckSuperstructureParameters:
        """Map this legacy DeckParameters onto the 6 sub-dataclasses.

        See specs/008-deck-superstructure-refresh/research.md §R4.
        """
        ...
```

Contract:

- Deterministic: same input → same output. No I/O, no time, no env.
- No exceptions raised — if a legacy field has no sensible mapping (e.g., `cabin_trunk_corner_radius`), it is silently dropped (the new dataclasses use rake angles instead).
- The resulting `DeckSuperstructureParameters` passes its own `__post_init__` validation (the legacy `DeckParameters` validator already covers the same constraints).

### `Deck` — one field added

**Before** (v1.0.1): 11 fields.

**After** (v1.0.2):

```python
@dataclass(frozen=True)
class Deck:
    # ... 11 existing fields unchanged ...
    parameters_superstructure: DeckSuperstructureParameters  # NEW — always populated
```

Contract:

- Existing callers using `deck.parameters` (legacy DeckParameters) still get the v1.0.1 dataclass populated.
- New `deck.parameters_superstructure` is populated regardless of which input form was passed; when legacy was passed, it holds the result of `parameters.to_superstructure_parameters()`.
- Adding a field to a frozen dataclass with a non-default value is technically a breaking change for keyword constructors. **However:** `Deck` is documented as a return type only — the v1.0.0/v1.0.1 docs and quickstart never construct `Deck(...)` directly; all examples obtain it via `build_deck()`. The public API contract is "consume what `build_deck` returns", not "construct Deck arbitrarily". The semver PATCH bump is correct under this contract. If a future caller is found to construct `Deck(...)` directly in third-party code, this would be flagged for MINOR bump in a separate spec — currently no such caller exists.
- The new field has no default to ensure the wrapper code always populates it (a default would mask bugs where a builder forgets to set the field).

## Body type contract (constitution III)

Every `.body` attribute on the sub-wrappers (`DeckPlate.body`, `CabinTrunk.body`, `Windshield.body`, `Hardtop.body`, `HardtopPillars.body`, `Railings.body`) MUST satisfy:

```python
body.TypeId == "PartDesign::Body"
body.Shape.Volume > 0
body.Shape.isValid()  # or body.Shape.ShapeType == "Solid"
```

**Exception**: `HardtopPillars.body` may be a `Part::Compound` containing multiple `PartDesign::Body` children (one per pillar). The compound itself is the legacy `HardtopPillars.body` field; the underlying pillars are individually PartDesign Bodies accessible via the new `PillarBody` list. This dual-shape is the same back-compat pattern used for v1.0.1 → v1.0.2.

Geometry tests assert this contract per-body (`test_deck_partdesign_feature_types.py`).

## Error contract (unchanged)

```python
DeckParameterError(parameter_name: str, parameter_value: float | None, valid_range: str)
DeckConstructionError(message: str, *, parameters=None, hull=None, underlying=None, detected_version=None, supported_range=None)
```

Both classes preserve their v1.0.0 attribute shapes. New `DeckParameterError` parameter names introduced by this spec follow the existing convention:

- Composite cross-field errors: `<a><>name<b>` (e.g., `windshield_top_z<>base_z`, `hardtop_curl_length<>length`).
- Single-field errors: just the field name (e.g., `windshield_top_width`, `pillar_diameter`).

## Test contract

The contract is verified by:

| Test | File | Asserts |
|---|---|---|
| Back-compat | `tests/unit/test_deck_back_compat.py` | `build_deck(hull)` works with no parameters → uses defaults. `build_deck(hull, DeckParameters())` works. `build_deck(hull, parameters_superstructure=DeckSuperstructureParameters())` works. Passing both raises `DeckParameterError`. |
| Body type | `tests/geometry/test_deck_partdesign_feature_types.py` | Every sub-body is `PartDesign::Body`. No `Part::Feature` raw solids. |
| Pillar seating | `tests/geometry/test_deck_pillar_seating.py` | For layouts 1..5, every pillar's BoundBox.ZMin ≥ deck_plate.BoundBox.ZMax - 1.0. |
| Silhouette | `tests/geometry/test_deck_silhouette.py` | For default parameters, every body's BoundBox matches R1 reference table ±1%. |
| Layout invariance | `tests/geometry/test_deck_layout_invariance.py` | Superstructure shape digests identical across layouts 1..5. |
| Reproducibility | `tests/geometry/test_deck_reproducibility.py` (extended) | Two consecutive builds produce identical SHA-256. |

## Migration guide for callers

**Nothing to migrate.** v1.0.1 code continues to work in v1.0.2.

If callers want the new per-component control:

```python
# Before (v1.0.1, still works in v1.0.2)
from storebro import build_hull, build_deck, DeckParameters
deck = build_deck(build_hull(), DeckParameters(railing_height=0.80))

# New (v1.0.2 only)
from storebro import build_hull, build_deck
from storebro.deck import (
    DeckSuperstructureParameters, RailingParameters
)

deck = build_deck(
    build_hull(),
    parameters_superstructure=DeckSuperstructureParameters(
        railings=RailingParameters(height_above_deck=800.0),
    ),
)
```

Both forms produce the same FCStd output for the same effective parameters.
