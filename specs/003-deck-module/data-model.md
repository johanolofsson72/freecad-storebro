# Data Model: Deck Module (Phase 1)

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md) | **Date**: 2026-05-17

Defines the data structures of `storebro.deck`: the public dataclass for inputs, the six sub-Body wrappers, the return aggregate, and the two public exception classes.

---

## Entity overview

```
DeckParameters (value object, frozen dataclass)
        │
        ▼
   build_deck(hull, parameters, *, document, name)
        │
        ├── validates hull             ──▶ DeckParameterError ("hull")
        ├── validates parameters       ──▶ DeckParameterError (per field)
        ├── validates cross-fields     ──▶ DeckParameterError (cross-field)
        ├── validates document binding ──▶ DeckParameterError ("document")
        ├── version-checks FreeCAD     ──▶ DeckConstructionError (version)
        │
        ├── builds DeckPlate, CabinTrunk, Windshield, Hardtop,
        │   HardtopPillars, Railings (each may add 1+ FreeCAD objects)
        │       │
        │       └── on FreeCAD failure ──▶ rollback added objects, raise
        │                                    DeckConstructionError
        │
        ▼
   Deck (returned, holds the 6 sub-Body wrappers + parameters + hull + label)
```

---

## 1. `DeckParameters` (frozen dataclass — value object)

Public, frozen `dataclasses.dataclass`. Hashable. Used as the single input contract for `build_deck`. All fields are SI: meters for lengths, degrees for angles.

### Fields

| Field | Type | Default | Unit | Valid range | Description |
|---|---|---|---|---|---|
| `deck_plate_thickness` | `float` | `0.025` | m | `> 0` | Vertical thickness of the deck plate slab |
| `cabin_trunk_length` | `float` | `4.50` | m | `> 0` and `< hull.loa` | Cabin trunk fore-aft length |
| `cabin_trunk_fwd_offset` | `float` | `2.00` | m | `>= 0` and `+ length <= hull.loa` | Distance from stem to cabin trunk forward face |
| `cabin_trunk_width` | `float` | `2.20` | m | `> 0` and `+ 2×walkway <= hull.beam_max` | Cabin trunk port-starboard width |
| `cabin_trunk_height` | `float` | `1.20` | m | `> 0` | Cabin trunk vertical height above the deck plate |
| `cabin_trunk_corner_radius` | `float` | `0.075` | m | `>= 0` | Rounded fillet radius at cabin trunk corners |
| `windshield_rake` | `float` | `25.0` | ° | `[0, 60]` | Windshield rake from vertical, aft direction positive |
| `hardtop_length` | `float` | `3.50` | m | `> 0` and `> overhangs` | Hardtop fore-aft length |
| `hardtop_height` | `float` | `0.10` | m | `>= 0` | Height of hardtop slab above cabin trunk top |
| `hardtop_overhang_fwd` | `float` | `0.20` | m | `>= 0` and `+ aft < length` | Hardtop overhang past cabin trunk forward face |
| `hardtop_overhang_aft` | `float` | `0.40` | m | `>= 0` and `+ fwd < length` | Hardtop overhang past cabin trunk aft face |
| `hardtop_pillar_diameter` | `float` | `0.04` | m | `> 0` | Diameter of each aft hardtop support pillar |
| `railing_height` | `float` | `0.65` | m | `> 0` | Height of perimeter rail above deck plate |
| `deck_side_walkway` | `float` | `0.40` | m | `> 0` | Perimeter walkway width between hull edge and cabin trunk side |

### Class-level constants

```python
REFERENCE_STOREBRO_DECK_RC34_1972: ClassVar[dict[str, float]] = {
    "deck_plate_thickness": 0.025,
    "cabin_trunk_length": 4.50,
    "cabin_trunk_fwd_offset": 2.00,
    "cabin_trunk_width": 2.20,
    "cabin_trunk_height": 1.20,
    "cabin_trunk_corner_radius": 0.075,
    "windshield_rake": 25.0,
    "hardtop_length": 3.50,
    "hardtop_height": 0.10,
    "hardtop_overhang_fwd": 0.20,
    "hardtop_overhang_aft": 0.40,
    "hardtop_pillar_diameter": 0.04,
    "railing_height": 0.65,
    "deck_side_walkway": 0.40,
}
```

This constant is read by `test_deck_default_dimensions.py` so the ±1% comparison cites a single source of truth.

### Validation

Per-field range checks happen in `__post_init__`. Cross-field checks involving the hull (e.g., `cabin_trunk_length < hull.loa`) cannot run in `__post_init__` because `DeckParameters` doesn't have access to the hull — those checks live in `build_deck` before any FreeCAD call. Both kinds of failure raise `DeckParameterError`.

### Identity & lifecycle

Frozen, hashable, value-equal. Lifecycle: built by the caller, passed to `build_deck`, discarded.

---

## 2. Sub-Body wrappers (`DeckPlate`, `CabinTrunk`, etc.)

Each of the six sub-Bodies has a small wrapper dataclass that holds the FreeCAD `Body` object plus a few measured properties. These are internal to the `Deck` aggregate (not separately publicly importable, but visible via `Deck` attributes).

```python
@dataclass(frozen=True)
class DeckPlate:
    body: FreeCAD.DocumentObject  # the Part::Feature / Body
    thickness: float              # echoes parameters.deck_plate_thickness

@dataclass(frozen=True)
class CabinTrunk:
    body: FreeCAD.DocumentObject
    length: float
    width: float
    height: float
    corner_radius: float

@dataclass(frozen=True)
class Windshield:
    body: FreeCAD.DocumentObject
    rake_degrees: float

@dataclass(frozen=True)
class Hardtop:
    body: FreeCAD.DocumentObject
    length: float
    height_above_cabin: float

@dataclass(frozen=True)
class HardtopPillars:
    body: FreeCAD.DocumentObject
    pillar_diameter: float

@dataclass(frozen=True)
class Railings:
    body: FreeCAD.DocumentObject
    height: float
```

Each wrapper's `body` field is the FreeCAD object actually present in the document. Frozen + value-equal on the underlying body identity.

---

## 3. `Deck` (return aggregate)

```python
@dataclass(frozen=True)
class Deck:
    parameters: DeckParameters
    hull: Hull
    document: FreeCAD.Document
    label: str
    build_duration_seconds: float

    deck_plate: DeckPlate
    cabin_trunk: CabinTrunk
    windshield: Windshield
    hardtop: Hardtop
    hardtop_pillars: HardtopPillars
    railings: Railings
```

### Contract guarantees

1. `document is hull.document` (FR-016).
2. `label` equals the resolved name (default `"Deck"`, with FreeCAD auto-numbering on collision).
3. All six sub-Body fields are non-`None` on a successful return.
4. `0 < build_duration_seconds < 45` for the default case (SC-002).

### Identity & lifecycle

Frozen, value-equal by underlying FreeCAD object identity. Lifecycle: returned by `build_deck`, lives as long as the document does.

---

## 4. `DeckParameterError(ValueError)` — public exception

Raised before any FreeCAD call when an input is invalid (parameter range, hull validity, document binding).

```python
class DeckParameterError(ValueError):
    parameter_name: str          # "cabin_trunk_length", "hull", "document", etc.
    parameter_value: float | None  # numeric value, or None for non-numeric / cross-field
    valid_range: str             # human-readable constraint

    def __init__(self, parameter_name: str,
                 parameter_value: float | None,
                 valid_range: str): ...
```

### Message format

```
DeckParameterError: <parameter_name> = <value> is outside the valid range <range>
```

For non-numeric or cross-field violations (`parameter_value is None`):

```
DeckParameterError: invalid <parameter_name> — <range>
```

### Used by

- `DeckParameters.__post_init__` (per-field ranges).
- `build_deck` before any FreeCAD call (cross-field, hull validity, document binding).

---

## 5. `DeckConstructionError(RuntimeError)` — public exception

Raised when FreeCAD raises mid-build (and rollback completes), or when the FreeCAD version is unsupported.

```python
class DeckConstructionError(RuntimeError):
    parameters: DeckParameters | None
    hull: Hull | None
    underlying: BaseException | None
    detected_version: tuple[int, int] | None
    supported_range: str | None

    def __init__(self, message: str, *,
                 parameters: DeckParameters | None = None,
                 hull: Hull | None = None,
                 underlying: BaseException | None = None,
                 detected_version: tuple[int, int] | None = None,
                 supported_range: str | None = None): ...
```

### Message format

```
DeckConstructionError: <message>
```

When wrapping a FreeCAD-side failure:

```
DeckConstructionError: build_deck failed during <ElementName> — <type(underlying)>: <message>
```

### Used by

- FreeCAD raises during one of the six `_build_<element>` helpers (the rollback runs first, then `DeckConstructionError` is raised).
- `_ensure_freecad_supported` rejects an out-of-range FreeCAD version.

---

## 6. Module-private types

Not public. Documented for plan completeness.

### `_RollbackTracker`

Internal `list[FreeCAD.DocumentObject]` accumulator threaded through the six `_build_<element>` helpers. Each helper appends its created objects immediately after `addObject` returns; the outer try/except in `build_deck` iterates the list in reverse on failure and calls `target_doc.removeObject(obj.Name)` per entry.

### `_SheerSample`

Internal NamedTuple `(x: float, y: float, z: float)` representing one of the five sampled sheer-line points (research.md R8). Built by `_sample_hull_sheer(hull)`, consumed by `_build_deck_plate`.

---

## State transitions

The deck module is stateless from the caller's perspective: `build_deck` is a pure function over `(Hull, DeckParameters, document, name)` with the side effect of adding six Bodies to a FreeCAD document.

Internal state machine of one `build_deck` invocation:

```
START
  │
  ├── version_check ──▶ raise DeckConstructionError (END)
  │
  ├── validate hull (None? empty shape?) ──▶ raise DeckParameterError (END)
  ├── validate parameters (per-field)    ──▶ raise DeckParameterError (END)
  ├── validate cross-fields              ──▶ raise DeckParameterError (END)
  ├── validate document binding          ──▶ raise DeckParameterError (END)
  │
  ├── sample hull sheer at 5 stations
  ├── build_deck_plate     → append objects to rollback tracker
  ├── build_cabin_trunk    → append objects to rollback tracker
  ├── build_windshield     → append objects to rollback tracker
  ├── build_hardtop        → append objects to rollback tracker
  ├── build_hardtop_pillars → append objects to rollback tracker
  ├── build_railings       → append objects to rollback tracker
  │       │
  │       └── if any helper raises ──▶ ROLLBACK (remove all added objs in reverse)
  │                                    ──▶ raise DeckConstructionError (END)
  │
  ├── document.recompute()
  │       │
  │       └── if recompute raises   ──▶ ROLLBACK ──▶ raise DeckConstructionError (END)
  │
  └── RETURN Deck(...)
```

This state machine is the model for the `/tla` step. With 8 states and ~10 transitions (counting rollback), spec 003 is RIGHT at the triviality-gate boundary — single Python actor, no concurrency, no async, but more transitions than spec 001/002. The `/tla` step decides whether formal verification adds value or whether the rollback discipline can rely on the dedicated `test_deck_construction_rollback.py` test.

---

## Cross-references

- Public API contract → [contracts/python-api.md](./contracts/python-api.md)
- Usage example → [quickstart.md](./quickstart.md)
- Formal invariants → [spec.allium](./spec.allium)
- Acceptance criteria → [spec.md](./spec.md) §Success Criteria
- Cross-module dependency on hull → [../001-hull-module/contracts/python-api.md](../001-hull-module/contracts/python-api.md)
