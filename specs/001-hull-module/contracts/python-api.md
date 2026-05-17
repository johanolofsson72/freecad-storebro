# Contract: `storebro.hull` Public Python API

**Spec**: [../spec.md](../spec.md) | **Plan**: [../plan.md](../plan.md) | **Data model**: [../data-model.md](../data-model.md) | **Date**: 2026-05-17

This is the **public API contract** for the hull module. Everything documented here is governed by semantic versioning (constitution principle VI): breaking changes require a MAJOR bump and a documented migration path. Anything not documented here is private and may change in any PATCH release.

---

## Module path

```python
import storebro.hull
# or, re-exported from the package root:
from storebro import build_hull, HullParameters, HullParameterError, HullConstructionError
```

`storebro.hull.__all__` exactly lists the public surface:

```python
__all__ = [
    "build_hull",
    "HullParameters",
    "HullParameterError",
    "HullConstructionError",
    "Hull",
]
```

---

## Function: `build_hull`

```python
def build_hull(
    parameters: HullParameters | None = None,
    *,
    document: "FreeCAD.Document | None" = None,
    name: str = "Hull",
) -> Hull:
    """Build a parametric Storebro hull Body in a FreeCAD document.

    Args:
        parameters: Hull dimensional parameters. None → use HullParameters() defaults
            (the canonical Storebro Royal Cruiser 34, 1972 model, within ±1%
            reference fidelity for the citation-grade LOA and beam).
        document: Target FreeCAD document. None → use FreeCAD.activeDocument()
            if one exists, else create a new one and activate it. The document is
            NOT renamed or otherwise mutated beyond the Body addition.
        name: Body Label. Defaults to "Hull". FreeCAD's standard auto-numbering
            applies on label collision (e.g. "Hull", "Hull001", "Hull002").

    Returns:
        Hull: a dataclass wrapping the FreeCAD Body, the input parameters, the
        target document, the resolved label, and the build duration.

    Raises:
        HullParameterError: If `parameters` (or its defaults) fails validation.
            Raised BEFORE any FreeCAD call.
        HullConstructionError: If the FreeCAD runtime version is outside the
            supported range, or if FreeCAD fails to construct the hull despite
            valid parameters.

    Example:
        >>> from storebro import build_hull, HullParameters
        >>> hull = build_hull()  # defaults: Storebro Royal Cruiser 34 (1972)
        >>> abs(hull.bbox[0] - 10.35) < 0.1035  # within ±1% of LOA = 10.35 m
        True
        >>> custom = build_hull(HullParameters(loa=12.0, beam_max=3.8))
        >>> custom.bbox[0] > hull.bbox[0]
        True
    """
```

### Contract guarantees

1. **No FreeCAD calls before parameter validation.** If `parameters` is invalid, `HullParameterError` is raised before `FreeCAD.newDocument`, `FreeCAD.activeDocument`, or any geometry call. This is verifiable from the call trace.
2. **Structural determinism.** Two calls with the same `HullParameters` (and the version-check having already passed) produce Bodies with identical volume, bounding-box dimensions, and topology counts. Byte-identical `.FCStd` is NOT guaranteed — that's the export module's contract.
3. **No silent mutation.** A caller-supplied `document` is not renamed, its top-level properties are not mutated, and no document is closed.
4. **Body is parametric.** The returned `Body` exposes hull dimensions as named FreeCAD `App::PropertyLength` / `App::PropertyAngle` properties. Editing them in the GUI recomputes the geometry.
5. **No logging.** v1.0 produces no log output, no metrics, no progress events.
6. **Idempotent re-invocation.** Calling `build_hull` twice in the same document adds two independent Bodies. The first has Label `"Hull"`, the second `"Hull001"` (via FreeCAD's auto-numbering).
7. **Lazy version check.** The supported-FreeCAD-version check runs on first invocation per process. Subsequent calls in the same process skip the check.

### Side effects

- Adds one `Part::Body` to the target FreeCAD document (the document is created if missing).
- The Body contains: 5 `Sketcher::Sketch` station sketches, 1 `PartDesign::AdditiveLoft`, 1 `PartDesign::Mirrored`.
- Document `recompute()` is invoked once before return so the geometry is current.

---

## Class: `HullParameters`

```python
@dataclass(frozen=True)
class HullParameters:
    loa: float = 10.35                   # m,  > 0 and > beam_max  (citation: RC34 1972)
    beam_max: float = 3.20               # m,  > 0 and < loa       (citation: RC34 1972)
    draft: float = 0.95                  # m,  > 0                  (estimate)
    freeboard: float = 0.95              # m,  > 0                  (estimate)
    deadrise_amidships: float = 16.0     # deg, [0, 30]             (estimate)
    sheer_height_aft: float = 0.85       # m,  > 0 and <= sheer_height_fwd  (estimate)
    sheer_height_fwd: float = 1.30       # m,  > 0 and >= sheer_height_aft  (estimate)
    transom_angle: float = 12.0          # deg, [0, 45]             (estimate)

    REFERENCE_STOREBRO_ROYAL_CRUISER_34_1972: ClassVar[dict[str, float]] = {...}

    @property
    def aspect_ratio(self) -> float: ...

    @property
    def is_planing_hull(self) -> bool: ...
```

### Contract guarantees

1. **Frozen**. Field assignment after construction raises `dataclasses.FrozenInstanceError`.
2. **Hashable**. `hash(HullParameters(...))` works; two instances with equal fields hash the same.
3. **Validated at construction**. `__post_init__` raises `HullParameterError` if any field or cross-field constraint fails. A successfully-constructed `HullParameters` is guaranteed valid — `build_hull` does not need to re-validate the same instance.
4. **Defaults are reference-fidelity**. The default-field values (no arguments) produce a hull whose bounding-box LOA and beam are within ±1% of the citation-grade Royal Cruiser 34 (1972) reference (SC-001). The remaining six parameters are estimate-grade and self-cite.

---

## Class: `Hull`

```python
@dataclass
class Hull:
    body: "FreeCAD.DocumentObject"
    parameters: HullParameters
    document: "FreeCAD.Document"
    label: str
    build_duration_seconds: float

    @property
    def bbox(self) -> tuple[float, float, float]:
        """(length, width, height) of body.Shape.BoundBox."""

    @property
    def volume(self) -> float:
        """body.Shape.Volume."""
```

### Contract guarantees

1. **`body.Shape.isClosed()` is `True`** (FR-010, closed watertight shell).
2. **`bbox[0]` ≈ `parameters.loa`** within FreeCAD's geometric tolerance (i.e. the bbox length matches the requested LOA).
3. **`build_duration_seconds < 30.0`** for default parameters on a developer laptop (SC-002). This is a soft guarantee — extreme parameter values may exceed it. The default-parameter case is hard-enforced via a test.

---

## Exceptions

### `HullParameterError(ValueError)`

```python
class HullParameterError(ValueError):
    parameter_name: str
    parameter_value: float | None
    valid_range: str

    def __init__(self, parameter_name: str, parameter_value: float | None, valid_range: str): ...
```

Subclasses `ValueError` so broad-catch idioms (`except ValueError`) still work. The three attributes are always set by `__init__`.

### `HullConstructionError(RuntimeError)`

```python
class HullConstructionError(RuntimeError):
    parameters: HullParameters | None
    underlying: BaseException | None
    detected_version: tuple[int, int] | None
    supported_range: str | None

    def __init__(self, message: str, *,
                 parameters: HullParameters | None = None,
                 underlying: BaseException | None = None,
                 detected_version: tuple[int, int] | None = None,
                 supported_range: str | None = None): ...
```

Subclasses `RuntimeError` so broad-catch idioms still work. Attributes that don't apply to a particular failure mode (e.g. `detected_version` on a FreeCAD-side construction failure) are `None`.

---

## Versioning

This contract is versioned with `storebro.__version__`. The hull module is part of the package's MAJOR version surface:

- **PATCH** (e.g. 1.0.0 → 1.0.1): bug fixes, internal refactor, default-value refinement within the ±1% reference fidelity band, expansion of the supported FreeCAD version range.
- **MINOR** (e.g. 1.0.0 → 1.1.0): new public optional kwargs to `build_hull`, new optional fields on `HullParameters` (with defaults), new public read-only properties on `Hull`, additional exception attributes (only-add, never-remove).
- **MAJOR** (e.g. 1.0.0 → 2.0.0): any of: removing a public name, changing a default value beyond ±1%, changing exception class hierarchies, changing function signatures in a non-additive way, dropping a previously-supported FreeCAD version.

---

## Out of scope (NOT part of this contract)

- The `_StationProfile`, `_HullDimensions`, `_freecad_check`, and any underscore-prefixed names are private.
- The exact internal feature names inside the `Part::Body` ("Sketch001", "AdditiveLoft", etc.) are not part of the contract. The export module (spec 002) is responsible for normalizing them in `.FCStd` output if reproducibility there demands it.
- The exact order of feature appearance in the FreeCAD document tree is internal.
- Any behavior under `FreeCAD < 1.1` is "raises `HullConstructionError`" — anything more specific is out of contract.
