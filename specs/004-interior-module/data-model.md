# Data Model: Interior Module (Phase 1)

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md) | **Date**: 2026-05-17

Defines the data structures of `storebro.interior`: the YAML schema mirror (`Position3D`, `Dimensions3D`, `CompartmentSpec`, `LayoutSpec`), the runtime aggregate (`Interior`), the per-compartment wrapper (`Compartment`), and the two public exception classes.

---

## Entity overview

```
canonical layout name ("Alternativ3")  OR  filesystem path (/tmp/my.yaml)
        │
        ▼
   _load_and_validate_layout(source)
        │
        ├── YAML parse error            ──▶ InteriorParameterError
        ├── schema_version != 1         ──▶ InteriorParameterError
        ├── missing field / wrong type  ──▶ InteriorParameterError
        ├── duplicate compartment name  ──▶ InteriorParameterError
        ├── position.y != 0             ──▶ InteriorParameterError
        │
        ▼
   LayoutSpec (validated)
        │
        ▼
   build_interior(hull, deck, layout=..., document=..., name=...)
        │
        ├── _validate_hull              ──▶ InteriorParameterError
        ├── _validate_deck              ──▶ InteriorParameterError
        ├── document binding mismatch   ──▶ InteriorParameterError
        ├── envelope per compartment    ──▶ InteriorParameterError
        ├── pairwise overlap            ──▶ InteriorParameterError
        ├── FreeCAD version             ──▶ InteriorConstructionError
        │
        ├── _build_compartment ×N (with rollback tracker)
        │       │
        │       └── FreeCAD failure     ──▶ rollback + InteriorConstructionError
        │
        ▼
   Interior (returned, holds N Compartment wrappers + inputs)
```

---

## 1. `Position3D` (frozen dataclass — internal)

```python
@dataclass(frozen=True)
class Position3D:
    x: float  # m, aft from bow
    y: float  # m, MUST be 0 in v1.0 (clarify Q3)
    z: float  # m, compartment floor
```

Constructed from each compartment's YAML `position` sub-dict. Frozen, hashable.

---

## 2. `Dimensions3D` (frozen dataclass — internal)

```python
@dataclass(frozen=True)
class Dimensions3D:
    length: float  # m
    width: float   # m
    height: float  # m

    # Validated > 0 by the loader; no __post_init__ here because the
    # loader produces error messages citing the YAML source/compartment name.
```

---

## 3. `CompartmentSpec` (frozen dataclass — internal)

```python
@dataclass(frozen=True)
class CompartmentSpec:
    name: str
    compartment_type: str  # one of "forward_cabin", "galley", "head", "salon"
    position: Position3D
    dimensions: Dimensions3D
    description: str | None = None
```

One per compartment in the YAML's `compartments` list. Validated for type whitelist and centerline symmetry (`position.y == 0`).

---

## 4. `LayoutSpec` (frozen dataclass — internal, but `LayoutSpec.layout_name` and `LayoutSpec.source` are exposed via `Interior.layout`)

```python
@dataclass(frozen=True)
class LayoutSpec:
    schema_version: int           # must equal 1 in v1.0 (FR-021)
    layout_name: str              # canonical name or user-provided
    source: str                   # citation: docs/references/AlternativN.JPG or user path
    compartments: tuple[CompartmentSpec, ...]  # tuple for hashability
```

Tuple instead of list for hashability. Loaded by `_load_and_validate_layout`, never mutated after construction.

---

## 5. `Compartment` (frozen dataclass — public via `Interior.compartments`)

```python
@dataclass(frozen=True)
class Compartment:
    spec: CompartmentSpec
    body: Any  # FreeCAD.DocumentObject (Part::Feature)
```

Wrapper around the FreeCAD Body produced for one compartment. Identity is the body's name; value-equal on `spec` since two builds with the same spec produce structurally identical Bodies.

---

## 6. `Interior` (frozen dataclass — public, return aggregate)

```python
@dataclass(frozen=True)
class Interior:
    layout: LayoutSpec
    hull: Hull
    deck: Deck
    document: Any  # FreeCAD.Document
    label: str
    build_duration_seconds: float
    compartments: tuple[Compartment, ...]
```

### Contract guarantees

1. `document is hull.document` (FR-016) AND `document is deck.document` (FR-019).
2. `label` equals the resolved `name` kwarg or `f"Interior_{layout.layout_name}"` (FR-017).
3. `compartments` contains exactly `len(layout.compartments)` entries, one per spec.
4. `0 < build_duration_seconds < 60` for the default case on a developer laptop (SC-002).
5. Every `Compartment.body.Shape.Volume > 0` (a successful build never produces an empty compartment).

---

## 7. `InteriorParameterError(ValueError)` — public exception

Raised before any FreeCAD call when an input is invalid (YAML schema, envelope, overlap, hull/deck validity, document binding).

```python
class InteriorParameterError(ValueError):
    source: str                  # YAML file path or canonical fixture name
    compartment_name: str | None # if the error pertains to one compartment
    field: str | None            # e.g. "position", "dimensions.length", "schema_version"
    reason: str                  # human-readable

    def __init__(self, source: str, compartment_name: str | None,
                 field: str | None, reason: str): ...
```

### Message format

```
InteriorParameterError: in <source> — <reason>
```

When compartment / field are populated:

```
InteriorParameterError: in <source> — compartment '<compartment_name>': field '<field>' — <reason>
```

---

## 8. `InteriorConstructionError(RuntimeError)` — public exception

Raised when FreeCAD raises mid-build (after rollback completes), or when the FreeCAD version is unsupported.

```python
class InteriorConstructionError(RuntimeError):
    layout_name: str | None
    hull: Hull | None
    deck: Deck | None
    underlying: BaseException | None
    detected_version: tuple[int, int] | None
    supported_range: str | None

    def __init__(self, message: str, *,
                 layout_name: str | None = None,
                 hull: Hull | None = None,
                 deck: Deck | None = None,
                 underlying: BaseException | None = None,
                 detected_version: tuple[int, int] | None = None,
                 supported_range: str | None = None): ...
```

Mirrors spec 003's `DeckConstructionError` with the addition of `layout_name`.

---

## 9. Module-private types

Not public. Documented for plan completeness.

### `_RollbackTracker`

Internal `list[FreeCAD.DocumentObject]` accumulator, threaded through every `_build_compartment` call. The outer `try/except` in `build_interior` calls `_rollback` on this list when a FreeCAD-side failure surfaces.

### `_COMPARTMENT_TYPES`

Frozenset of permitted compartment types: `{"forward_cabin", "galley", "head", "salon"}`. Used by the schema validator (FR-008).

### `_CANONICAL_LAYOUT_NAMES`

Frozenset of canonical fixture names: `{"Alternativ1", "Alternativ2", "Alternativ3", "Alternativ4", "Alternativ5"}`. Used by the layout resolver.

---

## State transitions

The interior module is stateless from the caller's perspective: `build_interior` is a pure function over `(Hull, Deck, layout, document, name)` with the side effect of adding compartment Bodies to a FreeCAD document.

Internal state machine of one `build_interior` invocation:

```
START
  │
  ├── _ensure_freecad_supported ──▶ raise InteriorConstructionError (END)
  │
  ├── _load_and_validate_layout(source)
  │   ├── parse failure              ──▶ raise InteriorParameterError (END)
  │   ├── schema version mismatch    ──▶ raise InteriorParameterError (END)
  │   ├── schema field violation     ──▶ raise InteriorParameterError (END)
  │   └── return LayoutSpec
  │
  ├── _validate_hull(hull)           ──▶ raise InteriorParameterError (END)
  ├── _validate_deck(deck, hull)     ──▶ raise InteriorParameterError (END)
  ├── _resolve_document(hull, document) ──▶ raise InteriorParameterError (END)
  │
  ├── for each compartment in layout:
  │       _validate_compartment_in_envelope(spec, hull)
  │       ──▶ raise InteriorParameterError (END)
  │
  ├── _validate_no_overlaps(compartments)
  │       ──▶ raise InteriorParameterError (END)
  │
  ├── for each compartment in layout:
  │       _build_compartment(spec, target_doc, added)
  │       └── FreeCAD failure ──▶ _rollback(target_doc, added)
  │                              ──▶ raise InteriorConstructionError (END)
  │
  ├── target_doc.recompute()
  │       └── recompute failure ──▶ _rollback + raise InteriorConstructionError (END)
  │
  └── RETURN Interior(layout, hull, deck, document, label, duration, compartments)
```

This is a 7-state, 7-transition state machine from the caller's view — same triviality profile as spec 003 (will likely trigger the same `/tla` triviality gate).

---

## Cross-references

- Public API contract → [contracts/python-api.md](./contracts/python-api.md)
- Usage example → [quickstart.md](./quickstart.md)
- Formal invariants → [spec.allium](./spec.allium)
- Acceptance criteria → [spec.md](./spec.md) §Success Criteria
- Cross-module dependencies on hull + deck → [../001-hull-module/contracts/python-api.md](../001-hull-module/contracts/python-api.md) + [../003-deck-module/contracts/python-api.md](../003-deck-module/contracts/python-api.md)
