# Contract: `storebro.interior` Public Python API

**Spec**: [../spec.md](../spec.md) | **Plan**: [../plan.md](../plan.md) | **Data model**: [../data-model.md](../data-model.md) | **Date**: 2026-05-17

Public API contract for the interior module. Governed by semantic versioning (constitution VI): breaking changes require a MAJOR bump and a documented migration path.

---

## Module path

```python
import storebro.interior
# or, re-exported from the package root:
from storebro import build_interior, Interior, InteriorParameterError, InteriorConstructionError
```

`storebro.interior.__all__`:

```python
__all__ = [
    "Interior",
    "InteriorConstructionError",
    "InteriorParameterError",
    "build_interior",
]
```

`Compartment`, `LayoutSpec`, `CompartmentSpec`, `Position3D`, `Dimensions3D` are visible via `Interior.<field>` attribute access but are NOT separately importable — same scoping choice as spec 003's sub-Body wrappers.

---

## Function: `build_interior`

```python
def build_interior(
    hull: "storebro.Hull",
    deck: "storebro.Deck",
    layout: str = "Alternativ3",
    *,
    document: "FreeCAD.Document | None" = None,
    name: str | None = None,
) -> Interior:
    """Build the parametric interior compartments on a hull and deck.

    Args:
        hull: A Hull returned by storebro.build_hull. Must have non-empty Shape.
        deck: A Deck returned by storebro.build_deck. Must be on the same
            document as hull (FR-019).
        layout: Either a canonical layout name ('Alternativ1' through
            'Alternativ5') or a filesystem path to a YAML layout file
            (default 'Alternativ3' per clarify Q4).
        document: Target FreeCAD document. None → use hull.document. Must
            equal hull.document if non-None.
        name: Base label for the Interior aggregate. None →
            f"Interior_{layout_name}". The compartment Bodies are labeled
            {name}_{compartment_type}, e.g. "Interior_Alternativ3_ForwardCabin".
            FreeCAD auto-numbering applies on collision.

    Returns:
        Interior: an aggregate with one Compartment wrapper per spec in the
        layout, plus the inputs and build duration.

    Raises:
        InteriorParameterError: Schema violation, envelope overflow, overlap,
            invalid hull/deck, or document mismatch. Raised BEFORE any FreeCAD
            call.
        InteriorConstructionError: Unsupported FreeCAD version, or FreeCAD-
            side failure mid-build (after rollback completes — the document
            is restored to its pre-call state).

    Example:
        >>> from storebro import build_hull, build_deck, build_interior
        >>> hull = build_hull()
        >>> deck = build_deck(hull)
        >>> interior = build_interior(hull, deck)
        >>> interior.layout.layout_name
        'Alternativ3'
        >>> len(interior.compartments) == 4
        True
    """
```

### Contract guarantees

1. **Pre-FreeCAD validation**. No FreeCAD call before YAML parsing, schema validation, envelope checks, and overlap checks all pass.
2. **Document binding**. `Interior.document is hull.document is deck.document`. Caller-supplied `document` MUST equal `hull.document` or `InteriorParameterError` is raised (FR-016).
3. **Compartments match layout**. `len(interior.compartments) == len(interior.layout.compartments)`.
4. **Envelope fit**. Every compartment Body's bbox is inside `hull.body.Shape.BoundBox` (SC-009).
5. **No overlap** (volume > 1e-6 m³). Face-touching shared bulkheads are permitted.
6. **Symmetry**. Every compartment Body is symmetric about the X-Z plane (FR-009).
7. **Rollback on failure**. FreeCAD-side failures roll back all Bodies added by this call (SC-008).
8. **Structural determinism**. Two calls with identical `(hull, deck, layout)` produce per-compartment identical volumes/bboxes within `1e-9` relative tolerance (SC-003).
9. **No logging**.

### Side effects

- Adds N `Part::Feature` objects to `hull.document` (one per compartment in the layout).
- Calls `document.recompute()` once before return.

---

## Class: `Interior`

```python
@dataclass(frozen=True)
class Interior:
    layout: LayoutSpec
    hull: "storebro.Hull"
    deck: "storebro.Deck"
    document: "FreeCAD.Document"
    label: str
    build_duration_seconds: float
    compartments: tuple[Compartment, ...]
```

Frozen, value-equal. `compartments` is a tuple (not list) for hashability.

---

## Exceptions

### `InteriorParameterError(ValueError)`

Same shape as spec 003's `DeckParameterError`, with `source`, `compartment_name`, `field`, `reason` attributes documenting which layout entry failed and why. Raised before any FreeCAD call.

### `InteriorConstructionError(RuntimeError)`

Mirrors spec 003's `DeckConstructionError` with an extra `layout_name` attribute. Raised after rollback completes.

Both classes are **independent** of spec 001/002/003's exception classes — each public module owns its own taxonomy.

---

## Layout source resolution

The `layout` argument is resolved in this order:

1. If `layout in {"Alternativ1", "Alternativ2", "Alternativ3", "Alternativ4", "Alternativ5"}` → load
   the corresponding fixture via `importlib.resources.files("storebro.fixtures") / f"{layout}.yaml"`.
2. Else if `layout` is a path to an existing file → load that file directly.
3. Else → raise `InteriorParameterError("layout", None, "layout", "must be one of the five canonical names or a path to a valid YAML file")`.

The five canonical names are the documented Storebro Royal Cruiser 34 1972 layout variants. User-supplied YAML files MUST follow the schema documented in `data-model.md`.

---

## YAML schema (v1)

```yaml
schema_version: 1
layout_name: Alternativ3
source: docs/references/Alternativ3.JPG
compartments:
  - name: ForwardCabin
    type: forward_cabin
    position: { x: 0.5, y: 0, z: 0.6 }
    dimensions: { length: 2.5, width: 2.1, height: 1.2 }
    description: V-berth forward cabin
  - name: Head
    type: head
    position: { x: 3.0, y: 0, z: 0.5 }
    dimensions: { length: 1.2, width: 1.0, height: 1.4 }
  # ...
```

All fields required except `description` on individual compartments. `schema_version` must be `1` in v1.0; unknown versions raise `InteriorParameterError`. `compartment_type` must be one of `forward_cabin`, `galley`, `head`, `salon`. `position.y` must be `0` (v1.0 symmetric-only).

---

## Versioning

- **PATCH**: bug fixes, refinement of canonical layout dimensions within ±5% of the cutaway citation, FreeCAD-version-range expansion.
- **MINOR**: new optional kwargs to `build_interior`, new optional fields on YAML schema (with defaults), new compartment types (added to the `forward_cabin/galley/head/salon` set), promoting sub-types to direct imports.
- **MAJOR**: removing a public name, removing a compartment type, bumping the YAML schema version, changing function signatures non-additively, dropping a previously-supported FreeCAD version, changing the `Alternativ1-5` canonical layout names.

---

## Out of scope (NOT part of this contract)

- `_load_and_validate_layout`, `_validate_compartment_in_envelope`, `_validate_no_overlaps`, `_build_compartment`, `_rollback`, `_RollbackTracker` — all private.
- Compartment furniture (bunks, settees, galley cabinetry) — out of scope, deferred.
- Engine room / aft cabin / dinette / wet locker — out of scope, deferred.
- Curved bulkheads following the hull — out of scope, deferred.
- Asymmetric compartments (`position.y != 0`) — out of scope, deferred.
- Glazing / window cutouts in compartment volumes — out of scope, deferred (coordinated with spec 003 v1.1+ work).
- Reading an interior back from `.FCStd` (`import_interior`) — write-only module.
