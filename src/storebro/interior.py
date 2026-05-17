"""Parametric Storebro interior module.

Public surface:
    build_interior       — function. Build N compartment Bodies from a YAML layout.
    Interior             — dataclass. build_interior return aggregate.
    InteriorParameterError — pre-FreeCAD validation failure.
    InteriorConstructionError — FreeCAD-side construction failure.

The module loads layout descriptions from YAML — either one of five canonical
fixtures shipped inside the package (`Alternativ1.yaml` through
`Alternativ5.yaml`) or a caller-supplied filesystem path. Each layout
materializes as a set of axis-aligned box compartments inside the FreeCAD
document that already holds the hull (spec 001) and deck (spec 003).

This is the project's first module with cross-dependency on two sibling
public modules — `storebro.hull` and `storebro.deck` — plus the shared
internal `storebro._freecad_check` helper. It does NOT import
`storebro.export` or `storebro.cli` (FR-011).
"""

from __future__ import annotations

import contextlib
import importlib.resources
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from storebro.deck import Deck
from storebro.hull import Hull

__all__ = [
    "Interior",
    "InteriorConstructionError",
    "InteriorParameterError",
    "build_interior",
]


# ---------------------------------------------------------------------------
# Exception classes (FR-015 + data-model §7/§8)
# ---------------------------------------------------------------------------


class InteriorParameterError(ValueError):
    """Raised before any FreeCAD call when an interior input is invalid.

    Attributes:
        source: YAML file path or canonical fixture name that the error
            pertains to.
        compartment_name: Name of the offending compartment, or None for
            top-level layout errors.
        field: Name of the offending field (e.g. ``"position.y"``,
            ``"schema_version"``), or None for non-field errors.
        reason: Human-readable explanation.

    Example:
        >>> err = InteriorParameterError("Alternativ3", "Salon", "dimensions.length", "must be > 0")
        >>> err.source
        'Alternativ3'
        >>> isinstance(err, ValueError)
        True
    """

    def __init__(
        self,
        source: str,
        compartment_name: str | None,
        field: str | None,
        reason: str,
    ) -> None:
        self.source = source
        self.compartment_name = compartment_name
        self.field = field
        self.reason = reason
        if compartment_name is None and field is None:
            message = f"InteriorParameterError: in {source} — {reason}"
        elif compartment_name is None:
            message = (
                f"InteriorParameterError: in {source} — field '{field}': {reason}"
            )
        elif field is None:
            message = (
                f"InteriorParameterError: in {source} — compartment "
                f"'{compartment_name}': {reason}"
            )
        else:
            message = (
                f"InteriorParameterError: in {source} — compartment "
                f"'{compartment_name}': field '{field}' — {reason}"
            )
        super().__init__(message)


class InteriorConstructionError(RuntimeError):
    """Raised when FreeCAD fails mid-build (after rollback completes) or
    when the FreeCAD version is outside the supported range.

    Attributes:
        layout_name: The layout that was being built.
        hull: The Hull the interior was being built on.
        deck: The Deck the interior was being built on.
        underlying: The wrapped FreeCAD-side exception.
        detected_version: ``(major, minor)`` for version-check failures only.
        supported_range: Human-readable range for version-check failures only.

    Example:
        >>> err = InteriorConstructionError("unsupported FreeCAD",
        ...                                  detected_version=(0, 20),
        ...                                  supported_range=">=1.1,<2.0")
        >>> err.detected_version
        (0, 20)
        >>> isinstance(err, RuntimeError)
        True
    """

    def __init__(
        self,
        message: str,
        *,
        layout_name: str | None = None,
        hull: Hull | None = None,
        deck: Deck | None = None,
        underlying: BaseException | None = None,
        detected_version: tuple[int, int] | None = None,
        supported_range: str | None = None,
    ) -> None:
        self.layout_name = layout_name
        self.hull = hull
        self.deck = deck
        self.underlying = underlying
        self.detected_version = detected_version
        self.supported_range = supported_range
        super().__init__(f"InteriorConstructionError: {message}")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_COMPARTMENT_TYPES: frozenset[str] = frozenset(
    {"forward_cabin", "galley", "head", "salon"}
)
_CANONICAL_LAYOUT_NAMES: frozenset[str] = frozenset(
    {"Alternativ1", "Alternativ2", "Alternativ3", "Alternativ4", "Alternativ5"}
)
_OVERLAP_THRESHOLD_M3 = 1.0e-6


# ---------------------------------------------------------------------------
# Value objects (data-model §1-§4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Position3D:
    """Compartment forward-bottom-center reference point (clarify Q3).

    Example:
        >>> p = Position3D(x=0.5, y=0.0, z=0.6)
        >>> p.y
        0.0
    """

    x: float
    y: float
    z: float


@dataclass(frozen=True)
class Dimensions3D:
    """Compartment outer dimensions.

    Example:
        >>> d = Dimensions3D(length=2.5, width=2.1, height=1.2)
        >>> d.length
        2.5
    """

    length: float
    width: float
    height: float


@dataclass(frozen=True)
class CompartmentSpec:
    """One compartment's parsed YAML entry.

    Example:
        >>> spec = CompartmentSpec(
        ...     name="ForwardCabin",
        ...     compartment_type="forward_cabin",
        ...     position=Position3D(0.5, 0.0, 0.6),
        ...     dimensions=Dimensions3D(2.5, 2.1, 1.2),
        ... )
        >>> spec.name
        'ForwardCabin'
    """

    name: str
    compartment_type: str
    position: Position3D
    dimensions: Dimensions3D
    description: str | None = None


@dataclass(frozen=True)
class LayoutSpec:
    """A parsed and validated layout (canonical or custom).

    Example:
        >>> # Loaded via _load_and_validate_layout("Alternativ3")
    """

    schema_version: int
    layout_name: str
    source: str
    compartments: tuple[CompartmentSpec, ...]


# ---------------------------------------------------------------------------
# Compartment + Interior aggregate (data-model §5-§6)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Compartment:
    """Wrapper around the FreeCAD Body for a single compartment.

    Example:
        >>> # Accessed via Interior.compartments after build_interior() returns.
    """

    spec: CompartmentSpec
    body: Any


@dataclass(frozen=True)
class Interior:
    """build_interior return value.

    Example:
        >>> # from storebro import build_hull, build_deck, build_interior
        >>> # interior = build_interior(build_deck(build_hull()))  # doctest: +SKIP
        >>> # interior.layout.layout_name  # doctest: +SKIP
        >>> # 'Alternativ3'
    """

    layout: LayoutSpec
    hull: Hull
    deck: Deck
    document: Any
    label: str
    build_duration_seconds: float
    compartments: tuple[Compartment, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Layout loading + schema validation
# ---------------------------------------------------------------------------


def _load_layout(source: str) -> tuple[str, dict[str, Any]]:
    """Resolve `source` to a YAML document.

    Returns the resolved source identifier (canonical name or absolute path)
    plus the parsed dict.
    """
    if source in _CANONICAL_LAYOUT_NAMES:
        try:
            fixture_path = (
                importlib.resources.files("storebro.fixtures") / f"{source}.yaml"
            )
            text = fixture_path.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError) as exc:
            raise InteriorParameterError(
                source, None, None, f"canonical fixture not found: {exc}"
            ) from exc
        try:
            return source, yaml.safe_load(text) or {}
        except yaml.YAMLError as exc:
            raise InteriorParameterError(
                source, None, None, f"YAML parse error: {exc}"
            ) from exc

    path = Path(source).expanduser()
    if not path.is_file():
        raise InteriorParameterError(
            source,
            None,
            "layout",
            "must be one of the five canonical names "
            "(Alternativ1-5) or a path to a valid YAML file",
        )
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InteriorParameterError(
            source, None, None, f"unable to read file: {exc}"
        ) from exc
    try:
        return str(path.resolve()), yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise InteriorParameterError(
            source, None, None, f"YAML parse error: {exc}"
        ) from exc


def _validate_layout_schema(raw: dict[str, Any], source: str) -> LayoutSpec:
    """Validate raw YAML dict against the v1 schema and build a LayoutSpec."""
    if not isinstance(raw, dict):
        raise InteriorParameterError(
            source, None, None, "top-level YAML must be a mapping"
        )

    if "schema_version" not in raw:
        raise InteriorParameterError(
            source, None, "schema_version", "field is required (v1.0 fixtures use schema_version: 1)"
        )
    if raw["schema_version"] != 1:
        raise InteriorParameterError(
            source,
            None,
            "schema_version",
            f"must be 1 (got {raw['schema_version']!r})",
        )

    layout_name = raw.get("layout_name")
    if not isinstance(layout_name, str) or not layout_name:
        raise InteriorParameterError(
            source, None, "layout_name", "must be a non-empty string"
        )

    src_field = raw.get("source")
    if not isinstance(src_field, str) or not src_field:
        raise InteriorParameterError(
            source, None, "source", "must be a non-empty string"
        )

    compartments_raw = raw.get("compartments")
    if not isinstance(compartments_raw, list) or not compartments_raw:
        raise InteriorParameterError(
            source, None, "compartments", "must be a non-empty list"
        )

    seen_names: set[str] = set()
    compartments: list[CompartmentSpec] = []
    for entry in compartments_raw:
        spec = _parse_compartment_entry(entry, source, seen_names)
        compartments.append(spec)
        seen_names.add(spec.name)

    return LayoutSpec(
        schema_version=1,
        layout_name=layout_name,
        source=src_field,
        compartments=tuple(compartments),
    )


def _parse_compartment_entry(
    entry: Any, source: str, seen_names: set[str]
) -> CompartmentSpec:
    if not isinstance(entry, dict):
        raise InteriorParameterError(
            source, None, "compartments[i]", "each compartment must be a mapping"
        )

    name = entry.get("name")
    if not isinstance(name, str) or not name:
        raise InteriorParameterError(
            source, None, "name", "each compartment must have a non-empty `name`"
        )
    if name in seen_names:
        raise InteriorParameterError(
            source, name, "name", "duplicate compartment name"
        )

    ctype = entry.get("type")
    if ctype not in _COMPARTMENT_TYPES:
        raise InteriorParameterError(
            source,
            name,
            "type",
            f"must be one of {sorted(_COMPARTMENT_TYPES)} (got {ctype!r})",
        )

    position = _parse_position(entry.get("position"), source, name)
    if position.y != 0:
        raise InteriorParameterError(
            source,
            name,
            "position.y",
            "must be 0 in v1.0 (asymmetric layouts deferred to v1.1+)",
        )

    dimensions = _parse_dimensions(entry.get("dimensions"), source, name)

    description = entry.get("description")
    if description is not None and not isinstance(description, str):
        raise InteriorParameterError(
            source, name, "description", "must be a string if provided"
        )

    return CompartmentSpec(
        name=name,
        compartment_type=ctype,
        position=position,
        dimensions=dimensions,
        description=description,
    )


def _parse_position(raw: Any, source: str, compartment_name: str) -> Position3D:
    if not isinstance(raw, dict):
        raise InteriorParameterError(
            source,
            compartment_name,
            "position",
            "must be a mapping with x, y, z keys",
        )
    for axis in ("x", "y", "z"):
        if axis not in raw:
            raise InteriorParameterError(
                source,
                compartment_name,
                f"position.{axis}",
                "missing required axis key",
            )
        if not isinstance(raw[axis], (int, float)):
            raise InteriorParameterError(
                source,
                compartment_name,
                f"position.{axis}",
                f"must be a number (got {type(raw[axis]).__name__})",
            )
    return Position3D(x=float(raw["x"]), y=float(raw["y"]), z=float(raw["z"]))


def _parse_dimensions(
    raw: Any, source: str, compartment_name: str
) -> Dimensions3D:
    if not isinstance(raw, dict):
        raise InteriorParameterError(
            source,
            compartment_name,
            "dimensions",
            "must be a mapping with length, width, height keys",
        )
    for axis in ("length", "width", "height"):
        if axis not in raw:
            raise InteriorParameterError(
                source,
                compartment_name,
                f"dimensions.{axis}",
                "missing required dimension key",
            )
        if not isinstance(raw[axis], (int, float)):
            raise InteriorParameterError(
                source,
                compartment_name,
                f"dimensions.{axis}",
                f"must be a number (got {type(raw[axis]).__name__})",
            )
        if raw[axis] <= 0:
            raise InteriorParameterError(
                source,
                compartment_name,
                f"dimensions.{axis}",
                f"must be > 0 (got {raw[axis]!r})",
            )
    return Dimensions3D(
        length=float(raw["length"]),
        width=float(raw["width"]),
        height=float(raw["height"]),
    )


# ---------------------------------------------------------------------------
# Hull / deck / document validation
# ---------------------------------------------------------------------------


def _validate_hull(hull: Hull | None) -> None:
    if hull is None:
        raise InteriorParameterError("interior", None, "hull", "must not be None")
    body = getattr(hull, "body", None)
    if body is None:
        raise InteriorParameterError(
            "interior", None, "hull", "Hull object has no `.body` attribute"
        )
    shape = getattr(body, "Shape", None)
    if shape is None or getattr(shape, "isNull", lambda: True)():
        raise InteriorParameterError(
            "interior",
            None,
            "hull",
            "hull body has no shape — recompute the source document first",
        )


def _validate_deck(deck: Deck | None, hull: Hull) -> None:
    if deck is None:
        raise InteriorParameterError("interior", None, "deck", "must not be None")
    deck_plate = getattr(deck, "deck_plate", None)
    if deck_plate is None or getattr(deck_plate, "body", None) is None:
        raise InteriorParameterError(
            "interior", None, "deck", "Deck object has no `.deck_plate.body`"
        )
    if deck.document is not hull.document:
        raise InteriorParameterError(
            "interior",
            None,
            "deck.document",
            "must equal hull.document — deck was not built on this hull",
        )


def _resolve_document(hull: Hull, document: Any) -> Any:
    if document is None:
        return hull.document
    if document is hull.document:
        return document
    raise InteriorParameterError(
        "interior",
        None,
        "document",
        "must equal hull.document for cross-module consistency",
    )


# ---------------------------------------------------------------------------
# Envelope + overlap validators
# ---------------------------------------------------------------------------


def _validate_compartment_in_envelope(
    spec: CompartmentSpec, hull: Hull, source: str
) -> None:
    """Reject compartments that exceed the hull envelope (FR-010)."""
    hp = hull.parameters
    if spec.position.x < 0:
        raise InteriorParameterError(
            source,
            spec.name,
            "position.x",
            f"must be >= 0 (got {spec.position.x})",
        )
    if spec.position.x + spec.dimensions.length > hp.loa:
        raise InteriorParameterError(
            source,
            spec.name,
            "dimensions.length",
            f"extends past stem (loa = {hp.loa} m)",
        )
    if spec.dimensions.width > hp.beam_max:
        raise InteriorParameterError(
            source,
            spec.name,
            "dimensions.width",
            f"exceeds hull beam_max ({hp.beam_max} m)",
        )
    if spec.position.z < -hp.draft:
        raise InteriorParameterError(
            source,
            spec.name,
            "position.z",
            f"floor is below keel (draft = {hp.draft} m)",
        )
    # Headroom above sheer covers cabin trunk; 1.5 m fixed budget.
    if spec.position.z + spec.dimensions.height > hp.sheer_height_fwd + 1.5:
        raise InteriorParameterError(
            source,
            spec.name,
            "dimensions.height",
            f"ceiling exceeds cabin trunk top "
            f"({hp.sheer_height_fwd} + 1.5 m headroom)",
        )


def _aabb_intersection_volume(
    c1: CompartmentSpec, c2: CompartmentSpec
) -> float:
    """AABB intersection volume for two compartments centered on Y=0."""
    # X overlap
    a_min = c1.position.x
    a_max = c1.position.x + c1.dimensions.length
    b_min = c2.position.x
    b_max = c2.position.x + c2.dimensions.length
    x_overlap = max(0.0, min(a_max, b_max) - max(a_min, b_min))

    # Y overlap (centered on 0)
    a_half = c1.dimensions.width / 2.0
    b_half = c2.dimensions.width / 2.0
    y_overlap = max(0.0, min(a_half, b_half) - max(-a_half, -b_half))

    # Z overlap
    a_min_z = c1.position.z
    a_max_z = c1.position.z + c1.dimensions.height
    b_min_z = c2.position.z
    b_max_z = c2.position.z + c2.dimensions.height
    z_overlap = max(0.0, min(a_max_z, b_max_z) - max(a_min_z, b_min_z))

    return x_overlap * y_overlap * z_overlap


def _validate_no_overlaps(
    compartments: tuple[CompartmentSpec, ...], source: str
) -> None:
    """Pairwise compartment-overlap check (FR-012)."""
    for i, c1 in enumerate(compartments):
        for c2 in compartments[i + 1 :]:
            overlap = _aabb_intersection_volume(c1, c2)
            if overlap > _OVERLAP_THRESHOLD_M3:
                raise InteriorParameterError(
                    source,
                    None,
                    "compartments",
                    f"compartments '{c1.name}' and '{c2.name}' overlap by "
                    f"{overlap:.6f} m^3 (threshold {_OVERLAP_THRESHOLD_M3})",
                )


# ---------------------------------------------------------------------------
# FreeCAD support + rollback (research R6, R7)
# ---------------------------------------------------------------------------


def _ensure_freecad_supported() -> None:
    from storebro import _freecad_check

    try:
        _freecad_check.ensure_supported_freecad()
    except Exception as exc:
        detected = getattr(exc, "detected_version", None)
        supported = getattr(exc, "supported_range", None)
        raise InteriorConstructionError(
            "unsupported FreeCAD version while preparing interior build",
            detected_version=detected,
            supported_range=supported,
            underlying=exc,
        ) from exc


def _rollback(target_doc: Any, added_objects: list[Any]) -> None:
    for obj in reversed(added_objects):
        with contextlib.suppress(Exception):
            target_doc.removeObject(obj.Name)
    with contextlib.suppress(Exception):
        target_doc.recompute()


# ---------------------------------------------------------------------------
# Compartment builder (T030)
# ---------------------------------------------------------------------------


def _compartment_label(spec: CompartmentSpec, layout_name: str) -> str:
    parts = [p.capitalize() for p in spec.compartment_type.split("_")]
    return f"Interior_{layout_name}_{''.join(parts)}"


def _build_compartment(
    spec: CompartmentSpec,
    layout_name: str,
    target_doc: Any,
    added: list[Any],
) -> Compartment:
    """Build one compartment as an axis-aligned Part::Feature box.

    Centered on Y=0; positioned at forward-bottom-center per clarify Q3.
    """
    import FreeCAD
    import Part

    half_w = spec.dimensions.width / 2.0
    box = Part.makeBox(
        spec.dimensions.length,
        spec.dimensions.width,
        spec.dimensions.height,
    )
    box.translate(
        FreeCAD.Vector(spec.position.x, -half_w, spec.position.z)
    )

    label = _compartment_label(spec, layout_name)
    obj = target_doc.addObject("Part::Feature", label)
    obj.Shape = box
    added.append(obj)

    # FR-007: expose dimensions as named GUI-editable properties.
    obj.addProperty("App::PropertyLength", "Length", "Compartment", "Compartment length")
    obj.addProperty("App::PropertyLength", "Width", "Compartment", "Compartment width")
    obj.addProperty("App::PropertyLength", "Height", "Compartment", "Compartment height")
    obj.Length = spec.dimensions.length * 1000.0
    obj.Width = spec.dimensions.width * 1000.0
    obj.Height = spec.dimensions.height * 1000.0

    return Compartment(spec=spec, body=obj)


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------


def build_interior(
    hull: Hull,
    deck: Deck,
    layout: str = "Alternativ3",
    *,
    document: Any = None,
    name: str | None = None,
) -> Interior:
    """Build the parametric interior compartments on a hull and deck.

    Args:
        hull: A Hull from ``storebro.hull.build_hull``. Must have non-empty
            Shape.
        deck: A Deck from ``storebro.deck.build_deck``. Must be on the same
            document as `hull`.
        layout: Either a canonical layout name (``"Alternativ1"`` through
            ``"Alternativ5"``) or a filesystem path to a YAML layout file.
            Defaults to ``"Alternativ3"`` (clarify Q4).
        document: Target FreeCAD document. ``None`` → use ``hull.document``.
            Must equal ``hull.document`` when non-None.
        name: Base label for the Interior aggregate. ``None`` →
            ``f"Interior_{layout.layout_name}"``. Compartment Bodies are
            labeled ``{name}_{CompartmentType}``.

    Returns:
        :class:`Interior` — aggregate with one :class:`Compartment` wrapper
        per layout spec.

    Raises:
        InteriorParameterError: Schema violation, envelope overflow,
            compartment overlap, invalid hull/deck, document mismatch.
            Raised BEFORE any FreeCAD call.
        InteriorConstructionError: Unsupported FreeCAD version, or FreeCAD-
            side failure mid-build (after rollback restores the document).

    Example:
        >>> # from storebro import build_hull, build_deck, build_interior
        >>> # interior = build_interior(build_deck(build_hull()))  # doctest: +SKIP
        >>> # len(interior.compartments)  # doctest: +SKIP
        >>> # 4
    """
    _ensure_freecad_supported()

    resolved_source, raw_layout = _load_layout(layout)
    layout_spec = _validate_layout_schema(raw_layout, resolved_source)

    _validate_hull(hull)
    _validate_deck(deck, hull)

    for spec in layout_spec.compartments:
        _validate_compartment_in_envelope(spec, hull, resolved_source)
    _validate_no_overlaps(layout_spec.compartments, resolved_source)

    target_doc = _resolve_document(hull, document)
    resolved_label = (
        name if name is not None else f"Interior_{layout_spec.layout_name}"
    )

    started = time.perf_counter()
    added: list[Any] = []
    try:
        compartments: list[Compartment] = []
        for spec in layout_spec.compartments:
            compartment = _build_compartment(
                spec, layout_spec.layout_name, target_doc, added
            )
            compartments.append(compartment)
        target_doc.recompute()
    except InteriorParameterError:
        _rollback(target_doc, added)
        raise
    except InteriorConstructionError:
        _rollback(target_doc, added)
        raise
    except BaseException as exc:
        _rollback(target_doc, added)
        raise InteriorConstructionError(
            f"build_interior failed during compartment construction — "
            f"{type(exc).__name__}: {exc}",
            layout_name=layout_spec.layout_name,
            hull=hull,
            deck=deck,
            underlying=exc,
        ) from exc

    duration = time.perf_counter() - started
    return Interior(
        layout=layout_spec,
        hull=hull,
        deck=deck,
        document=target_doc,
        label=resolved_label,
        build_duration_seconds=duration,
        compartments=tuple(compartments),
    )
