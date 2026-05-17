# Contract: `storebro.deck` Public Python API

**Spec**: [../spec.md](../spec.md) | **Plan**: [../plan.md](../plan.md) | **Data model**: [../data-model.md](../data-model.md) | **Date**: 2026-05-17

Public API contract for the deck module. Governed by semantic versioning (constitution VI): breaking changes require a MAJOR bump and a documented migration path.

---

## Module path

```python
import storebro.deck
# or, re-exported from the package root:
from storebro import build_deck, DeckParameters, Deck, DeckParameterError, DeckConstructionError
```

`storebro.deck.__all__`:

```python
__all__ = [
    "Deck",
    "DeckConstructionError",
    "DeckParameterError",
    "DeckParameters",
    "build_deck",
]
```

The six sub-Body wrapper dataclasses (`DeckPlate`, `CabinTrunk`, `Windshield`, `Hardtop`, `HardtopPillars`, `Railings`) are visible via `Deck.<field>` attribute access but are NOT separately importable from `storebro.deck` in v0.3.0 — that's a deliberate scope restriction to keep the public surface tight. Promote them to direct imports in a MINOR bump if user demand emerges.

---

## Function: `build_deck`

```python
def build_deck(
    hull: "storebro.Hull",
    parameters: DeckParameters | None = None,
    *,
    document: "FreeCAD.Document | None" = None,
    name: str = "Deck",
) -> Deck:
    """Build the parametric Storebro deck superstructure on a hull.

    Args:
        hull: A Hull returned by storebro.hull.build_hull. Must have a non-empty
            Shape (i.e. the hull's source document must have been recomputed
            after creation).
        parameters: Deck dimensional parameters. None → use DeckParameters()
            defaults (RC34 1972 estimate-grade values per
            research.md R1).
        document: Target FreeCAD document. None → use hull.document. Must equal
            hull.document if non-None — cross-document deck building is rejected
            with DeckParameterError (FR-016).
        name: Base label for the Deck aggregate. Defaults to "Deck". The six
            sub-Bodies are labeled "{name}_DeckPlate", "{name}_CabinTrunk",
            "{name}_Windshield", "{name}_Hardtop", "{name}_HardtopPillars",
            "{name}_Railings". FreeCAD auto-numbering applies on collision.

    Returns:
        Deck: an aggregate with the six sub-Body wrappers, the inputs, and the
        build duration.

    Raises:
        DeckParameterError: Invalid parameters, hull-incompatibility,
            null hull, document mismatch, etc. Raised BEFORE any FreeCAD call.
        DeckConstructionError: Unsupported FreeCAD version, or FreeCAD-side
            construction failure (after rollback completes — the document is
            restored to its pre-call state).

    Example:
        >>> from storebro import build_hull, build_deck
        >>> hull = build_hull()
        >>> deck = build_deck(hull)
        >>> deck.cabin_trunk.length
        4.5
        >>> deck.document is hull.document
        True
    """
```

### Contract guarantees

1. **Pre-FreeCAD validation**. No FreeCAD call happens before parameters are validated. Invalid inputs raise `DeckParameterError` deterministically.
2. **Document binding**. The returned `Deck.document is hull.document`. Caller-supplied `document` MUST equal `hull.document` or `DeckParameterError` is raised.
3. **Six Bodies, six labels**. The returned `Deck` has six populated sub-Body wrappers and six Bodies in the document with the documented labels.
4. **Symmetry**. Every sub-Body is symmetric about the X-Z plane (FR-009).
5. **Sheer alignment**. The deck plate's underside Z at the five sampled stations matches the hull's sheer Z within 1 µm (SC-009).
6. **Rollback on failure**. FreeCAD-side failures roll back ALL Bodies added by this call. The document state after the failed call equals the document state before the call (SC-008).
7. **Structural determinism**. Two calls with identical `(hull, parameters)` produce sub-Bodies with identical volumes, bbox dimensions, and topology counts to within `1e-9` relative tolerance (SC-003).
8. **No logging**. v0.3.0 produces no log output, no metrics, no progress events.

### Side effects

- Adds 6+ `Part::Feature` (or `PartDesign::Body`) objects to `hull.document`.
- May add intermediate sketches, mirroring features, etc. — all are children of one of the six sub-Bodies and visible in the FreeCAD document tree.
- Calls `document.recompute()` once before return.

---

## Class: `DeckParameters`

```python
@dataclass(frozen=True)
class DeckParameters:
    deck_plate_thickness: float = 0.025       # m
    cabin_trunk_length: float = 4.50          # m
    cabin_trunk_fwd_offset: float = 2.00      # m
    cabin_trunk_width: float = 2.20           # m
    cabin_trunk_height: float = 1.20          # m
    cabin_trunk_corner_radius: float = 0.075  # m
    windshield_rake: float = 25.0             # deg
    hardtop_length: float = 3.50              # m
    hardtop_height: float = 0.10              # m
    hardtop_overhang_fwd: float = 0.20        # m
    hardtop_overhang_aft: float = 0.40        # m
    hardtop_pillar_diameter: float = 0.04     # m
    railing_height: float = 0.65              # m
    deck_side_walkway: float = 0.40           # m

    REFERENCE_STOREBRO_DECK_RC34_1972: ClassVar[dict[str, float]] = {...}
```

### Contract guarantees

1. **Frozen**, hashable, value-equal.
2. **Validated at construction**. `__post_init__` checks per-field ranges and intra-deck cross-field constraints (e.g., `hardtop_overhang_fwd + hardtop_overhang_aft < hardtop_length`). Cross-hull constraints are checked by `build_deck`, not by `DeckParameters` (because `DeckParameters` doesn't see the hull).
3. **Defaults are reference-fidelity**. Default-field values produce a deck whose cabin trunk length, hardtop length, and railing height fall within ±1% of the citation-grade RC34 1972 reference (SC-001).

---

## Class: `Deck`

```python
@dataclass(frozen=True)
class Deck:
    parameters: DeckParameters
    hull: "storebro.Hull"
    document: "FreeCAD.Document"
    label: str
    build_duration_seconds: float
    deck_plate: DeckPlate
    cabin_trunk: CabinTrunk
    windshield: Windshield
    hardtop: Hardtop
    hardtop_pillars: HardtopPillars
    railings: Railings
```

Frozen, value-equal. The six sub-Body wrapper types are internal but accessible.

---

## Exceptions

### `DeckParameterError(ValueError)`

Same shape as spec 001's `HullParameterError`. Carries `parameter_name`, `parameter_value`, `valid_range`. Raised before any FreeCAD call.

### `DeckConstructionError(RuntimeError)`

Same shape as spec 001's `HullConstructionError`, with the addition of a `hull` attribute (for diagnosis). Carries `parameters`, `hull`, `underlying`, `detected_version`, `supported_range`. Raised after rollback completes.

Both exception classes are **independent** of spec 001's classes per clarify Q5 — no shared base class, no inheritance bridge.

---

## Versioning

- **PATCH**: bug fixes, internal refactor, default-value refinement within ±1% of the citation-grade reference, FreeCAD-version-range expansion.
- **MINOR**: new optional kwargs to `build_deck`, new optional fields on `DeckParameters` (with defaults), new read-only attributes on `Deck` / sub-Body wrappers, promoting sub-Body wrappers to direct imports.
- **MAJOR**: removing a public name, changing a default value beyond ±1%, changing exception class hierarchies, changing function signatures non-additively, dropping a previously-supported FreeCAD version.

---

## Out of scope (NOT part of this contract)

- `_build_deck_plate`, `_build_cabin_trunk`, etc. — private builders.
- `_sample_hull_sheer`, `_RollbackTracker`, etc. — private helpers.
- Glazing / window cutouts (deferred to v1.1+).
- Stanchion-and-rail railings (deferred to v1.1+).
- Fly bridge / swim platform / anchor pulpit / transom door (deferred).
- Cross-document deck building (explicitly rejected).
- Reading a Deck back from a `.FCStd` (`import_deck`): no, the deck module is build-only.
