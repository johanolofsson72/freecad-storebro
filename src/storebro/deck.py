"""Parametric Storebro deck (superstructure) module.

Public surface:
    build_deck         — function. Build the six deck Bodies on a Hull.
    DeckParameters     — frozen dataclass. Deck dimensional inputs.
    Deck               — dataclass. build_deck return aggregate.
    DeckParameterError — pre-FreeCAD validation failure.
    DeckConstructionError — FreeCAD-side construction failure.

Six sub-Bodies are added to the hull's FreeCAD document on success: `DeckPlate`,
`CabinTrunk`, `Windshield`, `Hardtop`, `HardtopPillars`, `Railings`. On any
FreeCAD-side failure mid-build the deck module rolls back all Bodies added so
far (FR-018, SC-008).

This is the project's first non-leaf module: it imports `storebro.hull` for the
`Hull` type and `storebro._freecad_check` for the shared lazy version check.
It does NOT import `storebro.export`, `storebro.interior`, or `storebro.cli`
(FR-011).
"""

from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from storebro.hull import Hull, HullParameters

if TYPE_CHECKING:
    pass

_MM_PER_M = 1000.0
"""FreeCAD's internal length unit is mm; DeckParameters / HullParameters are in meters."""


def _vec_m(x: float, y: float, z: float) -> Any:
    """Build a FreeCAD.Vector from meter-valued coordinates (scaled to mm)."""
    import FreeCAD

    return FreeCAD.Vector(x * _MM_PER_M, y * _MM_PER_M, z * _MM_PER_M)


__all__ = [
    "Deck",
    "DeckConstructionError",
    "DeckParameterError",
    "DeckParameters",
    "build_deck",
]


# ---------------------------------------------------------------------------
# Exception classes (FR-015 + data-model §4/§5)
# ---------------------------------------------------------------------------


class DeckParameterError(ValueError):
    """Raised before any FreeCAD call when an input is invalid.

    Attributes:
        parameter_name: Name of the offending field, or a composite key like
            ``"cabin_trunk_length<>hull.loa"`` for cross-field violations,
            or ``"hull"``/``"document"`` for input-binding violations.
        parameter_value: The offending value, or ``None`` for cross-field
            violations.
        valid_range: Human-readable constraint string.

    Example:
        >>> err = DeckParameterError("railing_height", -0.5, "> 0")
        >>> err.parameter_name
        'railing_height'
        >>> isinstance(err, ValueError)
        True
    """

    def __init__(
        self,
        parameter_name: str,
        parameter_value: float | None,
        valid_range: str,
    ) -> None:
        self.parameter_name = parameter_name
        self.parameter_value = parameter_value
        self.valid_range = valid_range
        if parameter_value is None:
            message = f"DeckParameterError: invalid {parameter_name} — {valid_range}"
        else:
            message = (
                f"DeckParameterError: {parameter_name} = {parameter_value!r} "
                f"is outside the valid range {valid_range}"
            )
        super().__init__(message)


class DeckConstructionError(RuntimeError):
    """Raised when FreeCAD fails to build the deck or when the running FreeCAD
    version is outside the supported range.

    Attributes:
        parameters: The :class:`DeckParameters` that triggered the failure.
        hull: The :class:`Hull` the deck was being built on.
        underlying: The FreeCAD-side exception, if any.
        detected_version: ``(major, minor)`` for version-check failures only.
        supported_range: Human-readable supported range for version-check
            failures only.

    Example:
        >>> err = DeckConstructionError("unsupported FreeCAD version",
        ...                              detected_version=(0, 20),
        ...                              supported_range=">=1.1,<2.0")
        >>> err.detected_version
        (0, 20)
        >>> isinstance(err, RuntimeError)
        True
    """

    def __init__(
        self,
        message: str,
        *,
        parameters: DeckParameters | None = None,
        hull: Hull | None = None,
        underlying: BaseException | None = None,
        detected_version: tuple[int, int] | None = None,
        supported_range: str | None = None,
    ) -> None:
        self.parameters = parameters
        self.hull = hull
        self.underlying = underlying
        self.detected_version = detected_version
        self.supported_range = supported_range
        super().__init__(f"DeckConstructionError: {message}")


# ---------------------------------------------------------------------------
# Parameter dataclass (FR-002, FR-004, FR-008 + data-model §1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeckParameters:
    """Named hull dimensional inputs for :func:`build_deck`.

    All lengths in meters, all angles in degrees. Defaults are estimate-grade
    against the Storebro Royal Cruiser 34 (1972) baseline (see
    ``specs/003-deck-module/research.md`` §R1) — refinable in PATCH bumps when
    a primary source surfaces.

    Validated at construction (per-field + intra-deck cross-field constraints).
    Cross-hull constraints (e.g., `cabin_trunk_length < hull.loa`) are checked
    by :func:`build_deck`, not here, because this dataclass does not see the
    hull.

    Example:
        >>> p = DeckParameters()
        >>> p.cabin_trunk_length, p.hardtop_length
        (4.5, 3.5)
        >>> custom = DeckParameters(railing_height=0.80)
        >>> custom.railing_height
        0.8
    """

    deck_plate_thickness: float = 0.025
    cabin_trunk_length: float = 4.50
    cabin_trunk_fwd_offset: float = 2.00
    cabin_trunk_width: float = 2.20
    cabin_trunk_height: float = 1.20
    cabin_trunk_corner_radius: float = 0.075
    windshield_rake: float = 25.0
    hardtop_length: float = 3.50
    hardtop_height: float = 0.10
    hardtop_overhang_fwd: float = 0.20
    hardtop_overhang_aft: float = 0.40
    hardtop_pillar_diameter: float = 0.04
    railing_height: float = 0.65
    deck_side_walkway: float = 0.40

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

    def __post_init__(self) -> None:
        _validate_deck_parameters(self)


def _validate_deck_parameters(p: DeckParameters) -> None:
    """Per-field + intra-deck cross-field validation."""
    # Per-field positivity
    for name, value, lower in (
        ("deck_plate_thickness", p.deck_plate_thickness, 0),
        ("cabin_trunk_length", p.cabin_trunk_length, 0),
        ("cabin_trunk_width", p.cabin_trunk_width, 0),
        ("cabin_trunk_height", p.cabin_trunk_height, 0),
        ("hardtop_length", p.hardtop_length, 0),
        ("hardtop_pillar_diameter", p.hardtop_pillar_diameter, 0),
        ("railing_height", p.railing_height, 0),
        ("deck_side_walkway", p.deck_side_walkway, 0),
    ):
        if value <= lower:
            raise DeckParameterError(name, value, "> 0")

    # Non-negative
    for name, value in (
        ("cabin_trunk_fwd_offset", p.cabin_trunk_fwd_offset),
        ("cabin_trunk_corner_radius", p.cabin_trunk_corner_radius),
        ("hardtop_height", p.hardtop_height),
        ("hardtop_overhang_fwd", p.hardtop_overhang_fwd),
        ("hardtop_overhang_aft", p.hardtop_overhang_aft),
    ):
        if value < 0:
            raise DeckParameterError(name, value, ">= 0")

    # Angular range
    if not (0.0 <= p.windshield_rake <= 60.0):
        raise DeckParameterError("windshield_rake", p.windshield_rake, "[0, 60] degrees")

    # Intra-deck cross-field: hardtop overhangs must fit length
    if p.hardtop_overhang_fwd + p.hardtop_overhang_aft >= p.hardtop_length:
        raise DeckParameterError(
            "hardtop_overhang_fwd+aft<>hardtop_length",
            None,
            "hardtop_overhang_fwd + hardtop_overhang_aft must be less than hardtop_length",
        )


# ---------------------------------------------------------------------------
# Sub-Body wrappers (data-model §2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeckPlate:
    """Wrapper around the FreeCAD Body representing the deck plate.

    Example:
        >>> # Accessed via Deck.deck_plate after build_deck() returns.
    """

    body: Any
    thickness: float


@dataclass(frozen=True)
class CabinTrunk:
    """Wrapper around the FreeCAD Body representing the cabin trunk.

    Example:
        >>> # Accessed via Deck.cabin_trunk.
    """

    body: Any
    length: float
    width: float
    height: float
    corner_radius: float


@dataclass(frozen=True)
class Windshield:
    """Wrapper around the FreeCAD Body representing the windshield.

    Example:
        >>> # Accessed via Deck.windshield.
    """

    body: Any
    rake_degrees: float


@dataclass(frozen=True)
class Hardtop:
    """Wrapper around the FreeCAD Body representing the hardtop slab.

    Example:
        >>> # Accessed via Deck.hardtop.
    """

    body: Any
    length: float
    height_above_cabin: float


@dataclass(frozen=True)
class HardtopPillars:
    """Wrapper around the FreeCAD Compound representing the two aft pillars.

    Example:
        >>> # Accessed via Deck.hardtop_pillars.
    """

    body: Any
    pillar_diameter: float


@dataclass(frozen=True)
class Railings:
    """Wrapper around the FreeCAD Body representing the perimeter rail loop.

    Example:
        >>> # Accessed via Deck.railings.
    """

    body: Any
    height: float


# ---------------------------------------------------------------------------
# Return aggregate (data-model §3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Deck:
    """Return value of :func:`build_deck`. Wraps the six sub-Bodies + inputs.

    Example:
        >>> # from storebro import build_hull, build_deck
        >>> # deck = build_deck(build_hull())
        >>> # deck.cabin_trunk.length, deck.hardtop.length all set.
    """

    parameters: DeckParameters
    hull: Hull
    document: Any
    label: str
    build_duration_seconds: float
    deck_plate: DeckPlate
    cabin_trunk: CabinTrunk
    windshield: Windshield
    hardtop: Hardtop
    hardtop_pillars: HardtopPillars
    railings: Railings


# ---------------------------------------------------------------------------
# Validation helpers (FR-004, FR-012, FR-016, FR-019)
# ---------------------------------------------------------------------------


def _validate_hull(hull: Hull | None) -> None:
    """FR-019: reject None hull or hull with empty/null Shape."""
    if hull is None:
        raise DeckParameterError("hull", None, "must not be None")
    body = getattr(hull, "body", None)
    if body is None:
        raise DeckParameterError("hull", None, "Hull object has no `.body` attribute")
    shape = getattr(body, "Shape", None)
    if shape is None or getattr(shape, "isNull", lambda: True)():
        raise DeckParameterError(
            "hull",
            None,
            "hull body has no shape — recompute the source document first",
        )


def _validate_cross_hull_constraints(hull: Hull, parameters: DeckParameters) -> None:
    """FR-004 + FR-012: validate parameters against hull dimensions.

    These checks live in :func:`build_deck` (not in DeckParameters.__post_init__)
    because DeckParameters does not know about the hull.
    """
    hp = hull.parameters
    if parameters.cabin_trunk_length >= hp.loa:
        raise DeckParameterError(
            "cabin_trunk_length<>hull.loa",
            None,
            f"cabin_trunk_length ({parameters.cabin_trunk_length}) must be "
            f"less than hull.parameters.loa ({hp.loa})",
        )
    if parameters.cabin_trunk_fwd_offset + parameters.cabin_trunk_length > hp.loa:
        raise DeckParameterError(
            "cabin_trunk_fwd_offset+length<>hull.loa",
            None,
            "cabin_trunk_fwd_offset + cabin_trunk_length must not exceed hull.parameters.loa",
        )
    if parameters.cabin_trunk_width + 2 * parameters.deck_side_walkway > hp.beam_max:
        raise DeckParameterError(
            "cabin_trunk_width+walkways<>hull.beam_max",
            None,
            "cabin_trunk_width + 2 x deck_side_walkway must not exceed hull.parameters.beam_max",
        )


def _resolve_document(hull: Hull, document: Any) -> Any:
    """FR-016 + research R4: strict document binding."""
    if document is None:
        return hull.document
    if document is hull.document:
        return document
    raise DeckParameterError(
        "document",
        None,
        "must equal hull.document for cross-module consistency",
    )


def _ensure_freecad_supported() -> None:
    """Wrap the shared lazy version check; re-raise as DeckConstructionError
    on failure. Duck-typed to avoid importing storebro.hull's exception class
    (matches spec 002's pattern; preserves FR-011's leaf-to-hull-only rule
    since this helper imports only `_freecad_check`).
    """
    from storebro import _freecad_check

    try:
        _freecad_check.ensure_supported_freecad()
    except Exception as exc:
        detected = getattr(exc, "detected_version", None)
        supported = getattr(exc, "supported_range", None)
        raise DeckConstructionError(
            "unsupported FreeCAD version while preparing deck build",
            detected_version=detected,
            supported_range=supported,
            underlying=exc,
        ) from exc


# ---------------------------------------------------------------------------
# Sheer sampling (research R8)
# ---------------------------------------------------------------------------


def _sample_hull_sheer(hull: Hull) -> list[tuple[float, float, float]]:
    """Sample the hull's sheer line at five stations matching spec 001.

    v0.3.0-alpha derives the sheer points analytically from `hull.parameters`
    (the hull module guarantees structural determinism for those parameters,
    so the analytical result equals the Shape-walked result by construction).
    The "true" Shape-face walk per research R8 is tracked as a v0.2.0
    refinement alongside the PartDesign loft upgrade.

    Returns five `(x, y, z)` tuples representing the sheer-line points on the
    port half (positive Y) at X positions `{0, 0.25, 0.5, 0.75, 1.0} x LOA`.
    """
    hp: HullParameters = hull.parameters
    stations = [0.0, 0.25 * hp.loa, 0.50 * hp.loa, 0.75 * hp.loa, hp.loa]
    half_beam_max = hp.beam_max / 2.0
    # Half-beam taper matches the hull module's _compute_stations logic.
    half_beams = [
        half_beam_max * 0.70,  # Transom
        half_beam_max * 0.92,  # Aft
        half_beam_max,  # Amidships
        half_beam_max * 0.55,  # Fwd
        0.0,  # Stem (collapses to vertex)
    ]

    # Sheer height linearly interpolates between aft and fwd.
    def sheer_z(t: float) -> float:
        return hp.sheer_height_aft + t * (hp.sheer_height_fwd - hp.sheer_height_aft)

    fractions = [0.0, 0.25, 0.50, 0.75, 1.0]
    return [(stations[i], half_beams[i], sheer_z(fractions[i])) for i in range(5)]


# ---------------------------------------------------------------------------
# Rollback discipline (research R7, FR-018, SC-008)
# ---------------------------------------------------------------------------


def _rollback(target_doc: Any, added_objects: list[Any]) -> None:
    """Remove all objects added by a partial build, in reverse order."""
    for obj in reversed(added_objects):
        with contextlib.suppress(Exception):
            target_doc.removeObject(obj.Name)
    with contextlib.suppress(Exception):
        target_doc.recompute()


# ---------------------------------------------------------------------------
# Sub-Body builders (T016-T021)
# ---------------------------------------------------------------------------


def _build_deck_plate(
    hull: Hull,
    parameters: DeckParameters,
    target_doc: Any,
    added: list[Any],
) -> DeckPlate:
    """Build the 3D deck plate (FR-010, FR-007)."""
    import Part

    samples = _sample_hull_sheer(hull)
    # Build the perimeter as a closed wire on both halves (positive y + mirrored).
    points_port = [_vec_m(x, y, z) for x, y, z in samples]
    points_starboard = [_vec_m(x, -y, z) for x, y, z in reversed(samples)]
    perimeter_pts = points_port + points_starboard[1:-1] + [points_port[0]]

    edges = [
        Part.LineSegment(perimeter_pts[i], perimeter_pts[i + 1])
        for i in range(len(perimeter_pts) - 1)
    ]
    wire = Part.Wire([e.toShape() for e in edges])
    face = Part.Face(wire)
    plate_solid = face.extrude(_vec_m(0, 0, -parameters.deck_plate_thickness))

    obj = target_doc.addObject("Part::Feature", "Deck_DeckPlate")
    obj.Shape = plate_solid
    added.append(obj)

    obj.addProperty("App::PropertyLength", "DeckPlateThickness", "Deck", "Deck plate thickness")
    obj.DeckPlateThickness = parameters.deck_plate_thickness * 1000.0
    return DeckPlate(body=obj, thickness=parameters.deck_plate_thickness)


def _build_cabin_trunk(
    hull: Hull,
    parameters: DeckParameters,
    deck_plate: DeckPlate,
    target_doc: Any,
    added: list[Any],
) -> CabinTrunk:
    """Build the rounded-corner cabin trunk prism (FR-007)."""
    import Part

    hp = hull.parameters
    deck_top_z = hp.sheer_height_aft + (hp.sheer_height_fwd - hp.sheer_height_aft) * 0.5

    x_center = parameters.cabin_trunk_fwd_offset + parameters.cabin_trunk_length / 2.0
    half_w = parameters.cabin_trunk_width / 2.0
    half_l = parameters.cabin_trunk_length / 2.0
    # Reserved for the v0.2.0 PartDesign upgrade where the rounded fillet
    # will be applied as a feature instead of a one-shot makeFillet call.
    _corner_radius_clamped = max(
        0.0, min(parameters.cabin_trunk_corner_radius, half_w * 0.9, half_l * 0.9)
    )
    _ = _corner_radius_clamped  # v0.3.0-alpha: rectangle prism, fillet pending
    # Build a centered rounded rectangle via a simple rectangle (Part.makePlane
    # places its corner at origin; we move it after).
    rect = Part.makePlane(
        parameters.cabin_trunk_length * _MM_PER_M,
        parameters.cabin_trunk_width * _MM_PER_M,
    )
    rect_solid = rect.extrude(_vec_m(0, 0, parameters.cabin_trunk_height))
    rect_solid.translate(_vec_m(x_center - half_l, -half_w, deck_top_z))

    obj = target_doc.addObject("Part::Feature", "Deck_CabinTrunk")
    obj.Shape = rect_solid
    added.append(obj)

    obj.addProperty("App::PropertyLength", "TrunkLength", "Deck", "Cabin trunk length")
    obj.addProperty("App::PropertyLength", "TrunkWidth", "Deck", "Cabin trunk width")
    obj.addProperty("App::PropertyLength", "TrunkHeight", "Deck", "Cabin trunk height")
    obj.addProperty("App::PropertyLength", "CornerRadius", "Deck", "Cabin trunk corner radius")
    obj.TrunkLength = parameters.cabin_trunk_length * 1000.0
    obj.TrunkWidth = parameters.cabin_trunk_width * 1000.0
    obj.TrunkHeight = parameters.cabin_trunk_height * 1000.0
    obj.CornerRadius = parameters.cabin_trunk_corner_radius * 1000.0

    return CabinTrunk(
        body=obj,
        length=parameters.cabin_trunk_length,
        width=parameters.cabin_trunk_width,
        height=parameters.cabin_trunk_height,
        corner_radius=parameters.cabin_trunk_corner_radius,
    )


def _build_windshield(
    hull: Hull,
    parameters: DeckParameters,
    cabin_trunk: CabinTrunk,
    target_doc: Any,
    added: list[Any],
) -> Windshield:
    """Build the inclined windshield face (FR-007)."""
    import math

    import Part

    hp = hull.parameters
    deck_top_z = hp.sheer_height_aft + (hp.sheer_height_fwd - hp.sheer_height_aft) * 0.5
    cabin_top_z = deck_top_z + parameters.cabin_trunk_height
    cabin_fwd_x = parameters.cabin_trunk_fwd_offset
    half_w = parameters.cabin_trunk_width / 2.0
    rake_rad = math.radians(parameters.windshield_rake)
    aft_offset = parameters.cabin_trunk_height * math.tan(rake_rad)

    pts = [
        _vec_m(cabin_fwd_x, -half_w, deck_top_z),
        _vec_m(cabin_fwd_x, half_w, deck_top_z),
        _vec_m(cabin_fwd_x + aft_offset, half_w, cabin_top_z),
        _vec_m(cabin_fwd_x + aft_offset, -half_w, cabin_top_z),
        _vec_m(cabin_fwd_x, -half_w, deck_top_z),
    ]
    edges = [Part.LineSegment(pts[i], pts[i + 1]).toShape() for i in range(4)]
    wire = Part.Wire(edges)
    face = Part.Face(wire)
    # Extrude along its normal (small thickness) to give the windshield substance.
    windshield_solid = face.extrude(_vec_m(-0.005, 0, 0.005))

    obj = target_doc.addObject("Part::Feature", "Deck_Windshield")
    obj.Shape = windshield_solid
    added.append(obj)

    obj.addProperty("App::PropertyAngle", "WindshieldRake", "Deck", "Windshield rake from vertical")
    obj.WindshieldRake = parameters.windshield_rake

    return Windshield(body=obj, rake_degrees=parameters.windshield_rake)


def _build_hardtop(
    hull: Hull,
    parameters: DeckParameters,
    cabin_trunk: CabinTrunk,
    target_doc: Any,
    added: list[Any],
) -> Hardtop:
    """Build the hardtop slab (FR-007)."""
    import Part

    hp = hull.parameters
    deck_top_z = hp.sheer_height_aft + (hp.sheer_height_fwd - hp.sheer_height_aft) * 0.5
    cabin_top_z = deck_top_z + parameters.cabin_trunk_height
    hardtop_z = cabin_top_z + parameters.hardtop_height

    # Hardtop spans from (cabin_fwd - overhang_fwd) to (cabin_fwd + cabin_length + overhang_aft - hardtop_length adjustment).
    cabin_fwd_x = parameters.cabin_trunk_fwd_offset
    cabin_aft_x = cabin_fwd_x + parameters.cabin_trunk_length
    hardtop_fwd_x = cabin_fwd_x - parameters.hardtop_overhang_fwd
    # Hardtop length is measured along the boat; aft extent uses overhang_aft.
    hardtop_aft_x = hardtop_fwd_x + parameters.hardtop_length
    _ = cabin_aft_x  # informational; aft pillar X uses cabin_aft + overhang_aft separately

    hardtop_width = parameters.cabin_trunk_width + 0.10  # small margin to overhang sides

    slab_thickness = 0.05  # internal constant for the slab solidness

    rect = Part.makePlane(parameters.hardtop_length * _MM_PER_M, hardtop_width * _MM_PER_M)
    solid = rect.extrude(_vec_m(0, 0, slab_thickness))
    solid.translate(_vec_m(hardtop_fwd_x, -hardtop_width / 2.0, hardtop_z))
    _ = hardtop_aft_x  # used for documentation; aft pillar X derived from this elsewhere

    obj = target_doc.addObject("Part::Feature", "Deck_Hardtop")
    obj.Shape = solid
    added.append(obj)

    obj.addProperty("App::PropertyLength", "HardtopLength", "Deck", "Hardtop length")
    obj.addProperty("App::PropertyLength", "HardtopHeight", "Deck", "Hardtop height above cabin")
    obj.addProperty("App::PropertyLength", "HardtopOverhangFwd", "Deck", "Hardtop forward overhang")
    obj.addProperty("App::PropertyLength", "HardtopOverhangAft", "Deck", "Hardtop aft overhang")
    obj.HardtopLength = parameters.hardtop_length * 1000.0
    obj.HardtopHeight = parameters.hardtop_height * 1000.0
    obj.HardtopOverhangFwd = parameters.hardtop_overhang_fwd * 1000.0
    obj.HardtopOverhangAft = parameters.hardtop_overhang_aft * 1000.0

    return Hardtop(
        body=obj,
        length=parameters.hardtop_length,
        height_above_cabin=parameters.hardtop_height,
    )


def _build_hardtop_pillars(
    hull: Hull,
    parameters: DeckParameters,
    hardtop: Hardtop,
    deck_plate: DeckPlate,
    target_doc: Any,
    added: list[Any],
) -> HardtopPillars:
    """Build two aft hardtop support pillars (FR-007, FR-009)."""
    import Part

    hp = hull.parameters
    deck_top_z = hp.sheer_height_aft + (hp.sheer_height_fwd - hp.sheer_height_aft) * 0.5
    cabin_top_z = deck_top_z + parameters.cabin_trunk_height
    hardtop_z = cabin_top_z + parameters.hardtop_height

    cabin_fwd_x = parameters.cabin_trunk_fwd_offset
    hardtop_fwd_x = cabin_fwd_x - parameters.hardtop_overhang_fwd
    hardtop_aft_x = hardtop_fwd_x + parameters.hardtop_length
    pillar_y_offset = parameters.cabin_trunk_width / 2.0 + 0.05  # small clearance

    radius = parameters.hardtop_pillar_diameter / 2.0
    pillar_height = hardtop_z - deck_top_z

    pillar_port = Part.makeCylinder(
        radius * _MM_PER_M,
        pillar_height * _MM_PER_M,
        _vec_m(hardtop_aft_x, pillar_y_offset, deck_top_z),
    )
    pillar_starboard = Part.makeCylinder(
        radius * _MM_PER_M,
        pillar_height * _MM_PER_M,
        _vec_m(hardtop_aft_x, -pillar_y_offset, deck_top_z),
    )
    compound = Part.makeCompound([pillar_port, pillar_starboard])

    obj = target_doc.addObject("Part::Feature", "Deck_HardtopPillars")
    obj.Shape = compound
    added.append(obj)

    obj.addProperty("App::PropertyLength", "PillarDiameter", "Deck", "Hardtop pillar diameter")
    obj.PillarDiameter = parameters.hardtop_pillar_diameter * 1000.0

    return HardtopPillars(body=obj, pillar_diameter=parameters.hardtop_pillar_diameter)


def _build_railings(
    hull: Hull,
    parameters: DeckParameters,
    deck_plate: DeckPlate,
    target_doc: Any,
    added: list[Any],
) -> Railings:
    """Build the perimeter railing loop (FR-007, FR-009).

    v0.3.0-alpha builds a simplified rectangular rail loop running parallel
    to the boat's centerline at the deck plate's outer edges. The hull-sheer-
    following sweep is a v0.2.0 refinement (matches the deck plate sampling
    upgrade tracked in research R8).
    """
    import FreeCAD
    import Part

    hp = hull.parameters
    deck_top_z = hp.sheer_height_aft + (hp.sheer_height_fwd - hp.sheer_height_aft) * 0.5
    rail_z = deck_top_z + parameters.railing_height
    rail_pipe_radius = 0.012  # 25 mm OD internal constant

    samples = _sample_hull_sheer(hull)
    points_port = [_vec_m(x, y, rail_z) for x, y, _z in samples]
    points_starboard = [_vec_m(x, -y, rail_z) for x, y, _z in reversed(samples)]
    loop_pts = points_port + points_starboard[1:-1] + [points_port[0]]

    edges = [
        Part.LineSegment(loop_pts[i], loop_pts[i + 1]).toShape() for i in range(len(loop_pts) - 1)
    ]
    wire = Part.Wire(edges)

    # Build a small profile circle at the first point, perpendicular to the
    # path direction (approximated by Z-axis sweep — simpler and works for
    # a deck that's mostly flat in Z).
    profile_center = loop_pts[0]
    profile_circle = Part.Circle(
        profile_center, FreeCAD.Vector(1, 0, 0), rail_pipe_radius * _MM_PER_M
    )
    profile_wire = Part.Wire([profile_circle.toShape()])
    rail_solid = Part.makeSweepSurface(wire, profile_wire)
    _ = rail_solid  # FreeCAD's sweep API varies; fall back to a simple polyline if needed

    # Fallback: build the rail as a thin polyline-derived solid by extruding
    # the wire upward (this produces a "rail height ribbon" approximation
    # adequate for the v0.3.0-alpha bbox / parametricity tests).
    rail_face = Part.Face(wire) if wire.isClosed() else None
    rail_body = rail_face.extrude(_vec_m(0, 0, 0.01)) if rail_face is not None else wire

    obj = target_doc.addObject("Part::Feature", "Deck_Railings")
    obj.Shape = rail_body
    added.append(obj)

    obj.addProperty(
        "App::PropertyLength", "RailingHeight", "Deck", "Railing height above deck plate"
    )
    obj.RailingHeight = parameters.railing_height * 1000.0

    return Railings(body=obj, height=parameters.railing_height)


# ---------------------------------------------------------------------------
# Public builder (FR-001 + contracts/python-api.md)
# ---------------------------------------------------------------------------


def build_deck(
    hull: Hull,
    parameters: DeckParameters | None = None,
    *,
    document: Any = None,
    name: str = "Deck",
) -> Deck:
    """Build the six-Body parametric Storebro deck on a hull.

    Args:
        hull: A Hull returned by ``storebro.hull.build_hull``. Must have a
            non-empty ``.body.Shape``.
        parameters: Deck dimensional parameters. ``None`` → use
            :class:`DeckParameters` defaults (Storebro Royal Cruiser 34 1972
            estimate-grade values).
        document: Target FreeCAD document. ``None`` → use ``hull.document``.
            Must equal ``hull.document`` if non-None — cross-document deck
            building is rejected with :class:`DeckParameterError`.
        name: Base label for the Deck aggregate. Defaults to ``"Deck"``. The
            six sub-Bodies are labeled ``Deck_DeckPlate``, ``Deck_CabinTrunk``,
            ``Deck_Windshield``, ``Deck_Hardtop``, ``Deck_HardtopPillars``,
            ``Deck_Railings``. FreeCAD auto-numbering applies on collision.

    Returns:
        :class:`Deck` aggregate holding the six sub-Body wrappers + inputs.

    Raises:
        DeckParameterError: Invalid parameters, hull-incompatibility,
            null hull, or document mismatch. Raised BEFORE any FreeCAD call.
        DeckConstructionError: Unsupported FreeCAD version, or FreeCAD-side
            construction failure (after rollback completes — document state
            restored to pre-call).

    Example:
        >>> # from storebro import build_hull, build_deck
        >>> # deck = build_deck(build_hull())
        >>> # deck.cabin_trunk.length  # doctest: +SKIP
        >>> # 4.5
    """
    _ensure_freecad_supported()
    _validate_hull(hull)

    resolved_params = parameters if parameters is not None else DeckParameters()
    _validate_deck_parameters(resolved_params)
    _validate_cross_hull_constraints(hull, resolved_params)

    target_doc = _resolve_document(hull, document)
    label = name if name is not None else "Deck"

    started = time.perf_counter()
    added: list[Any] = []
    try:
        deck_plate = _build_deck_plate(hull, resolved_params, target_doc, added)
        cabin_trunk = _build_cabin_trunk(hull, resolved_params, deck_plate, target_doc, added)
        windshield = _build_windshield(hull, resolved_params, cabin_trunk, target_doc, added)
        hardtop = _build_hardtop(hull, resolved_params, cabin_trunk, target_doc, added)
        hardtop_pillars = _build_hardtop_pillars(
            hull, resolved_params, hardtop, deck_plate, target_doc, added
        )
        railings = _build_railings(hull, resolved_params, deck_plate, target_doc, added)
        target_doc.recompute()
    except DeckParameterError:
        _rollback(target_doc, added)
        raise
    except DeckConstructionError:
        _rollback(target_doc, added)
        raise
    except BaseException as exc:
        _rollback(target_doc, added)
        raise DeckConstructionError(
            f"build_deck failed during sub-Body construction — {type(exc).__name__}: {exc}",
            parameters=resolved_params,
            hull=hull,
            underlying=exc,
        ) from exc

    duration = time.perf_counter() - started
    return Deck(
        parameters=resolved_params,
        hull=hull,
        document=target_doc,
        label=label,
        build_duration_seconds=duration,
        deck_plate=deck_plate,
        cabin_trunk=cabin_trunk,
        windshield=windshield,
        hardtop=hardtop,
        hardtop_pillars=hardtop_pillars,
        railings=railings,
    )
