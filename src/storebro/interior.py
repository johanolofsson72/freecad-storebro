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
    # spec 024 — contoured + fabric-detailed cushions.
    contoured: bool = True
    cushion_segments: int = 2
    seam_gap: float = 15.0
    cushion_fillet: float = 25.0
    buttons_per_row: int = 4
    button_rows: int = 2
    button_radius: float = 35.0
    piping: bool = True
    piping_radius: float = 12.0
    fold_creases: int = 2

    def __post_init__(self) -> None:
        for name, value in (
            ("berth_base_height", self.base_height),
            ("berth_cushion_thickness", self.cushion_thickness),
            ("berth_cushion_fillet", self.cushion_fillet),
            ("berth_button_radius", self.button_radius),
            ("berth_piping_radius", self.piping_radius),
        ):
            if value <= 0:
                raise _furniture_error(name, "must be > 0")
        if self.cushion_count < 0:
            raise _furniture_error("berth_cushion_count", "must be >= 0")
        if self.wall_inset < 0:
            raise _furniture_error("berth_wall_inset", "must be >= 0")
        if self.cushion_segments < 1:
            raise _furniture_error("berth_cushion_segments", "must be >= 1")
        for name, value in (
            ("berth_seam_gap", self.seam_gap),
            ("berth_buttons_per_row", float(self.buttons_per_row)),
            ("berth_button_rows", float(self.button_rows)),
            ("berth_fold_creases", float(self.fold_creases)),
        ):
            if value < 0:
                raise _furniture_error(name, "must be >= 0")


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
    # spec 024 — rounded worktop edges + a forward appliance fascia.
    contoured: bool = True
    edge_fillet: float = 12.0
    fascia: bool = True
    fascia_thickness: float = 18.0

    def __post_init__(self) -> None:
        for name, value in (
            ("galley_counter_height", self.counter_height),
            ("galley_counter_thickness", self.counter_thickness),
            ("galley_sink_recess_depth", self.sink_recess_depth),
            ("galley_stove_recess_depth", self.stove_recess_depth),
            ("galley_edge_fillet", self.edge_fillet),
            ("galley_fascia_thickness", self.fascia_thickness),
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
    # spec 024 — contoured toilet (rounded pedestal + bowl) + faucet.
    contoured: bool = True
    toilet_fillet: float = 30.0
    bowl_radius: float = 170.0
    faucet: bool = True
    faucet_height: float = 200.0

    def __post_init__(self) -> None:
        for name, value in (
            ("head_toilet_height", self.toilet_height),
            ("head_sink_height", self.sink_height),
            ("head_toilet_fillet", self.toilet_fillet),
            ("head_bowl_radius", self.bowl_radius),
            ("head_faucet_height", self.faucet_height),
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
    # spec 024 — contoured + fabric-detailed settee.
    contoured: bool = True
    seat_fillet: float = 25.0
    buttons_per_row: int = 6
    button_rows: int = 1
    button_radius: float = 35.0
    piping: bool = True
    piping_radius: float = 12.0
    fold_creases: int = 2

    def __post_init__(self) -> None:
        for name, value in (
            ("salon_seat_height", self.seat_height),
            ("salon_table_height", self.table_height),
            ("salon_seat_fillet", self.seat_fillet),
            ("salon_button_radius", self.button_radius),
            ("salon_piping_radius", self.piping_radius),
        ):
            if value <= 0:
                raise _furniture_error(name, "must be > 0")
        for name, value in (
            ("salon_buttons_per_row", float(self.buttons_per_row)),
            ("salon_button_rows", float(self.button_rows)),
            ("salon_fold_creases", float(self.fold_creases)),
        ):
            if value < 0:
                raise _furniture_error(name, "must be >= 0")


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
    # spec 024 — rounded corners + a rounded-top doorway.
    contoured: bool = True
    corner_fillet: float = 40.0
    doorway: bool = True
    doorway_width: float = 600.0
    doorway_height: float = 1500.0

    def __post_init__(self) -> None:
        for name, value in (
            ("bulkhead_thickness", self.thickness),
            ("bulkhead_corner_fillet", self.corner_fillet),
            ("bulkhead_doorway_width", self.doorway_width),
            ("bulkhead_doorway_height", self.doorway_height),
        ):
            if value <= 0:
                raise _furniture_error(name, "must be > 0")


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


# ---------------------------------------------------------------------------
# spec 024 — contour helpers (Part B-rep on Part::Feature furniture).
#
# A spike proved every op manifold AND byte-reproducible (filleted/cut/fused
# volumes are identical across builds — no spec 022 arc-loft trouble), so these
# are safe for constitution II. Each contoured piece carries a manifold-or-box
# fallback gate (FR-007).
# ---------------------------------------------------------------------------


def _box_shape(origin: Any, size: tuple[float, float, float]) -> Any:
    """A translated Part box shape (no document object)."""
    import Part

    dx, dy, dz = size
    s = Part.makeBox(dx, dy, dz)
    s.translate(origin)
    return s


def _rounded_box_shape(
    origin: Any, size: tuple[float, float, float], radius: float, *, vertical_only: bool = False
) -> Any:
    """A box with filleted edges (clamped radius; falls back to the plain box).

    ``vertical_only`` rounds just the four Z-parallel edges (e.g. bulkhead
    corners); otherwise all edges are rounded (a soft cushion/pad).
    """
    s = _box_shape(origin, size)
    dx, dy, dz = size
    rr = min(radius, dx / 2.1, dy / 2.1, dz / 2.1)
    if rr <= 0:
        return s
    if vertical_only:
        edges = [
            e
            for e in s.Edges
            if len(e.Vertexes) == 2 and abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 1e-6
        ]
        rr = min(radius, dx / 2.1, dy / 2.1)
    else:
        edges = list(s.Edges)
    try:
        filleted = s.makeFillet(rr, edges)
        if len(filleted.Solids) == 1 and filleted.isValid():
            return filleted
    except Exception:
        pass
    return s


def _cushion_shape(origin: Any, size: tuple[float, float, float], fab: Any) -> Any:
    """A fabric-detailed cushion: rounded box + tufting buttons (cut spheres) +
    piping welt (fused frame) + fold creases (cut grooves).

    ``fab`` supplies ``cushion_fillet``/``button_*``/``piping*``/``fold_creases``
    (the berth or salon params). Returns a single-solid shape; on any failure or
    a non-single-solid result, returns the plain box (FR-007, deterministic).
    """
    import FreeCAD
    import Part

    dx, dy, dz = size
    ox, oy, oz = origin.x, origin.y, origin.z
    fillet = float(getattr(fab, "cushion_fillet", 0.0) or getattr(fab, "seat_fillet", 20.0))
    base = _rounded_box_shape(origin, size, fillet)
    try:
        shape = base
        top_z = oz + dz
        # Tufting buttons — a grid of shallow cut-sphere dimples on the top face.
        cols = max(0, int(getattr(fab, "buttons_per_row", 0)))
        rows = max(0, int(getattr(fab, "button_rows", 0)))
        br = float(getattr(fab, "button_radius", 0.0))
        depth = min(br * 0.55, dz * 0.4)
        for i in range(cols):
            for j in range(rows):
                bx = ox + dx * (i + 0.5) / cols
                by = oy + dy * (j + 0.5) / rows
                sph = Part.makeSphere(br)
                sph.translate(FreeCAD.Vector(bx, by, top_z + br - depth))
                shape = shape.cut(sph)
        # Piping welt — a thin raised rounded frame around the top perimeter.
        if getattr(fab, "piping", False):
            pr = float(getattr(fab, "piping_radius", 0.0))
            inset = pr * 2.0
            if dx > 4 * inset and dy > 4 * inset:
                outer = Part.makeBox(dx - 2 * inset + 2 * pr, dy - 2 * inset + 2 * pr, pr)
                inner = Part.makeBox(dx - 2 * inset, dy - 2 * inset, pr * 2)
                outer.translate(FreeCAD.Vector(ox + inset - pr, oy + inset - pr, top_z - pr * 0.3))
                inner.translate(FreeCAD.Vector(ox + inset, oy + inset, top_z - pr))
                shape = shape.fuse(outer.cut(inner))
        # Fold creases — shallow grooves cut across the top.
        folds = max(0, int(getattr(fab, "fold_creases", 0)))
        for k in range(folds):
            gx = ox + dx * (k + 1) / (folds + 1)
            groove = Part.makeBox(8.0, dy * 0.7, 10.0)
            groove.translate(FreeCAD.Vector(gx - 4.0, oy + dy * 0.15, top_z - 6.0))
            shape = shape.cut(groove)
        if len(shape.Solids) == 1 and shape.isValid():
            return shape
    except Exception:
        pass
    return _box_shape(origin, size)


def _finalize_piece(
    target_doc: Any,
    added: list[Any],
    name: str,
    shape: Any,
    fallback: tuple[Any, tuple[float, float, float]],
) -> Any:
    """Wrap a contour shape as a Part::Feature, falling back to a box if the
    shape is not a single valid solid (FR-007, manifold-or-box gate)."""
    if shape is None or len(shape.Solids) != 1 or not shape.isValid():
        shape = _box_shape(fallback[0], fallback[1])
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
    """forward_cabin → a berth base + cushion(s).

    spec 024: when ``contoured`` the cushion slab is split into
    ``cushion_segments`` fabric-detailed sub-cushions (rounded + tufting buttons
    + piping + fold creases) separated by seam gaps; else the spec 012 boxes.
    """
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
    if not params.contoured:
        for i in range(params.cushion_count):
            bodies.append(
                _box(
                    target_doc, added, f"{label}_Cushion_{i + 1}",
                    FreeCAD.Vector(x0, -width / 2.0, z0 + base_h), (length, width, cush_t),
                )
            )
        return bodies
    # Contoured: per cushion layer, split into segmented sub-cushions.
    seg = max(1, params.cushion_segments)
    gap = params.seam_gap
    seg_len = (length - (seg - 1) * gap) / seg
    seq = 0
    for _layer in range(params.cushion_count):
        for s in range(seg):
            seq += 1
            sx = x0 + s * (seg_len + gap)
            origin = FreeCAD.Vector(sx, -width / 2.0, z0 + base_h)
            shape = _cushion_shape(origin, (seg_len, width, cush_t), params)
            bodies.append(
                _finalize_piece(
                    target_doc, added, f"{label}_Cushion_{seq}", shape,
                    (origin, (seg_len, width, cush_t)),
                )
            )
    return bodies


def _build_galley_counter(
    spec: CompartmentSpec, params: GalleyParameters, label: str, target_doc: Any, added: list[Any]
) -> list[Any]:
    """galley → a worktop box with blind sink + stove recesses (Part.Cut).

    spec 024: when ``contoured`` the worktop outer corners are rounded and a
    forward fascia panel is fused under the front edge — kept a single valid
    solid (the spec 012 manifold guard); on failure it falls back to the plain
    worktop.
    """
    import FreeCAD
    import Part

    inset = 0.05 * _M_TO_MM
    counter_h = params.counter_height
    thick = params.counter_thickness
    length = spec.dimensions.length * _M_TO_MM - 2 * inset
    width = spec.dimensions.width * _M_TO_MM - 2 * inset
    x0 = spec.position.x * _M_TO_MM + inset
    z0 = spec.position.z * _M_TO_MM + counter_h - thick

    def _make_counter(*, contour: bool) -> Any:
        c = Part.makeBox(length, width, thick)
        c.translate(FreeCAD.Vector(x0, -width / 2.0, z0))
        if contour:
            # Round the four outer vertical corner edges before cutting recesses.
            rr = min(params.edge_fillet, width / 2.1, length / 2.1)
            corners = [
                e
                for e in c.Edges
                if len(e.Vertexes) == 2
                and abs(e.Vertexes[0].Z - e.Vertexes[1].Z) > 1e-6
            ]
            with contextlib.suppress(Exception):
                c = c.makeFillet(rr, corners)
        if params.cutouts_enabled:
            sink_d = params.sink_recess_depth
            stove_d = params.stove_recess_depth
            cut_l, cut_w = length * 0.25, width * 0.4
            top_z = z0 + thick
            sink = Part.makeBox(cut_l, cut_w, sink_d)
            sink.translate(FreeCAD.Vector(x0 + length * 0.1, -cut_w / 2.0, top_z - sink_d))
            stove = Part.makeBox(cut_l, cut_w, stove_d)
            stove.translate(FreeCAD.Vector(x0 + length * 0.6, -cut_w / 2.0, top_z - stove_d))
            c = c.cut(sink).cut(stove)
        if contour and params.fascia:
            # A fascia panel hanging under the front edge, overlapping the worktop.
            fascia = Part.makeBox(length, params.fascia_thickness, counter_h * 0.18)
            fascia.translate(
                FreeCAD.Vector(x0, -width / 2.0, z0 - counter_h * 0.18 + thick * 0.4)
            )
            c = c.fuse(fascia)
        return c

    counter = _make_counter(contour=params.contoured)
    if params.contoured and (len(counter.Solids) != 1 or not counter.isValid()):
        counter = _make_counter(contour=False)  # manifold-or-fallback gate

    obj = target_doc.addObject("Part::Feature", f"{label}_GalleyCounter")
    obj.Shape = counter
    added.append(obj)
    return [obj]


def _build_head_fittings(
    spec: CompartmentSpec, params: HeadParameters, label: str, target_doc: Any, added: list[Any]
) -> list[Any]:
    """head → a toilet + a sink against the walls.

    spec 024: when ``contoured`` the toilet is a rounded pedestal fused with a
    bowl and the sink gains a faucet (stem + spout); else the spec 012 boxes.
    """
    import FreeCAD
    import Part

    toilet_h = params.toilet_height
    sink_h = params.sink_height
    tl, tw = 0.5 * _M_TO_MM, 0.4 * _M_TO_MM
    sl, sw, st = 0.4 * _M_TO_MM, 0.3 * _M_TO_MM, 0.15 * _M_TO_MM
    x0, z0 = spec.position.x * _M_TO_MM, spec.position.z * _M_TO_MM
    aft_x = (spec.position.x + spec.dimensions.length) * _M_TO_MM
    half_w = spec.dimensions.width / 2.0 * _M_TO_MM
    wall_gap = 0.1 * _M_TO_MM
    toilet_origin = FreeCAD.Vector(x0 + wall_gap, -tw / 2.0, z0)
    sink_origin = FreeCAD.Vector(aft_x - wall_gap - sl, half_w - sw, z0 + sink_h - st)

    if not params.contoured:
        return [
            _box(target_doc, added, f"{label}_Toilet", toilet_origin, (tl, tw, toilet_h)),
            _box(target_doc, added, f"{label}_Sink", sink_origin, (sl, sw, st)),
        ]

    bodies: list[Any] = []
    # Toilet: rounded pedestal fused with a bowl cylinder on top.
    toilet_shape = None
    try:
        ped = _rounded_box_shape(toilet_origin, (tl, tw, toilet_h), params.toilet_fillet)
        br = min(params.bowl_radius, tl / 2.1, tw / 2.1)
        bowl = Part.makeCylinder(br, br * 0.7)
        bowl.translate(FreeCAD.Vector(x0 + wall_gap + tl / 2.0, 0.0, z0 + toilet_h))
        fused = ped.fuse(bowl)
        if len(fused.Solids) == 1 and fused.isValid():
            toilet_shape = fused
    except Exception:
        toilet_shape = None
    bodies.append(
        _finalize_piece(
            target_doc, added, f"{label}_Toilet", toilet_shape, (toilet_origin, (tl, tw, toilet_h))
        )
    )
    # Sink + faucet (stem + spout). The sink stays a box; the faucet is its own
    # small fitting (a fused stem+spout, or two pieces if they don't merge).
    bodies.append(_box(target_doc, added, f"{label}_Sink", sink_origin, (sl, sw, st)))
    if params.faucet:
        try:
            fx = aft_x - wall_gap - sl * 0.7
            fy = half_w - sw * 0.5
            fz = z0 + sink_h
            stem = Part.makeCylinder(15.0, params.faucet_height)
            stem.translate(FreeCAD.Vector(fx, fy, fz))
            spout = Part.makeCylinder(10.0, params.faucet_height * 0.6)
            spout.rotate(FreeCAD.Vector(fx, fy, fz + params.faucet_height), FreeCAD.Vector(0, 1, 0), 55)
            faucet = stem.fuse(spout)
            obj = target_doc.addObject("Part::Feature", f"{label}_Faucet")
            obj.Shape = faucet
            added.append(obj)
            bodies.append(obj)
        except Exception:
            pass
    return bodies


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
    settee_origin = FreeCAD.Vector(x0 + end_gap, -width / 2.0 + side_gap, z0)
    settee_size = (length - 2 * end_gap, settee_d, seat_h)
    if params.contoured:
        settee = _finalize_piece(
            target_doc, added, f"{label}_Settee",
            _cushion_shape(settee_origin, settee_size, params),
            (settee_origin, settee_size),
        )
    else:
        settee = _box(target_doc, added, f"{label}_Settee", settee_origin, settee_size)
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
    """A thin partition at the compartment's aft boundary.

    spec 024: when ``contoured`` the panel has rounded vertical corners and,
    where it is tall/wide enough, a rounded-top doorway opening; else the spec
    012 plain box. Kept a single valid solid (manifold-or-box fallback).
    """
    import FreeCAD
    import Part

    thick = params.thickness
    aft_x = (spec.position.x + spec.dimensions.length) * _M_TO_MM - thick
    width = spec.dimensions.width * _M_TO_MM
    height = spec.dimensions.height * _M_TO_MM
    z0 = spec.position.z * _M_TO_MM
    origin = FreeCAD.Vector(aft_x, -width / 2.0, z0)
    size = (thick, width, height)

    if not params.contoured:
        return _box(target_doc, added, f"{label}_Bulkhead", origin, size)

    shape = None
    try:
        panel = _rounded_box_shape(origin, size, params.corner_fillet, vertical_only=True)
        dw = params.doorway_width
        dh = params.doorway_height
        if params.doorway and dw < width * 0.85 and dh < height * 0.92:
            # Doorway: a through-X opening (rectangle + a half-cylinder arch top).
            door = Part.makeBox(thick * 3.0, dw, dh)
            door.translate(FreeCAD.Vector(aft_x - thick, -dw / 2.0, z0))
            arch = Part.makeCylinder(dw / 2.0, thick * 3.0)
            arch.rotate(FreeCAD.Vector(0, 0, 0), FreeCAD.Vector(0, 1, 0), 90)
            arch.translate(FreeCAD.Vector(aft_x - thick, 0.0, z0 + dh))
            panel = panel.cut(door.fuse(arch))
        if len(panel.Solids) == 1 and panel.isValid():
            shape = panel
    except Exception:
        shape = None
    return _finalize_piece(target_doc, added, f"{label}_Bulkhead", shape, (origin, size))


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
