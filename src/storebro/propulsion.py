"""Parametric propulsion installation for the Storebro Royal Cruiser 34.

Spec 014. Builds an inboard propulsion train — engine bed (stringers), engine
block, propeller shaft, propeller, and rudder — and composes them via
:func:`build_propulsion` into a :class:`Propulsion` aggregate. Single-screw
(``engine_count=1``) and twin-screw (``engine_count=2``, default) layouts are
supported; the twin layout mirrors port/starboard trains about the centreline.

Coordinate convention (shared with hull/deck): bow = XMax, stern = XMin,
waterline = Z=0, port = +Y, starboard = -Y, all millimetres. "Aft" = smaller X.

Every component is a FreeCAD ``PartDesign::Body`` (sketch + Pad features), seated
on the ACTUAL sampled hull geometry (keel depth + half-beam read from
``hull.body.Shape``). The hull solid is NEVER booleaned — the shaft penetration
is modeled as an additive stern-tube boss (preserves manifold integrity per the
specs 009/011 lessons). Geometry fidelity is representative, not CAD-faithful
(FR-015); detailed machinery is deferred (see spec.allium).

Public API:

- :func:`build_propulsion` — compose the five components into a document
- :class:`Propulsion` — return type of :func:`build_propulsion`
- :class:`PropulsionParameters` — composite parameter set (frozen)
- :class:`EngineBedParameters`, :class:`EngineParameters`,
  :class:`ShaftParameters`, :class:`PropellerParameters`,
  :class:`RudderParameters` — per-component parameters (frozen)
- :class:`EngineBed`, :class:`EngineBlock`, :class:`Shaft`, :class:`Propeller`,
  :class:`Rudder` — component result wrappers
- :class:`PropulsionParameterError`, :class:`PropulsionConstructionError`

Example:
    >>> from storebro import build_propulsion, PropulsionParameters
    >>> # build_propulsion(hull, deck) requires FreeCAD 1.1+ on this host.
"""

from __future__ import annotations

import contextlib
import dataclasses
import math
import time
from dataclasses import dataclass, field
from typing import Any

from storebro.deck import Deck
from storebro.hull import Hull

_MM_PER_M = 1000.0
_WATERLINE_Z_MM = 0.0
"""Design waterline is the Z=0 datum (keel below, freeboard above)."""

__all__ = [
    "EngineBed",
    "EngineBedParameters",
    "EngineBlock",
    "EngineParameters",
    "Propeller",
    "PropellerParameters",
    "Propulsion",
    "PropulsionConstructionError",
    "PropulsionParameterError",
    "PropulsionParameters",
    "Rudder",
    "RudderParameters",
    "Shaft",
    "ShaftParameters",
    "build_propulsion",
]


# ---------------------------------------------------------------------------
# Exceptions (mirror hull.HullParameterError / HullConstructionError)
# ---------------------------------------------------------------------------


class PropulsionParameterError(ValueError):
    """Raised before any FreeCAD call when a propulsion parameter is invalid.

    Carries structured attributes so callers can introspect the failure
    without parsing the message string.

    Example:
        >>> err = PropulsionParameterError("engine_count", 3, "in {1, 2}")
        >>> err.parameter_name
        'engine_count'
        >>> isinstance(err, ValueError)
        True
    """

    def __init__(
        self,
        parameter_name: str,
        parameter_value: float | int | None,
        valid_range: str,
    ) -> None:
        self.parameter_name = parameter_name
        self.parameter_value = parameter_value
        self.valid_range = valid_range
        if parameter_value is None:
            message = (
                f"PropulsionParameterError: invalid parameter combination — "
                f"{parameter_name} ({valid_range})"
            )
        else:
            message = (
                f"PropulsionParameterError: {parameter_name} = {parameter_value!r} "
                f"is outside the valid range {valid_range}"
            )
        super().__init__(message)


class PropulsionConstructionError(RuntimeError):
    """Raised when FreeCAD fails to construct the propulsion geometry.

    The document is rolled back to its pre-call state before this is raised.

    Example:
        >>> err = PropulsionConstructionError("boom")
        >>> isinstance(err, RuntimeError)
        True
    """

    def __init__(
        self,
        message: str,
        *,
        parameters: PropulsionParameters | None = None,
        underlying: BaseException | None = None,
    ) -> None:
        self.parameters = parameters
        self.underlying = underlying
        super().__init__(f"PropulsionConstructionError: {message}")


# ---------------------------------------------------------------------------
# Component parameter dataclasses (data-model §1; constitution I)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EngineBedParameters:
    """Engine bed / stringer dimensions (mm). Frozen; validated on construction."""

    length_mm: float = 1400.0
    width_mm: float = 120.0
    height_mm: float = 200.0

    def __post_init__(self) -> None:
        _require_positive("engine_bed.length_mm", self.length_mm)
        _require_positive("engine_bed.width_mm", self.width_mm)
        _require_positive("engine_bed.height_mm", self.height_mm)


@dataclass(frozen=True)
class EngineParameters:
    """Engine block dimensions + longitudinal station (mm). Frozen."""

    length_mm: float = 1100.0
    width_mm: float = 600.0
    height_mm: float = 700.0
    station_x_mm: float = 3500.0

    def __post_init__(self) -> None:
        _require_positive("engine.length_mm", self.length_mm)
        _require_positive("engine.width_mm", self.width_mm)
        _require_positive("engine.height_mm", self.height_mm)
        _require_non_negative("engine.station_x_mm", self.station_x_mm)


@dataclass(frozen=True)
class ShaftParameters:
    """Propeller-shaft diameter, down-angle, and hull-exit station (mm/deg). Frozen."""

    diameter_mm: float = 45.0
    angle_deg: float = 10.0
    exit_x_mm: float = 1800.0

    def __post_init__(self) -> None:
        _require_positive("shaft.diameter_mm", self.diameter_mm)
        if not (0.0 <= self.angle_deg <= 30.0):
            raise PropulsionParameterError("shaft.angle_deg", self.angle_deg, "[0, 30]")
        _require_non_negative("shaft.exit_x_mm", self.exit_x_mm)


@dataclass(frozen=True)
class PropellerParameters:
    """Propeller disc / hub diameters and blade count (mm). Frozen."""

    diameter_mm: float = 450.0
    hub_diameter_mm: float = 90.0
    blade_count: int = 3

    def __post_init__(self) -> None:
        _require_positive("propeller.diameter_mm", self.diameter_mm)
        _require_positive("propeller.hub_diameter_mm", self.hub_diameter_mm)
        if self.hub_diameter_mm >= self.diameter_mm:
            raise PropulsionParameterError(
                "propeller.hub_diameter_mm",
                self.hub_diameter_mm,
                f"< diameter_mm ({self.diameter_mm})",
            )
        if not (2 <= self.blade_count <= 6):
            raise PropulsionParameterError("propeller.blade_count", self.blade_count, "[2, 6]")


@dataclass(frozen=True)
class RudderParameters:
    """Rudder blade chord/span/thickness and stock diameter (mm). Frozen."""

    chord_mm: float = 300.0
    span_mm: float = 500.0
    thickness_mm: float = 40.0
    stock_diameter_mm: float = 50.0

    def __post_init__(self) -> None:
        _require_positive("rudder.chord_mm", self.chord_mm)
        _require_positive("rudder.span_mm", self.span_mm)
        _require_positive("rudder.thickness_mm", self.thickness_mm)
        _require_positive("rudder.stock_diameter_mm", self.stock_diameter_mm)


@dataclass(frozen=True)
class PropulsionParameters:
    """Composite propulsion parameters + layout fields (mm). Frozen.

    ``rudder_count=None`` resolves to ``engine_count`` at build time (one rudder
    per screw). An explicitly-supplied value must be in ``{1, 2}``.
    """

    engine_count: int = 2
    engine_offset_y_mm: float = 400.0
    rudder_count: int | None = None
    engine_bed: EngineBedParameters = field(default_factory=EngineBedParameters)
    engine: EngineParameters = field(default_factory=EngineParameters)
    shaft: ShaftParameters = field(default_factory=ShaftParameters)
    propeller: PropellerParameters = field(default_factory=PropellerParameters)
    rudder: RudderParameters = field(default_factory=RudderParameters)

    def __post_init__(self) -> None:
        if self.engine_count not in (1, 2):
            raise PropulsionParameterError("engine_count", self.engine_count, "in {1, 2}")
        if self.rudder_count is not None and self.rudder_count not in (1, 2):
            raise PropulsionParameterError("rudder_count", self.rudder_count, "in {1, 2} or None")
        _require_non_negative("engine_offset_y_mm", self.engine_offset_y_mm)
        if self.engine_count == 1 and self.engine_offset_y_mm != 0.0:
            raise PropulsionParameterError(
                "engine_offset_y_mm",
                self.engine_offset_y_mm,
                "= 0 when engine_count == 1 (single screw is centred)",
            )
        if self.engine_count == 2 and self.engine_offset_y_mm <= 0.0:
            raise PropulsionParameterError(
                "engine_offset_y_mm",
                self.engine_offset_y_mm,
                "> 0 when engine_count == 2 (twin screws are offset)",
            )
        if self.shaft.exit_x_mm >= self.engine.station_x_mm:
            raise PropulsionParameterError(
                "shaft.exit_x_mm",
                self.shaft.exit_x_mm,
                f"< engine.station_x_mm ({self.engine.station_x_mm}) — shaft runs aft",
            )


def _require_positive(name: str, value: float) -> None:
    if not (math.isfinite(value) and value > 0):
        raise PropulsionParameterError(name, value, "> 0")


def _require_non_negative(name: str, value: float) -> None:
    if not (math.isfinite(value) and value >= 0):
        raise PropulsionParameterError(name, value, ">= 0")


# ---------------------------------------------------------------------------
# Result wrapper dataclasses (data-model §"Output wrapper dataclasses")
# ---------------------------------------------------------------------------


@dataclass
class EngineBed:
    """One engine bed body (per train)."""

    body: Any
    parameters: EngineBedParameters
    is_port: bool
    volume_mm3: float
    bbox_min_z_mm: float


@dataclass
class EngineBlock:
    """One engine block body (per train)."""

    body: Any
    parameters: EngineParameters
    is_port: bool
    rests_on_bed: bool
    within_hull_envelope: bool
    pierces_hull_shell: bool
    volume_mm3: float


@dataclass
class Shaft:
    """One propeller-shaft body incl. the additive stern-tube boss (per train)."""

    body: Any
    parameters: ShaftParameters
    is_port: bool
    forward_z_mm: float
    aft_z_mm: float
    exit_x_mm: float
    exit_z_mm: float
    has_stern_tube_boss: bool
    volume_mm3: float


@dataclass
class Propeller:
    """One propeller body (hub + blades, per train)."""

    body: Any
    parameters: PropellerParameters
    is_port: bool
    hub_x_mm: float
    bbox_min_z_mm: float
    blade_count: int
    volume_mm3: float


@dataclass
class Rudder:
    """One rudder body (blade + stock)."""

    body: Any
    parameters: RudderParameters
    is_port: bool
    x_mm: float
    bbox_min_z_mm: float
    volume_mm3: float


@dataclass
class Propulsion:
    """Return value of :func:`build_propulsion`. Wraps the component bodies."""

    document: Any
    parameters: PropulsionParameters
    engine_beds: list[EngineBed]
    engines: list[EngineBlock]
    shafts: list[Shaft]
    propellers: list[Propeller]
    rudders: list[Rudder]
    hull_modified: bool
    build_duration_seconds: float = field(default=0.0)


# ---------------------------------------------------------------------------
# Hull-geometry sampling (FR-003; mirrors hull._hull_outer_y_and_freeboard_at)
# ---------------------------------------------------------------------------


def _vertices_near(shape: Any, x_mm: float, frac: float = 0.05) -> list[Any]:
    span = shape.BoundBox.XLength
    near = [v for v in shape.Vertexes if abs(v.X - x_mm) < frac * span]
    return near if near else list(shape.Vertexes)


def _hull_bottom_z_at(hull: Hull, x_mm: float) -> float:
    """Return the hull keel (min Z, mm) near longitudinal station X."""
    shape = hull.body.Shape
    near = _vertices_near(shape, x_mm)
    return float(min((v.Z for v in near), default=shape.BoundBox.ZMin))


def _hull_half_beam_at(hull: Hull, x_mm: float) -> float:
    """Return the hull half-beam (max |Y|, mm) near longitudinal station X."""
    shape = hull.body.Shape
    near = _vertices_near(shape, x_mm)
    return float(max((abs(v.Y) for v in near), default=shape.BoundBox.YMax))


def _shape_top_z_at(shape: Any, x_mm: float) -> float:
    """Return the max Z (mm) near longitudinal station X — a clearance ceiling."""
    near = _vertices_near(shape, x_mm)
    return float(max((v.Z for v in near), default=shape.BoundBox.ZMax))


def _engine_ceiling_z(hull: Hull, deck: Deck | None, x_mm: float) -> float:
    """Engine-height ceiling: deck-plate top Z, or the hull sheer when no deck."""
    if deck is not None:
        return _shape_top_z_at(deck.deck_plate.body.Shape, x_mm)
    return _shape_top_z_at(hull.body.Shape, x_mm)


# ---------------------------------------------------------------------------
# PartDesign micro-helpers (module-local; mirror the spec 008/010 deck idiom)
# ---------------------------------------------------------------------------


def _pd_get_origin_plane(body: Any, plane_name: str) -> Any:
    for feat in body.Origin.OriginFeatures:
        if feat.Name.rstrip("0123456789") == plane_name:
            return feat
    raise RuntimeError(f"Could not locate Origin.{plane_name} on body {body.Label!r}")


def _pd_datum_xy(body: Any, name: str, z_mm: float, added: list[Any]) -> Any:
    """PartDesign datum parallel to XY at global Z = z_mm (normal +Z)."""
    import FreeCAD

    xy_plane = _pd_get_origin_plane(body, "XY_Plane")
    datum = body.newObject("PartDesign::Plane", name)
    added.append(datum)
    datum.AttachmentSupport = [(xy_plane, "")]
    datum.MapMode = "FlatFace"
    datum.AttachmentOffset = FreeCAD.Placement(
        FreeCAD.Vector(0.0, 0.0, z_mm), FreeCAD.Rotation()
    )
    return datum


def _pd_datum_yz(body: Any, name: str, x_mm: float, z_mm: float, added: list[Any]) -> Any:
    """PartDesign datum parallel to YZ at global (x_mm, 0, z_mm); normal +X.

    YZ_Plane local frame: local X = global Y, local Y = global Z, local Z =
    global X (normal). Local AttachmentOffset vector is therefore (0, z_mm, x_mm).
    """
    import FreeCAD

    yz_plane = _pd_get_origin_plane(body, "YZ_Plane")
    datum = body.newObject("PartDesign::Plane", name)
    added.append(datum)
    datum.AttachmentSupport = [(yz_plane, "")]
    datum.MapMode = "FlatFace"
    datum.AttachmentOffset = FreeCAD.Placement(
        FreeCAD.Vector(0.0, z_mm, x_mm), FreeCAD.Rotation()
    )
    return datum


def _pd_close_loop(sketch: Any, line_ids: list[int]) -> None:
    import Sketcher

    n = len(line_ids)
    for i in range(n):
        j = (i + 1) % n
        sketch.addConstraint(Sketcher.Constraint("Coincident", line_ids[i], 2, line_ids[j], 1))


def _pd_rect_pad(
    body: Any,
    datum: Any,
    name: str,
    corners_uv: list[tuple[float, float]],
    length: float,
    added: list[Any],
    *,
    midplane: bool = False,
    reversed_: bool = False,
) -> Any:
    """Sketch a closed polygon (in datum-local u/v) and Pad it along the datum normal."""
    import FreeCAD
    import Part

    sketch = body.newObject("Sketcher::SketchObject", f"{name}Sketch")
    added.append(sketch)
    sketch.AttachmentSupport = [(datum, "")]
    sketch.MapMode = "FlatFace"
    pts = [FreeCAD.Vector(u, v, 0) for (u, v) in corners_uv]
    line_ids: list[int] = []
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        line_ids.append(sketch.addGeometry(Part.LineSegment(pts[i], pts[j]), False))
    _pd_close_loop(sketch, line_ids)
    pad = body.newObject("PartDesign::Pad", f"{name}Pad")
    added.append(pad)
    pad.Profile = (sketch, [""])
    pad.Length = length
    pad.Midplane = midplane
    pad.Reversed = reversed_
    return pad


def _pd_circle_pad(
    body: Any,
    datum: Any,
    name: str,
    center_u: float,
    center_v: float,
    radius: float,
    length: float,
    added: list[Any],
    *,
    midplane: bool = False,
) -> Any:
    """Sketch a circle (in datum-local u/v) and Pad it along the datum normal."""
    import FreeCAD
    import Part

    sketch = body.newObject("Sketcher::SketchObject", f"{name}Sketch")
    added.append(sketch)
    sketch.AttachmentSupport = [(datum, "")]
    sketch.MapMode = "FlatFace"
    circle = Part.Circle(FreeCAD.Vector(center_u, center_v, 0), FreeCAD.Vector(0, 0, 1), radius)
    sketch.addGeometry(circle.toShape().Curve, False)
    pad = body.newObject("PartDesign::Pad", f"{name}Pad")
    added.append(pad)
    pad.Profile = (sketch, [""])
    pad.Length = length
    pad.Midplane = midplane
    pad.Reversed = False
    return pad


def _shaft_axis_placement(coupling_x: float, offset_y: float, coupling_z: float, angle_deg: float) -> Any:
    """Placement that maps a body's local +X axis to the aft-and-down shaft axis.

    Rotation about global +Y by (180 - angle): local +X -> (-cos, 0, -sin),
    i.e. aft (-X) and down (-Z). Base = the forward (engine-coupling) point.
    """
    import FreeCAD

    return FreeCAD.Placement(
        FreeCAD.Vector(coupling_x, offset_y, coupling_z),
        FreeCAD.Rotation(FreeCAD.Vector(0.0, 1.0, 0.0), 180.0 - angle_deg),
    )


# ---------------------------------------------------------------------------
# Component builders (data-model §"Output wrapper dataclasses"; plan Build Seq)
# ---------------------------------------------------------------------------


def _build_engine_bed(
    hull: Hull,
    params: PropulsionParameters,
    target_doc: Any,
    added: list[Any],
    *,
    is_port: bool,
    offset_y: float,
) -> EngineBed:
    """Box Pad seated on the sampled keel at the engine station (per train)."""
    bp = params.engine_bed
    engine_x = params.engine.station_x_mm
    keel_z = _hull_bottom_z_at(hull, engine_x)
    fwd_x = engine_x + bp.length_mm / 2.0
    aft_x = engine_x - bp.length_mm / 2.0
    y0, y1 = offset_y - bp.width_mm / 2.0, offset_y + bp.width_mm / 2.0

    body = target_doc.addObject("PartDesign::Body", "Propulsion_EngineBed")
    added.append(body)
    target_doc.recompute()
    datum = _pd_datum_xy(body, "EngineBedDatum", keel_z, added)
    _pd_rect_pad(
        body,
        datum,
        "EngineBed",
        [(aft_x, y0), (fwd_x, y0), (fwd_x, y1), (aft_x, y1)],
        bp.height_mm,
        added,
    )
    target_doc.recompute()
    shape = body.Shape
    return EngineBed(
        body=body,
        parameters=bp,
        is_port=is_port,
        volume_mm3=float(shape.Volume),
        bbox_min_z_mm=float(shape.BoundBox.ZMin),
    )


def _build_engine(
    hull: Hull,
    deck: Deck | None,
    params: PropulsionParameters,
    bed: EngineBed,
    target_doc: Any,
    added: list[Any],
    *,
    is_port: bool,
    offset_y: float,
) -> EngineBlock:
    """Box Pad resting on the bed top, contained within the hull envelope (per train)."""
    ep = params.engine
    engine_x = ep.station_x_mm
    keel_z = _hull_bottom_z_at(hull, engine_x)
    bottom_z = keel_z + params.engine_bed.height_mm
    top_z = bottom_z + ep.height_mm
    ceiling = _engine_ceiling_z(hull, deck, engine_x)
    half_beam = _hull_half_beam_at(hull, engine_x)

    fwd_x = engine_x + ep.length_mm / 2.0
    aft_x = engine_x - ep.length_mm / 2.0
    y0, y1 = offset_y - ep.width_mm / 2.0, offset_y + ep.width_mm / 2.0

    body = target_doc.addObject("PartDesign::Body", "Propulsion_Engine")
    added.append(body)
    target_doc.recompute()
    datum = _pd_datum_xy(body, "EngineDatum", bottom_z, added)
    _pd_rect_pad(
        body,
        datum,
        "Engine",
        [(aft_x, y0), (fwd_x, y0), (fwd_x, y1), (aft_x, y1)],
        ep.height_mm,
        added,
    )
    target_doc.recompute()

    within = (top_z <= ceiling) and (abs(offset_y) + ep.width_mm / 2.0 <= half_beam)
    shape = body.Shape
    return EngineBlock(
        body=body,
        parameters=ep,
        is_port=is_port,
        rests_on_bed=True,
        within_hull_envelope=within,
        pierces_hull_shell=not within,
        volume_mm3=float(shape.Volume),
    )


def _build_shaft(
    hull: Hull,
    params: PropulsionParameters,
    target_doc: Any,
    added: list[Any],
    *,
    is_port: bool,
    offset_y: float,
) -> Shaft:
    """Tilted cylinder from the engine coupling aft to the hull exit + stern-tube boss."""
    sp = params.shaft
    engine_x = params.engine.station_x_mm
    exit_x = sp.exit_x_mm
    angle = math.radians(sp.angle_deg)
    run = engine_x - exit_x
    slant = run / math.cos(angle)
    exit_z = _hull_bottom_z_at(hull, exit_x)
    coupling_z = exit_z + run * math.tan(angle)
    radius = sp.diameter_mm / 2.0

    body = target_doc.addObject("PartDesign::Body", "Propulsion_Shaft")
    added.append(body)
    target_doc.recompute()

    # Shaft: circle on the YZ origin plane, padded +X (local) by the slant length.
    shaft_datum = _pd_datum_yz(body, "ShaftDatum", 0.0, 0.0, added)
    _pd_circle_pad(body, shaft_datum, "Shaft", 0.0, 0.0, radius, slant, added)
    # Stern-tube boss: fatter coaxial cylinder near the aft (exit) end.
    boss_len = min(120.0, slant * 0.4)
    boss_datum = _pd_datum_yz(body, "BossDatum", slant - boss_len, 0.0, added)
    _pd_circle_pad(body, boss_datum, "Boss", 0.0, 0.0, radius * 1.8, boss_len, added)
    target_doc.recompute()

    body.Placement = _shaft_axis_placement(engine_x, offset_y, coupling_z, sp.angle_deg)
    target_doc.recompute()

    shape = body.Shape
    return Shaft(
        body=body,
        parameters=sp,
        is_port=is_port,
        forward_z_mm=coupling_z,
        aft_z_mm=exit_z,
        exit_x_mm=exit_x,
        exit_z_mm=exit_z,
        has_stern_tube_boss=True,
        volume_mm3=float(shape.Volume),
    )


def _blade_corners(
    angle_rad: float, inner_r: float, outer_r: float, half_w: float
) -> list[tuple[float, float]]:
    """Four corners (u, v) of a radial blade rectangle rotated to ``angle_rad``."""
    dx, dy = math.cos(angle_rad), math.sin(angle_rad)  # radial unit (u, v)
    tx, ty = -dy, dx  # tangential unit
    return [
        (inner_r * dx - half_w * tx, inner_r * dy - half_w * ty),
        (outer_r * dx - half_w * tx, outer_r * dy - half_w * ty),
        (outer_r * dx + half_w * tx, outer_r * dy + half_w * ty),
        (inner_r * dx + half_w * tx, inner_r * dy + half_w * ty),
    ]


def _build_propeller(
    params: PropulsionParameters,
    shaft: Shaft,
    target_doc: Any,
    added: list[Any],
    *,
    is_port: bool,
    offset_y: float,
) -> Propeller:
    """Hub cylinder + N radial blades, on the shaft axis aft of the shaft exit (per train)."""
    pp = params.propeller
    angle_deg = params.shaft.angle_deg
    angle = math.radians(angle_deg)
    hub_r = pp.hub_diameter_mm / 2.0
    prop_r = pp.diameter_mm / 2.0
    hub_len = pp.hub_diameter_mm  # representative axial length
    blade_thickness = max(pp.diameter_mm * 0.05, 8.0)
    blade_half_w = pp.diameter_mm * 0.10

    # Hub centre: a short distance aft-and-down from the shaft exit on the axis.
    aft_dir = (-math.cos(angle), 0.0, -math.sin(angle))
    gap = hub_len
    hub_cx = shaft.exit_x_mm + aft_dir[0] * gap
    hub_cz = shaft.exit_z_mm + aft_dir[2] * gap

    body = target_doc.addObject("PartDesign::Body", "Propulsion_Propeller")
    added.append(body)
    target_doc.recompute()

    hub_datum = _pd_datum_yz(body, "PropHubDatum", 0.0, 0.0, added)
    _pd_circle_pad(body, hub_datum, "PropHub", 0.0, 0.0, hub_r, hub_len, added, midplane=True)
    blade_datum = _pd_datum_yz(body, "PropBladeDatum", 0.0, 0.0, added)
    for i in range(pp.blade_count):
        a = (2.0 * math.pi * i) / pp.blade_count
        corners = _blade_corners(a, hub_r * 0.8, prop_r, blade_half_w)
        _pd_rect_pad(
            body,
            blade_datum,
            f"PropBlade{i}",
            corners,
            blade_thickness,
            added,
            midplane=True,
        )
    target_doc.recompute()

    body.Placement = _shaft_axis_placement(hub_cx, offset_y, hub_cz, angle_deg)
    target_doc.recompute()

    shape = body.Shape
    return Propeller(
        body=body,
        parameters=pp,
        is_port=is_port,
        hub_x_mm=hub_cx,
        bbox_min_z_mm=float(shape.BoundBox.ZMin),
        blade_count=pp.blade_count,
        volume_mm3=float(shape.Volume),
    )


def _build_rudder(
    hull: Hull,
    params: PropulsionParameters,
    propeller: Propeller,
    target_doc: Any,
    added: list[Any],
    *,
    is_port: bool,
    offset_y: float,
) -> Rudder:
    """Foil-plate blade + vertical stock, aft of the propeller below the waterline."""
    rp = params.rudder
    margin = 60.0
    trailing_x = propeller.hub_x_mm - margin
    center_x = trailing_x - rp.chord_mm / 2.0
    fwd_x = center_x + rp.chord_mm / 2.0
    aft_x = center_x - rp.chord_mm / 2.0
    top_z = min(_WATERLINE_Z_MM, _hull_bottom_z_at(hull, center_x))
    bottom_z = top_z - rp.span_mm

    body = target_doc.addObject("PartDesign::Body", "Propulsion_Rudder")
    added.append(body)
    target_doc.recompute()

    # Blade: a chord(X) x thickness(Y) column extruded up by span from the
    # bottom datum (XY datum, normal +Z). Representative flat foil plate.
    blade_datum = _pd_datum_xy(body, "RudderBladeDatum", bottom_z, added)
    y0, y1 = offset_y - rp.thickness_mm / 2.0, offset_y + rp.thickness_mm / 2.0
    _pd_rect_pad(
        body,
        blade_datum,
        "RudderBlade",
        [(aft_x, y0), (fwd_x, y0), (fwd_x, y1), (aft_x, y1)],
        rp.span_mm,
        added,
    )
    # Stock: vertical cylinder near the leading edge, overlapping the blade and
    # extending up into the hull underbody (so the two fuse into one solid).
    stock_datum = _pd_datum_xy(body, "RudderStockDatum", bottom_z, added)
    stock_x = center_x + rp.chord_mm * 0.25
    _pd_circle_pad(
        body,
        stock_datum,
        "RudderStock",
        stock_x,
        offset_y,
        rp.stock_diameter_mm / 2.0,
        rp.span_mm + 150.0,
        added,
    )
    target_doc.recompute()

    shape = body.Shape
    return Rudder(
        body=body,
        parameters=rp,
        is_port=is_port,
        x_mm=center_x,
        bbox_min_z_mm=float(shape.BoundBox.ZMin),
        volume_mm3=float(shape.Volume),
    )


# ---------------------------------------------------------------------------
# Orchestration helpers
# ---------------------------------------------------------------------------


def _resolve_rudder_count(params: PropulsionParameters) -> PropulsionParameters:
    """Resolve ``rudder_count=None`` to ``engine_count`` (one rudder per screw)."""
    if params.rudder_count is None:
        return dataclasses.replace(params, rudder_count=params.engine_count)
    return params


def _resolve_trains(params: PropulsionParameters) -> list[tuple[bool, float]]:
    """Return ``[(is_port, offset_y_mm), ...]`` — 1 centreline train, or 2 mirrored."""
    if params.engine_count == 1:
        return [(True, 0.0)]
    return [
        (True, params.engine_offset_y_mm),
        (False, -params.engine_offset_y_mm),
    ]


def _validate_build_context(hull: Hull, params: PropulsionParameters) -> None:
    """Hull-relative validation that needs sampled geometry (FR-005, FR-004)."""
    engine_x = params.engine.station_x_mm
    half_beam = _hull_half_beam_at(hull, engine_x)
    if params.engine_offset_y_mm + params.engine.width_mm / 2.0 > half_beam:
        raise PropulsionParameterError(
            "engine_offset_y_mm",
            params.engine_offset_y_mm,
            f"<= {half_beam - params.engine.width_mm / 2.0:.1f} "
            "(engine must stay inboard of the hull topside at its station)",
        )
    exit_z = _hull_bottom_z_at(hull, params.shaft.exit_x_mm)
    if exit_z > _WATERLINE_Z_MM:
        raise PropulsionParameterError(
            "shaft.exit_x_mm",
            params.shaft.exit_x_mm,
            "a station where the hull bottom is below the waterline",
        )


def _assert_manifold(wrappers: list[Any]) -> None:
    """Assert every produced body is a single closed valid solid (FR-008)."""
    for w in wrappers:
        shape = w.body.Shape
        if len(shape.Solids) != 1 or not shape.isValid():
            raise PropulsionConstructionError(
                f"{w.body.Label} is not a single closed manifold "
                f"(Solids={len(shape.Solids)}, isValid={shape.isValid()})"
            )


# ---------------------------------------------------------------------------
# Public entry point (FR-001, FR-006, FR-010)
# ---------------------------------------------------------------------------


def build_propulsion(
    hull: Hull,
    deck: Deck | None = None,
    parameters: PropulsionParameters | None = None,
    *,
    document: Any | None = None,
    name: str = "Propulsion",
    apply_render_attributes: bool = True,
) -> Propulsion:
    """Build a parametric inboard propulsion installation seated in the hull.

    Args:
        hull: A built :class:`~storebro.hull.Hull`; its shape is sampled for
            keel depth and half-beam. Components are added to ``hull.document``
            unless ``document`` is given.
        deck: Optional built :class:`~storebro.deck.Deck`; supplies the engine
            clearance ceiling. ``None`` → fall back to the hull sheer.
        parameters: Propulsion parameters. ``None`` → twin-screw RC34 defaults.
        document: Target FreeCAD document. ``None`` → ``hull.document``.
        name: Reserved label prefix (component bodies are individually labelled).

    Returns:
        :class:`Propulsion` wrapping the produced component bodies.

    Raises:
        PropulsionParameterError: Invalid parameters or build-context violation
            (engine offset past the topsides, shaft exit not aft of the engine,
            exit above the waterline). Raised before/at the start of the build.
        PropulsionConstructionError: A FreeCAD-side failure; the document is
            rolled back to its pre-call state first.

    Example:
        >>> from storebro import build_propulsion
        >>> # prop = build_propulsion(hull, deck)  # twin screw by default
    """
    from storebro._freecad_check import ensure_supported_freecad

    ensure_supported_freecad()

    base = parameters if parameters is not None else PropulsionParameters()
    # Re-validate on entry (defends against subclasses bypassing __post_init__).
    PropulsionParameters.__post_init__(base)
    resolved = _resolve_rudder_count(base)

    target_doc = document if document is not None else hull.document
    _validate_build_context(hull, resolved)

    started = time.perf_counter()
    added: list[Any] = []
    try:
        beds: list[EngineBed] = []
        engines: list[EngineBlock] = []
        shafts: list[Shaft] = []
        propellers: list[Propeller] = []
        rudders: list[Rudder] = []

        for is_port, offset_y in _resolve_trains(resolved):
            bed = _build_engine_bed(
                hull, resolved, target_doc, added, is_port=is_port, offset_y=offset_y
            )
            beds.append(bed)
            engine = _build_engine(
                hull, deck, resolved, bed, target_doc, added, is_port=is_port, offset_y=offset_y
            )
            engines.append(engine)
            shaft = _build_shaft(
                hull, resolved, target_doc, added, is_port=is_port, offset_y=offset_y
            )
            shafts.append(shaft)
            propeller = _build_propeller(
                resolved, shaft, target_doc, added, is_port=is_port, offset_y=offset_y
            )
            propellers.append(propeller)

        rudder_count = resolved.rudder_count if resolved.rudder_count is not None else 1
        if rudder_count == len(propellers):
            for prop in propellers:
                rudders.append(
                    _build_rudder(
                        hull,
                        resolved,
                        prop,
                        target_doc,
                        added,
                        is_port=prop.is_port,
                        offset_y=_propeller_offset_y(resolved, prop),
                    )
                )
        else:
            # Single centreline rudder aft of the (first) propeller.
            rudders.append(
                _build_rudder(
                    hull,
                    resolved,
                    propellers[0],
                    target_doc,
                    added,
                    is_port=True,
                    offset_y=0.0,
                )
            )

        target_doc.recompute()
        _assert_manifold([*beds, *engines, *shafts, *propellers, *rudders])
    except PropulsionParameterError:
        _rollback(target_doc, added)
        raise
    except PropulsionConstructionError:
        _rollback(target_doc, added)
        raise
    except BaseException as underlying:
        _rollback(target_doc, added)
        raise PropulsionConstructionError(
            f"FreeCAD failed to construct propulsion with parameters {resolved!r} — "
            f"{type(underlying).__name__}: {underlying}",
            parameters=resolved,
            underlying=underlying,
        ) from underlying

    # spec 015 — cosmetic render attributes: dark engine + bed, steel shaft,
    # bronze propeller + rudder. Geometry committed → outside the rollback block.
    from storebro.render import apply_render_attributes as _apply_render_attributes

    _render_targets: list[Any] = [
        *(b.body for b in beds),
        *(e.body for e in engines),
        *(s.body for s in shafts),
        *(p.body for p in propellers),
        *(r.body for r in rudders),
    ]
    _apply_render_attributes(_render_targets, enabled=apply_render_attributes)

    duration = time.perf_counter() - started
    return Propulsion(
        document=target_doc,
        parameters=resolved,
        engine_beds=beds,
        engines=engines,
        shafts=shafts,
        propellers=propellers,
        rudders=rudders,
        hull_modified=False,
        build_duration_seconds=duration,
    )


def _propeller_offset_y(params: PropulsionParameters, prop: Propeller) -> float:
    """Recover a propeller's transverse offset for placing its matching rudder."""
    if params.engine_count == 1:
        return 0.0
    return params.engine_offset_y_mm if prop.is_port else -params.engine_offset_y_mm


def _rollback(target_doc: Any, added: list[Any]) -> None:
    for obj in reversed(added):
        with contextlib.suppress(BaseException):
            target_doc.removeObject(obj.Name)
