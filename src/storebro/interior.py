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
from typing import Any, Literal

import yaml

from storebro.deck import Deck
from storebro.hull import Hull

__all__ = [
    "BerthParameters",
    "BulkheadParameters",
    "FurnitureParameters",
    "GalleyParameters",
    "HeadParameters",
    "HelmParameters",
    "Interior",
    "InteriorConstructionError",
    "InteriorParameterError",
    "SalonParameters",
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
            message = f"InteriorParameterError: in {source} — field '{field}': {reason}"
        elif field is None:
            message = (
                f"InteriorParameterError: in {source} — compartment '{compartment_name}': {reason}"
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
    {"forward_cabin", "galley", "head", "salon", "helm"}  # spec 023: helm (DS)
)
_CANONICAL_LAYOUT_NAMES: frozenset[str] = frozenset(
    {"Alternativ1", "Alternativ2", "Alternativ3", "Alternativ4", "Alternativ5"}
)
# spec 023 — the DS enclosed-saloon layout is a bundled fixture loadable by name
# (like the canonical five) but kept out of _CANONICAL_LAYOUT_NAMES so the
# five-name contracts are unchanged.
_DS_LAYOUT_NAME = "DsSaloon"
_BUNDLED_LAYOUT_NAMES: frozenset[str] = _CANONICAL_LAYOUT_NAMES | {_DS_LAYOUT_NAME}
_OVERLAP_THRESHOLD_M3 = 1.0e-6
# spec 017: single metre→millimetre conversion authority for the geometry-
# construction boundary. Layouts/fixtures are authored in metres; FreeCAD's
# internal length unit is millimetres. Every coordinate handed to Part/Vector
# is multiplied by this constant, exactly as the hull module does with
# `hull._MM_PER_M`. Validation stays in metre-space and does NOT use it.
_M_TO_MM = 1000.0


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
# Spec 012 — furniture parameter dataclasses (data-model §1)
#
# Type-keyed furniture for Alt1/Alt2 compartments. All lengths in mm.
# Validation raises InteriorParameterError (source="FurnitureParameters").
# Furniture is built as Part::Feature B-rep solids (matching the module's
# spec 004 idiom); the galley counter uses a boolean Part.Cut for recesses.
# ---------------------------------------------------------------------------


def _furniture_error(field_name: str, reason: str) -> InteriorParameterError:
    """Build an InteriorParameterError for a furniture-parameter violation."""
    return InteriorParameterError("FurnitureParameters", None, field_name, reason)


@dataclass(frozen=True)
class BerthParameters:
    """Forward-cabin berth (base + cushions) parameters (data-model §1.1).

    Example:
        >>> p = BerthParameters()
        >>> p.base_height, p.cushion_count
        (350.0, 1)
    """

    base_height: float = 350.0
    cushion_thickness: float = 100.0
    cushion_count: int = 1
    wall_inset: float = 50.0

    def __post_init__(self) -> None:
        for name, value in (
            ("berth_base_height", self.base_height),
            ("berth_cushion_thickness", self.cushion_thickness),
        ):
            if value <= 0:
                raise _furniture_error(name, "must be > 0")
        if self.cushion_count < 0:
            raise _furniture_error("berth_cushion_count", "must be >= 0")
        if self.wall_inset < 0:
            raise _furniture_error("berth_wall_inset", "must be >= 0")


@dataclass(frozen=True)
class GalleyParameters:
    """Galley counter + sink/stove recess parameters (data-model §1.2).

    Recess depths must stay below the counter thickness so the boolean cut
    is a blind recess (manifold by construction; spec 009/011 lesson).

    Example:
        >>> p = GalleyParameters()
        >>> p.counter_height, p.cutouts_enabled
        (900.0, True)
    """

    counter_height: float = 900.0
    counter_thickness: float = 40.0
    sink_recess_depth: float = 30.0
    stove_recess_depth: float = 20.0
    cutouts_enabled: bool = True

    def __post_init__(self) -> None:
        for name, value in (
            ("galley_counter_height", self.counter_height),
            ("galley_counter_thickness", self.counter_thickness),
            ("galley_sink_recess_depth", self.sink_recess_depth),
            ("galley_stove_recess_depth", self.stove_recess_depth),
        ):
            if value <= 0:
                raise _furniture_error(name, "must be > 0")
        for name, value in (
            ("galley_sink_recess_depth", self.sink_recess_depth),
            ("galley_stove_recess_depth", self.stove_recess_depth),
        ):
            if value >= self.counter_thickness:
                raise _furniture_error(
                    name, "must be < counter_thickness (blind recess, not through)"
                )


@dataclass(frozen=True)
class HeadParameters:
    """Head toilet + sink parameters (data-model §1.3).

    Example:
        >>> p = HeadParameters()
        >>> p.toilet_height, p.sink_height
        (400.0, 800.0)
    """

    toilet_height: float = 400.0
    sink_height: float = 800.0

    def __post_init__(self) -> None:
        for name, value in (
            ("head_toilet_height", self.toilet_height),
            ("head_sink_height", self.sink_height),
        ):
            if value <= 0:
                raise _furniture_error(name, "must be > 0")


@dataclass(frozen=True)
class SalonParameters:
    """Salon seating + table parameters (data-model §1.4).

    Example:
        >>> p = SalonParameters()
        >>> p.seat_height, p.table_height
        (400.0, 650.0)
    """

    seat_height: float = 400.0
    table_height: float = 650.0

    def __post_init__(self) -> None:
        for name, value in (
            ("salon_seat_height", self.seat_height),
            ("salon_table_height", self.table_height),
        ):
            if value <= 0:
                raise _furniture_error(name, "must be > 0")


@dataclass(frozen=True)
class HelmParameters:
    """Helm-station console + seat parameters (spec 023, DS enclosed saloon).

    Example:
        >>> p = HelmParameters()
        >>> p.console_height, p.seat_height
        (1100.0, 550.0)
    """

    console_height: float = 1100.0
    console_depth: float = 500.0
    seat_height: float = 550.0

    def __post_init__(self) -> None:
        for name, value in (
            ("helm_console_height", self.console_height),
            ("helm_console_depth", self.console_depth),
            ("helm_seat_height", self.seat_height),
        ):
            if value <= 0:
                raise _furniture_error(name, "must be > 0")


@dataclass(frozen=True)
class BulkheadParameters:
    """Bulkhead partition parameters (data-model §1.5).

    Example:
        >>> p = BulkheadParameters()
        >>> p.thickness
        25.0
    """

    thickness: float = 25.0

    def __post_init__(self) -> None:
        if self.thickness <= 0:
            raise _furniture_error("bulkhead_thickness", "must be > 0")


@dataclass(frozen=True)
class FurnitureParameters:
    """Composite of the per-type furniture parameter dataclasses (data-model §1.6).

    The optional ``parameters_furniture`` entry point for :func:`build_interior`.

    Example:
        >>> p = FurnitureParameters()
        >>> p.berth.base_height, p.galley.counter_height
        (350.0, 900.0)
    """

    berth: BerthParameters = field(default_factory=BerthParameters)
    galley: GalleyParameters = field(default_factory=GalleyParameters)
    head: HeadParameters = field(default_factory=HeadParameters)
    salon: SalonParameters = field(default_factory=SalonParameters)
    bulkhead: BulkheadParameters = field(default_factory=BulkheadParameters)
    helm: HelmParameters = field(default_factory=HelmParameters)  # spec 023 (DS)


# ---------------------------------------------------------------------------
# Compartment + Interior aggregate (data-model §5-§6)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Compartment:
    """Wrapper around the FreeCAD Body for a single compartment.

    For furnished (Alt1/Alt2) compartments ``body`` is a ``Part::Compound`` of
    the furniture pieces (+ bulkhead) and ``furniture`` holds the individual
    bodies; for unfurnished compartments ``body`` is the legacy single box.

    Example:
        >>> # Accessed via Interior.compartments after build_interior() returns.
    """

    spec: CompartmentSpec
    body: Any
    furniture: tuple[Any, ...] = ()
    is_furnished: bool = False


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
    if source in _BUNDLED_LAYOUT_NAMES:
        try:
            fixture_path = importlib.resources.files("storebro.fixtures") / f"{source}.yaml"
            text = fixture_path.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError) as exc:
            raise InteriorParameterError(
                source, None, None, f"canonical fixture not found: {exc}"
            ) from exc
        try:
            return source, yaml.safe_load(text) or {}
        except yaml.YAMLError as exc:
            raise InteriorParameterError(source, None, None, f"YAML parse error: {exc}") from exc

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
        raise InteriorParameterError(source, None, None, f"unable to read file: {exc}") from exc
    try:
        return str(path.resolve()), yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise InteriorParameterError(source, None, None, f"YAML parse error: {exc}") from exc


def _validate_layout_schema(raw: dict[str, Any], source: str) -> LayoutSpec:
    """Validate raw YAML dict against the v1 schema and build a LayoutSpec."""
    if not isinstance(raw, dict):
        raise InteriorParameterError(source, None, None, "top-level YAML must be a mapping")

    if "schema_version" not in raw:
        raise InteriorParameterError(
            source,
            None,
            "schema_version",
            "field is required (v1.0 fixtures use schema_version: 1)",
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
        raise InteriorParameterError(source, None, "layout_name", "must be a non-empty string")

    src_field = raw.get("source")
    if not isinstance(src_field, str) or not src_field:
        raise InteriorParameterError(source, None, "source", "must be a non-empty string")

    compartments_raw = raw.get("compartments")
    if not isinstance(compartments_raw, list) or not compartments_raw:
        raise InteriorParameterError(source, None, "compartments", "must be a non-empty list")

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


def _parse_compartment_entry(entry: Any, source: str, seen_names: set[str]) -> CompartmentSpec:
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
        raise InteriorParameterError(source, name, "name", "duplicate compartment name")

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
        raise InteriorParameterError(source, name, "description", "must be a string if provided")

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


def _parse_dimensions(raw: Any, source: str, compartment_name: str) -> Dimensions3D:
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
    spec: CompartmentSpec, hull: Hull, source: str, headroom_budget_m: float = 1.5
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
    # Headroom above sheer covers the cabin trunk (standard) or the taller DS
    # enclosed deckhouse (ds). Budget defaults to 1.5 m so "standard" is unchanged.
    if spec.position.z + spec.dimensions.height > hp.sheer_height_fwd + headroom_budget_m:
        raise InteriorParameterError(
            source,
            spec.name,
            "dimensions.height",
            f"ceiling exceeds headroom ({hp.sheer_height_fwd} + {headroom_budget_m} m)",
        )


def _aabb_intersection_volume(c1: CompartmentSpec, c2: CompartmentSpec) -> float:
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


def _validate_no_overlaps(compartments: tuple[CompartmentSpec, ...], source: str) -> None:
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

    half_w = spec.dimensions.width / 2.0 * _M_TO_MM
    box = Part.makeBox(
        spec.dimensions.length * _M_TO_MM,
        spec.dimensions.width * _M_TO_MM,
        spec.dimensions.height * _M_TO_MM,
    )
    box.translate(
        FreeCAD.Vector(
            spec.position.x * _M_TO_MM, -half_w, spec.position.z * _M_TO_MM
        )
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
# Spec 012 — furniture builders (Part::Feature B-rep, matching _build_compartment)
#
# Coordinate convention (spec 017): geometry is built at millimetre scale, the
# FreeCAD internal unit, consistent with the hull. Furniture parameters are
# already in mm and are used at face value; layout values derived from the
# spec (metre-space) are converted via `_M_TO_MM`; fixed real-world
# measurements embedded below are written at millimetre scale.
# ---------------------------------------------------------------------------

# spec 013: furniture now applies to all five canonical layouts (spec 012
# enabled Alt1/Alt2). Reuse _CANONICAL_LAYOUT_NAMES so the two cannot drift.
# Custom (non-canonical) YAML layouts keep boxy placeholders. The per-type
# dispatch skips absent compartment types (Alternativ5 has no galley).
_FURNISHED_LAYOUTS: frozenset[str] = _CANONICAL_LAYOUT_NAMES | {_DS_LAYOUT_NAME}


def _box(target_doc: Any, added: list[Any], name: str, origin: Any, size: tuple[float, float, float]) -> Any:
    """Make a Part::Feature box at `origin` with `size` (millimetre-magnitude units)."""
    import Part

    dx, dy, dz = size
    shape = Part.makeBox(dx, dy, dz)
    shape.translate(origin)
    obj = target_doc.addObject("Part::Feature", name)
    obj.Shape = shape
    added.append(obj)
    return obj


def _validate_furniture_envelope(
    spec: CompartmentSpec, furniture: FurnitureParameters, source: str
) -> None:
    """Reject furniture taller than its compartment (FR-006)."""
    # Validation stays in metre-space: compartment height `h` is in metres, so
    # furniture heights (mm) are converted down via `/ _M_TO_MM` for comparison.
    h = spec.dimensions.height
    if spec.compartment_type == "forward_cabin" and furniture.berth.base_height / _M_TO_MM >= h:
        raise InteriorParameterError(
            source, spec.name, "berth_base_height", "must be less than compartment height"
        )
    if spec.compartment_type == "galley" and furniture.galley.counter_height / _M_TO_MM >= h:
        raise InteriorParameterError(
            source, spec.name, "galley_counter_height", "must be less than compartment height"
        )


def _build_berth(
    spec: CompartmentSpec, params: BerthParameters, label: str, target_doc: Any, added: list[Any]
) -> list[Any]:
    """forward_cabin → a berth base box + cushion box(es) on top."""
    import FreeCAD

    inset = params.wall_inset
    base_h = params.base_height
    cush_t = params.cushion_thickness
    length = spec.dimensions.length * _M_TO_MM - 2 * inset
    width = spec.dimensions.width * _M_TO_MM - 2 * inset
    x0 = spec.position.x * _M_TO_MM + inset
    z0 = spec.position.z * _M_TO_MM
    bodies = [
        _box(
            target_doc, added, f"{label}_Berth",
            FreeCAD.Vector(x0, -width / 2.0, z0), (length, width, base_h),
        )
    ]
    for i in range(params.cushion_count):
        bodies.append(
            _box(
                target_doc, added, f"{label}_Cushion_{i + 1}",
                FreeCAD.Vector(x0, -width / 2.0, z0 + base_h), (length, width, cush_t),
            )
        )
    return bodies


def _build_galley_counter(
    spec: CompartmentSpec, params: GalleyParameters, label: str, target_doc: Any, added: list[Any]
) -> list[Any]:
    """galley → a worktop box with blind sink + stove recesses (Part.Cut)."""
    import FreeCAD
    import Part

    inset = 0.05 * _M_TO_MM
    counter_h = params.counter_height
    thick = params.counter_thickness
    length = spec.dimensions.length * _M_TO_MM - 2 * inset
    width = spec.dimensions.width * _M_TO_MM - 2 * inset
    x0 = spec.position.x * _M_TO_MM + inset
    z0 = spec.position.z * _M_TO_MM + counter_h - thick
    counter = Part.makeBox(length, width, thick)
    counter.translate(FreeCAD.Vector(x0, -width / 2.0, z0))

    if params.cutouts_enabled:
        sink_d = params.sink_recess_depth
        stove_d = params.stove_recess_depth
        cut_l, cut_w = length * 0.25, width * 0.4
        top_z = z0 + thick
        # Sink recess in the forward quarter; stove recess in the aft quarter.
        sink = Part.makeBox(cut_l, cut_w, sink_d)
        sink.translate(FreeCAD.Vector(x0 + length * 0.1, -cut_w / 2.0, top_z - sink_d))
        stove = Part.makeBox(cut_l, cut_w, stove_d)
        stove.translate(FreeCAD.Vector(x0 + length * 0.6, -cut_w / 2.0, top_z - stove_d))
        counter = counter.cut(sink).cut(stove)

    obj = target_doc.addObject("Part::Feature", f"{label}_GalleyCounter")
    obj.Shape = counter
    added.append(obj)
    return [obj]


def _build_head_fittings(
    spec: CompartmentSpec, params: HeadParameters, label: str, target_doc: Any, added: list[Any]
) -> list[Any]:
    """head → a toilet box + a sink box against the walls."""
    import FreeCAD

    toilet_h = params.toilet_height
    sink_h = params.sink_height
    tl, tw = 0.5 * _M_TO_MM, 0.4 * _M_TO_MM
    sl, sw, st = 0.4 * _M_TO_MM, 0.3 * _M_TO_MM, 0.15 * _M_TO_MM
    x0, z0 = spec.position.x * _M_TO_MM, spec.position.z * _M_TO_MM
    aft_x = (spec.position.x + spec.dimensions.length) * _M_TO_MM
    half_w = spec.dimensions.width / 2.0 * _M_TO_MM
    wall_gap = 0.1 * _M_TO_MM
    return [
        _box(
            target_doc, added, f"{label}_Toilet",
            FreeCAD.Vector(x0 + wall_gap, -tw / 2.0, z0), (tl, tw, toilet_h),
        ),
        _box(
            target_doc, added, f"{label}_Sink",
            FreeCAD.Vector(aft_x - wall_gap - sl, half_w - sw, z0 + sink_h - st), (sl, sw, st),
        ),
    ]


def _build_salon_furniture(
    spec: CompartmentSpec, params: SalonParameters, label: str, target_doc: Any, added: list[Any]
) -> list[Any]:
    """salon → a settee box + a table (top + pedestal)."""
    import FreeCAD

    seat_h = params.seat_height
    table_h = params.table_height
    x0, z0 = spec.position.x * _M_TO_MM, spec.position.z * _M_TO_MM
    width = spec.dimensions.width * _M_TO_MM
    length = spec.dimensions.length * _M_TO_MM
    end_gap = 0.1 * _M_TO_MM
    side_gap = 0.05 * _M_TO_MM
    settee_d = 0.5 * _M_TO_MM
    settee = _box(
        target_doc, added, f"{label}_Settee",
        FreeCAD.Vector(x0 + end_gap, -width / 2.0 + side_gap, z0),
        (length - 2 * end_gap, settee_d, seat_h),
    )
    table_top_t = 0.04 * _M_TO_MM
    table_l, table_w = length * 0.4, width * 0.4
    cx = x0 + length / 2.0
    table_top = _box(
        target_doc, added, f"{label}_TableTop",
        FreeCAD.Vector(cx - table_l / 2.0, -table_w / 2.0, z0 + table_h - table_top_t),
        (table_l, table_w, table_top_t),
    )
    half_ped = 0.04 * _M_TO_MM
    ped_side = 0.08 * _M_TO_MM
    pedestal = _box(
        target_doc, added, f"{label}_TablePedestal",
        FreeCAD.Vector(cx - half_ped, -half_ped, z0),
        (ped_side, ped_side, table_h - table_top_t),
    )
    return [settee, table_top, pedestal]


def _build_helm(
    spec: CompartmentSpec, params: HelmParameters, label: str, target_doc: Any, added: list[Any]
) -> list[Any]:
    """helm → a forward console box + a helm seat box (DS enclosed saloon)."""
    import FreeCAD

    x0, z0 = spec.position.x * _M_TO_MM, spec.position.z * _M_TO_MM
    width = spec.dimensions.width * _M_TO_MM
    side_gap = 0.05 * _M_TO_MM
    # Console: a forward dash spanning the width.
    console = _box(
        target_doc, added, f"{label}_HelmConsole",
        FreeCAD.Vector(x0 + side_gap, -width / 2.0 + side_gap, z0),
        (params.console_depth, width - 2 * side_gap, params.console_height),
    )
    # Helm seat: a seat box just aft of the console, offset to the helm side.
    seat_l = 0.5 * _M_TO_MM
    seat_w = 0.5 * _M_TO_MM
    seat = _box(
        target_doc, added, f"{label}_HelmSeat",
        FreeCAD.Vector(
            x0 + params.console_depth + side_gap + 0.1 * _M_TO_MM,
            -width / 2.0 + side_gap,
            z0,
        ),
        (seat_l, seat_w, params.seat_height),
    )
    return [console, seat]


def _build_bulkhead(
    spec: CompartmentSpec, params: BulkheadParameters, label: str, target_doc: Any, added: list[Any]
) -> Any:
    """A thin partition box at the compartment's aft boundary."""
    import FreeCAD

    thick = params.thickness
    aft_x = (spec.position.x + spec.dimensions.length) * _M_TO_MM - thick
    width = spec.dimensions.width * _M_TO_MM
    height = spec.dimensions.height * _M_TO_MM
    return _box(
        target_doc, added, f"{label}_Bulkhead",
        FreeCAD.Vector(aft_x, -width / 2.0, spec.position.z * _M_TO_MM), (thick, width, height),
    )


def _build_furnished_compartment(
    spec: CompartmentSpec,
    layout_name: str,
    furniture: FurnitureParameters,
    target_doc: Any,
    added: list[Any],
) -> Compartment:
    """Build type-keyed furniture for one compartment, wrapped as a compound."""
    import Part

    label = _compartment_label(spec, layout_name)
    local_added: list[Any] = []
    pieces: list[Any]
    if spec.compartment_type == "forward_cabin":
        pieces = _build_berth(spec, furniture.berth, label, target_doc, local_added)
    elif spec.compartment_type == "galley":
        pieces = _build_galley_counter(spec, furniture.galley, label, target_doc, local_added)
    elif spec.compartment_type == "head":
        pieces = _build_head_fittings(spec, furniture.head, label, target_doc, local_added)
    elif spec.compartment_type == "salon":
        pieces = _build_salon_furniture(spec, furniture.salon, label, target_doc, local_added)
    elif spec.compartment_type == "helm":
        pieces = _build_helm(spec, furniture.helm, label, target_doc, local_added)
    else:  # pragma: no cover - guarded by _COMPARTMENT_TYPES at parse time
        pieces = []
    pieces.append(_build_bulkhead(spec, furniture.bulkhead, label, target_doc, local_added))

    target_doc.recompute()

    # Galley counter manifold guard (FR-007): the cut worktop must stay a
    # single closed solid.
    if spec.compartment_type == "galley":
        counter_shape = pieces[0].Shape
        if len(counter_shape.Solids) != 1 or not counter_shape.isValid():
            raise InteriorConstructionError(
                f"galley counter in {spec.name} is non-manifold after recess cuts "
                f"(solids={len(counter_shape.Solids)}, valid={counter_shape.isValid()})",
                layout_name=layout_name,
            )

    compound_obj = target_doc.addObject("Part::Feature", label)
    compound_obj.Shape = Part.makeCompound([p.Shape for p in pieces])
    local_added.append(compound_obj)
    added.extend(local_added)
    return Compartment(
        spec=spec, body=compound_obj, furniture=tuple(pieces), is_furnished=True
    )


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------


def build_interior(
    hull: Hull,
    deck: Deck,
    layout: str = "Alternativ3",
    *,
    parameters_furniture: FurnitureParameters | None = None,
    document: Any = None,
    name: str | None = None,
    apply_render_attributes: bool = True,
    superstructure_variant: Literal["standard", "ds"] = "standard",
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

    # spec 023 — the DS variant builds the bundled enclosed-saloon layout with a
    # taller standing-headroom budget; "standard" is unchanged (1.5 m).
    if superstructure_variant == "ds":
        layout = _DS_LAYOUT_NAME
        headroom_budget_m = 2.5
    else:
        headroom_budget_m = 1.5

    resolved_source, raw_layout = _load_layout(layout)
    layout_spec = _validate_layout_schema(raw_layout, resolved_source)

    _validate_hull(hull)
    _validate_deck(deck, hull)

    for spec in layout_spec.compartments:
        _validate_compartment_in_envelope(spec, hull, resolved_source, headroom_budget_m)
    _validate_no_overlaps(layout_spec.compartments, resolved_source)

    # spec 012 — resolve furniture; gate detailed furniture to Alt1/Alt2.
    furniture = parameters_furniture if parameters_furniture is not None else FurnitureParameters()
    furnished = layout_spec.layout_name in _FURNISHED_LAYOUTS
    if furnished:
        for spec in layout_spec.compartments:
            _validate_furniture_envelope(spec, furniture, resolved_source)

    target_doc = _resolve_document(hull, document)
    resolved_label = name if name is not None else f"Interior_{layout_spec.layout_name}"

    started = time.perf_counter()
    added: list[Any] = []
    try:
        compartments: list[Compartment] = []
        for spec in layout_spec.compartments:
            if furnished:
                compartment = _build_furnished_compartment(
                    spec, layout_spec.layout_name, furniture, target_doc, added
                )
            else:
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
            f"build_interior failed during compartment construction — {type(exc).__name__}: {exc}",
            layout_name=layout_spec.layout_name,
            hull=hull,
            deck=deck,
            underlying=exc,
        ) from exc

    # spec 015 — cosmetic render attributes: compartment compounds read as teak
    # joinery (trim). Geometry committed → outside the rollback try-block.
    from storebro.render import apply_render_attributes as _apply_render_attributes

    _apply_render_attributes(
        [c.body for c in compartments], enabled=apply_render_attributes
    )

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
