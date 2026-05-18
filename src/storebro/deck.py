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
import math
import time
from dataclasses import dataclass, field
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
    "CabinTrunkParameters",
    "Deck",
    "DeckConstructionError",
    "DeckParameterError",
    "DeckParameters",
    "DeckSuperstructureParameters",
    "HardtopParameters",
    "PillarParameters",
    "RailingParameters",
    "WindshieldParameters",
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

    def to_superstructure_parameters(self) -> DeckSuperstructureParameters:
        """Map legacy 14-field DeckParameters onto the new 6-dataclass composite.

        Deterministic, pure: no I/O, no time, no env. See spec 008
        research.md §R4 for the field-by-field translation.

        Legacy fields that do not map onto the new dataclasses
        (`deck_plate_thickness`, `cabin_trunk_fwd_offset`,
        `cabin_trunk_corner_radius`) are silently dropped — they were
        either consumed by the deck plate (which is separate from the
        superstructure) or replaced by an idiomatic alternative
        (rake angles instead of corner radius). The legacy
        `cabin_trunk_width` becomes both forward_width and aft_width
        on the new CabinTrunkParameters (legacy assumed a rectangular
        cabin trunk).

        Example:
            >>> legacy = DeckParameters()
            >>> sp = legacy.to_superstructure_parameters()
            >>> sp.cabin_trunk.length > 0
            True
            >>> sp.pillars.diameter > 0
            True
        """
        # Legacy fields are in meters; new dataclasses are in millimeters.
        # Legacy cabin trunk is a rectangular box (single width) — map
        # to both forward + aft on the new tapered dataclass so the
        # default-trip-back-through-shim retains its rectangular shape
        # rather than silently introducing taper. The reference RC34 is
        # tapered, but a caller who explicitly passes legacy values
        # expects a faithful translation, not a redesign.
        legacy_w_mm = self.cabin_trunk_width * 1000.0
        cabin = CabinTrunkParameters(
            length=self.cabin_trunk_length * 1000.0,
            forward_width=legacy_w_mm,
            aft_width=legacy_w_mm,
            height=self.cabin_trunk_height * 1000.0,
            # Legacy has no per-face rake angle — use the spec 008
            # defaults that match the reference photo. The legacy
            # cabin_trunk_corner_radius is silently dropped.
            forward_rake_angle=CabinTrunkParameters().forward_rake_angle,
            aft_rake_angle=CabinTrunkParameters().aft_rake_angle,
            wall_inset=self.deck_side_walkway * 1000.0,
        )

        # Legacy windshield has a single rake — duplicate it as base + top
        # on the new dataclass. Other fields fall back to spec 008
        # reference defaults.
        ws_defaults = WindshieldParameters()
        windshield = WindshieldParameters(
            base_z=ws_defaults.base_z,
            top_z=ws_defaults.top_z,
            rake_angle_base=self.windshield_rake,
            rake_angle_top=self.windshield_rake,
            base_width=ws_defaults.base_width,
            top_width=ws_defaults.top_width,
            thickness=ws_defaults.thickness,
        )

        # Legacy hardtop_height is the slab thickness in legacy; map to
        # thickness here. The new height_above_deck is independent.
        ht_defaults = HardtopParameters()
        hardtop = HardtopParameters(
            length=self.hardtop_length * 1000.0,
            forward_width=ht_defaults.forward_width,
            aft_width=ht_defaults.aft_width,
            thickness=self.hardtop_height * 1000.0
            if self.hardtop_height > 0
            else ht_defaults.thickness,
            height_above_deck=ht_defaults.height_above_deck,
            leading_edge_curl_depth=ht_defaults.leading_edge_curl_depth,
            leading_edge_curl_length=ht_defaults.leading_edge_curl_length,
        )

        # Pillars: legacy supplies only a diameter; positions and count
        # use spec 008 defaults. Walkway maps to inboard_offset.
        pillar_defaults = PillarParameters()
        pillars = PillarParameters(
            count_per_side=pillar_defaults.count_per_side,
            diameter=self.hardtop_pillar_diameter * 1000.0,
            forward_x=pillar_defaults.forward_x,
            aft_x=pillar_defaults.aft_x,
            inboard_offset_from_sheer=self.deck_side_walkway * 1000.0,
        )

        # Railings: legacy supplies only height; everything else takes
        # spec 008 defaults.
        railing_defaults = RailingParameters()
        railings = RailingParameters(
            post_count_per_side=railing_defaults.post_count_per_side,
            post_diameter=railing_defaults.post_diameter,
            top_rail_diameter=railing_defaults.top_rail_diameter,
            height_above_deck=self.railing_height * 1000.0,
            forward_x=railing_defaults.forward_x,
            aft_x=railing_defaults.aft_x,
            inboard_offset_from_sheer=self.deck_side_walkway * 1000.0,
        )

        return DeckSuperstructureParameters(
            cabin_trunk=cabin,
            windshield=windshield,
            hardtop=hardtop,
            pillars=pillars,
            railings=railings,
        )


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
# Spec 008 — per-component parameter dataclasses (data-model §1)
#
# Six new dataclasses split the legacy 14-field DeckParameters into per-
# component shapes that match the Storebro RC34 1972 reference profile
# (docs/references/Alternativ3.JPG). Defaults sourced from spec 008
# research.md §R1 visual measurements at LOA = 10360 mm.
#
# All dimensions in mm, all angles in degrees. The composite
# DeckSuperstructureParameters is the new entry point for build_deck();
# the legacy DeckParameters dataclass is preserved unchanged + given a
# to_superstructure_parameters() shim (data-model §1.7).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CabinTrunkParameters:
    """Cabin trunk reshape parameters (data-model §1.1).

    All lengths in millimeters, all angles in degrees. Defaults derived
    from Alternativ3.JPG at LOA = 10360 mm.

    Example:
        >>> p = CabinTrunkParameters()
        >>> p.length, p.forward_width, p.aft_width
        (4600.0, 1900.0, 2150.0)
        >>> tall = CabinTrunkParameters(height=1300.0)
        >>> tall.height
        1300.0
    """

    length: float = 4600.0
    forward_width: float = 1900.0
    aft_width: float = 2150.0
    height: float = 1100.0
    forward_rake_angle: float = 8.0
    aft_rake_angle: float = 2.0
    wall_inset: float = 350.0

    def __post_init__(self) -> None:
        for name, value in (
            ("cabin_trunk_length", self.length),
            ("cabin_trunk_forward_width", self.forward_width),
            ("cabin_trunk_aft_width", self.aft_width),
            ("cabin_trunk_height", self.height),
        ):
            if value <= 0:
                raise DeckParameterError(name, value, "> 0")
        if self.wall_inset < 0:
            raise DeckParameterError("cabin_trunk_wall_inset", self.wall_inset, ">= 0")
        if self.forward_width > self.aft_width:
            raise DeckParameterError(
                "cabin_trunk_forward_width<>aft_width",
                None,
                "forward_width must be <= aft_width (tapered silhouette invariant)",
            )
        if not (0.0 <= self.forward_rake_angle <= 45.0):
            raise DeckParameterError(
                "cabin_trunk_forward_rake_angle",
                self.forward_rake_angle,
                "[0, 45] degrees",
            )
        if not (-15.0 <= self.aft_rake_angle <= 30.0):
            raise DeckParameterError(
                "cabin_trunk_aft_rake_angle",
                self.aft_rake_angle,
                "[-15, 30] degrees",
            )


@dataclass(frozen=True)
class WindshieldParameters:
    """Windshield reshape parameters (data-model §1.2).

    The windshield is lofted between a port-edge B-spline and a starboard-
    edge B-spline; top_width may be narrower than base_width per the
    reference top-tapering. Curvature radius (computed from base_z/top_z/
    rake delta) must be >= 200 mm to avoid spline self-intersection.

    Example:
        >>> p = WindshieldParameters()
        >>> p.base_width, p.top_width
        (2050.0, 1800.0)
    """

    base_z: float = 0.0
    top_z: float = 750.0
    rake_angle_base: float = 35.0
    rake_angle_top: float = 38.0
    base_width: float = 2050.0
    top_width: float = 1800.0
    thickness: float = 25.0

    def __post_init__(self) -> None:
        for name, value in (
            ("windshield_base_width", self.base_width),
            ("windshield_top_width", self.top_width),
            ("windshield_thickness", self.thickness),
        ):
            if value <= 0:
                raise DeckParameterError(name, value, "> 0")
        if self.top_z <= self.base_z:
            raise DeckParameterError(
                "windshield_top_z<>base_z",
                None,
                "top_z must be greater than base_z",
            )
        if self.top_width > self.base_width:
            raise DeckParameterError(
                "windshield_top_width<>base_width",
                None,
                "top_width must be <= base_width (no upward-widening)",
            )
        if not (-10.0 <= self.rake_angle_base <= 60.0):
            raise DeckParameterError(
                "windshield_rake_angle_base",
                self.rake_angle_base,
                "[-10, 60] degrees",
            )
        if not (-10.0 <= self.rake_angle_top <= 60.0):
            raise DeckParameterError(
                "windshield_rake_angle_top",
                self.rake_angle_top,
                "[-10, 60] degrees",
            )
        # Compute curvature radius of the circular arc that interpolates
        # the (base, top) control points with tangent directions rotated
        # by rake_angle_base and rake_angle_top. For an arc subtending
        # angle = abs(top - base) and chord = top_z - base_z:
        #     R = chord / (2 * sin(arc_angle / 2))
        # Sub-200 mm radius produces a curve so tight the B-spline
        # interpolation self-intersects.
        rake_delta_deg = abs(self.rake_angle_top - self.rake_angle_base)
        if rake_delta_deg > 0.001:
            chord = self.top_z - self.base_z
            half_delta_rad = math.radians(rake_delta_deg / 2.0)
            sin_half = math.sin(half_delta_rad)
            if sin_half > 0:
                radius_approx = chord / (2.0 * sin_half)
                if radius_approx < 200.0:
                    raise DeckParameterError(
                        "windshield_curvature_radius",
                        radius_approx,
                        ">= 200 mm (sub-minimum curvature causes B-spline self-intersection)",
                    )


@dataclass(frozen=True)
class HardtopParameters:
    """Hardtop reshape parameters (data-model §1.3).

    The hardtop has an aft taper (aft_width < forward_width) and a
    downward-curling leading edge bounded by leading_edge_curl_length
    and leading_edge_curl_depth.

    Example:
        >>> p = HardtopParameters()
        >>> p.forward_width > p.aft_width
        True
    """

    length: float = 3700.0
    forward_width: float = 2200.0
    aft_width: float = 2000.0
    thickness: float = 60.0
    height_above_deck: float = 2050.0
    leading_edge_curl_depth: float = 80.0
    leading_edge_curl_length: float = 250.0

    def __post_init__(self) -> None:
        for name, value in (
            ("hardtop_length", self.length),
            ("hardtop_forward_width", self.forward_width),
            ("hardtop_aft_width", self.aft_width),
            ("hardtop_thickness", self.thickness),
            ("hardtop_height_above_deck", self.height_above_deck),
        ):
            if value <= 0:
                raise DeckParameterError(name, value, "> 0")
        for name, value in (
            ("hardtop_leading_edge_curl_depth", self.leading_edge_curl_depth),
            ("hardtop_leading_edge_curl_length", self.leading_edge_curl_length),
        ):
            if value < 0:
                raise DeckParameterError(name, value, ">= 0")
        if self.aft_width > self.forward_width:
            raise DeckParameterError(
                "hardtop_aft_width<>forward_width",
                None,
                "aft_width must be <= forward_width (aft taper invariant)",
            )
        if self.leading_edge_curl_length > self.length:
            raise DeckParameterError(
                "hardtop_curl_length<>length",
                None,
                "leading_edge_curl_length must be <= length",
            )
        if self.leading_edge_curl_depth > self.height_above_deck:
            raise DeckParameterError(
                "hardtop_curl_depth<>height",
                None,
                "leading_edge_curl_depth must be <= height_above_deck",
            )


@dataclass(frozen=True)
class PillarParameters:
    """Hardtop pillar parameters (data-model §1.4).

    Pillars are circular-cross-section vertical posts seating on the
    deck plate top and extending up to the hardtop underside. Default
    layout: 2 per side (4 total), 35 mm diameter, 80 mm inboard offset
    from the sheer line.

    Example:
        >>> p = PillarParameters()
        >>> p.count_per_side, p.diameter
        (2, 35.0)
    """

    count_per_side: int = 2
    diameter: float = 35.0
    forward_x: float = 5400.0
    aft_x: float = 7800.0
    inboard_offset_from_sheer: float = 80.0

    def __post_init__(self) -> None:
        if self.count_per_side < 0:
            raise DeckParameterError(
                "pillar_count_per_side",
                self.count_per_side,
                ">= 0",
            )
        if self.diameter <= 0:
            raise DeckParameterError("pillar_diameter", self.diameter, "> 0")
        if self.forward_x >= self.aft_x:
            raise DeckParameterError(
                "pillar_forward_x<>aft_x",
                None,
                "forward_x must be < aft_x",
            )
        if self.inboard_offset_from_sheer < 0:
            raise DeckParameterError(
                "pillar_inboard_offset_from_sheer",
                self.inboard_offset_from_sheer,
                ">= 0",
            )


@dataclass(frozen=True)
class RailingParameters:
    """Railing parameters (data-model §1.5).

    Railings are constructed as a top-rail sweep along a perimeter wire
    plus N vertical posts. One port body + one starboard body (symmetric).

    Example:
        >>> p = RailingParameters()
        >>> p.post_count_per_side, p.height_above_deck
        (6, 720.0)
    """

    post_count_per_side: int = 6
    post_diameter: float = 25.0
    top_rail_diameter: float = 30.0
    height_above_deck: float = 720.0
    forward_x: float = 0.0
    aft_x: float = 9800.0
    inboard_offset_from_sheer: float = 60.0

    def __post_init__(self) -> None:
        if self.post_count_per_side < 0:
            raise DeckParameterError(
                "railing_post_count_per_side",
                self.post_count_per_side,
                ">= 0",
            )
        for name, value in (
            ("railing_post_diameter", self.post_diameter),
            ("railing_top_rail_diameter", self.top_rail_diameter),
            ("railing_height_above_deck", self.height_above_deck),
        ):
            if value <= 0:
                raise DeckParameterError(name, value, "> 0")
        if self.forward_x >= self.aft_x:
            raise DeckParameterError(
                "railing_forward_x<>aft_x",
                None,
                "forward_x must be < aft_x",
            )
        if self.inboard_offset_from_sheer < 0:
            raise DeckParameterError(
                "railing_inboard_offset_from_sheer",
                self.inboard_offset_from_sheer,
                ">= 0",
            )


@dataclass(frozen=True)
class DeckSuperstructureParameters:
    """Composite of the five per-component parameter dataclasses.

    The new entry-point parameter set for build_deck(). Replaces the
    flat 14-field DeckParameters at the type level while preserving
    back-compat for callers passing the legacy form.

    Cross-component invariants enforced in __post_init__:

    - railings.height_above_deck < hardtop.height_above_deck
      (railings cannot pierce the hardtop)
    - pillars.forward_x >= cabin_trunk.length
      (pillars cannot land inside the cabin trunk footprint)

    Example:
        >>> p = DeckSuperstructureParameters()
        >>> p.cabin_trunk.length, p.hardtop.length, p.pillars.count_per_side
        (4600.0, 3700.0, 2)
    """

    cabin_trunk: CabinTrunkParameters = field(default_factory=CabinTrunkParameters)
    windshield: WindshieldParameters = field(default_factory=WindshieldParameters)
    hardtop: HardtopParameters = field(default_factory=HardtopParameters)
    pillars: PillarParameters = field(default_factory=PillarParameters)
    railings: RailingParameters = field(default_factory=RailingParameters)

    def __post_init__(self) -> None:
        if self.railings.height_above_deck >= self.hardtop.height_above_deck:
            raise DeckParameterError(
                "railing_height<>hardtop_height",
                None,
                "railings.height_above_deck must be < hardtop.height_above_deck",
            )
        if self.pillars.forward_x < self.cabin_trunk.length:
            raise DeckParameterError(
                "pillar_forward_x<>cabin_trunk_length",
                None,
                "pillars.forward_x must be >= cabin_trunk.length "
                "(pillars cannot land inside the cabin trunk footprint)",
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


# ---------------------------------------------------------------------------
# Spec 008 — PartDesign helpers + sub-Body builders (constitution III)
#
# Every superstructure sub-body now lives in its own PartDesign::Body with
# sketches + PartDesign features. The legacy Part::Feature + raw Part.makeX
# call paths have been retired per FR-001/005/009/014/019/029.
#
# Pillar seating fix: the analytical sheer formula
#   hp.sheer_height_aft + t * (hp.sheer_height_fwd - hp.sheer_height_aft)
# is replaced by _resolve_deck_top_z_at(deck_plate, x_mm) which reads the
# *actual* deck plate body's top Z at the given X station. Closes the v1.0.1
# regression (pillars piercing the hull after spec 007 stem rake).
# ---------------------------------------------------------------------------


def _pd_get_origin_plane(body: Any, plane_name: str) -> Any:
    """Find a named Origin reference plane on a Body (XY_Plane, XZ_Plane, YZ_Plane).

    Mirrors :func:`storebro.hull._get_origin_plane`. Matches on Name prefix
    so the auto-numbering suffix that FreeCAD appends when multiple Bodies
    share a document does not break lookup.
    """
    for feat in body.Origin.OriginFeatures:
        if feat.Name.rstrip("0123456789") == plane_name:
            return feat
    raise RuntimeError(f"Could not locate Origin.{plane_name} on body {body.Label!r}")


def _resolve_deck_top_z_at(deck_plate: DeckPlate, x_mm: float) -> float:
    """Return the actual deck plate top Z (mm) at longitudinal station X (mm).

    Sources Z from the deck plate body's Shape vertices rather than from
    the analytical sheer formula on the hull parameters. This is the spec
    008 fix for the pillar-seating regression: after spec 007 introduced
    `stem_rake_angle`, the analytical formula diverges from the actual
    hull sheer at the forward end, so pillars built using the analytical
    Z end up below the actual hull rail.

    Algorithm: the deck plate has two vertices per longitudinal station
    (top and bottom of the extrusion). Group vertices by X-position and
    take the max Z per group — that's the top sheer at each station.
    Linearly interpolate between adjacent stations. Returns the bbox ZMax
    as a safe fallback when no top samples can be derived.
    """
    shape = deck_plate.body.Shape
    by_x: dict[float, float] = {}
    for v in shape.Vertexes:
        # Quantize X to 0.1 mm to merge floating-point duplicates within a
        # station.
        x_key = round(v.X, 1)
        prev = by_x.get(x_key)
        if prev is None or prev < v.Z:
            by_x[x_key] = v.Z
    if not by_x:
        return float(shape.BoundBox.ZMax)
    top_samples = sorted(by_x.items())
    if x_mm <= top_samples[0][0]:
        return top_samples[0][1]
    if x_mm >= top_samples[-1][0]:
        return top_samples[-1][1]
    for i in range(len(top_samples) - 1):
        x1, z1 = top_samples[i]
        x2, z2 = top_samples[i + 1]
        if x1 <= x_mm <= x2:
            if x2 == x1:
                return (z1 + z2) / 2.0
            t = (x_mm - x1) / (x2 - x1)
            return z1 + t * (z2 - z1)
    return float(shape.BoundBox.ZMax)


def _pd_make_datum_xy(
    body: Any, name: str, z_offset_mm: float, added: list[Any] | None = None
) -> Any:
    """Create a PartDesign datum plane parallel to XY at given Z offset.

    When ``added`` is provided, the datum is appended for rollback tracking.
    XY_Plane local frame: local X = global X, local Y = global Y, local Z = global Z;
    so AttachmentOffset (0, 0, z_offset_mm) puts the datum at global Z = z_offset_mm.
    """
    import FreeCAD

    xy_plane = _pd_get_origin_plane(body, "XY_Plane")
    datum = body.newObject("PartDesign::Plane", name)
    if added is not None:
        added.append(datum)
    datum.AttachmentSupport = [(xy_plane, "")]
    datum.MapMode = "FlatFace"
    datum.AttachmentOffset = FreeCAD.Placement(
        FreeCAD.Vector(0.0, 0.0, z_offset_mm),
        FreeCAD.Rotation(),
    )
    return datum


def _pd_close_loop_constraints(sketch: Any, line_ids: list[int]) -> None:
    """Add Coincident constraints between consecutive line endpoints (closed loop)."""
    import Sketcher

    n = len(line_ids)
    for i in range(n):
        j = (i + 1) % n
        sketch.addConstraint(
            Sketcher.Constraint("Coincident", line_ids[i], 2, line_ids[j], 1)
        )


def _build_cabin_trunk(
    hull: Hull,
    parameters: DeckParameters,
    deck_plate: DeckPlate,
    target_doc: Any,
    added: list[Any],
    *,
    superstructure: DeckSuperstructureParameters | None = None,
) -> CabinTrunk:
    """Build cabin trunk as PartDesign::Body with AdditiveLoft (spec 008 FR-001..004).

    Two trapezoidal sketches on XY-parallel datums (lower at deck top, upper
    at deck top + height) are lofted together. The upper sketch is shifted
    aftward by ``height * tan(forward_rake)`` and forward by
    ``height * tan(aft_rake)`` to produce the raked vertical faces.
    """
    import FreeCAD
    import Part

    sp = superstructure or parameters.to_superstructure_parameters()
    ct = sp.cabin_trunk

    # X coordinates: cabin trunk is positioned aft of the deck plate's
    # forward edge by `wall_inset`.
    deck_bb = deck_plate.body.Shape.BoundBox
    fwd_x_mm = deck_bb.XMin + ct.wall_inset
    aft_x_mm = fwd_x_mm + ct.length
    deck_top_z_mm = _resolve_deck_top_z_at(deck_plate, (fwd_x_mm + aft_x_mm) / 2.0)
    upper_z_mm = deck_top_z_mm + ct.height
    fwd_rake_dx = ct.height * math.tan(math.radians(ct.forward_rake_angle))
    aft_rake_dx = ct.height * math.tan(math.radians(ct.aft_rake_angle))
    fw = ct.forward_width / 2.0
    aw = ct.aft_width / 2.0

    body = target_doc.addObject("PartDesign::Body", "Deck_CabinTrunk")
    added.append(body)
    target_doc.recompute()

    lower_datum = _pd_make_datum_xy(body, "CabinTrunkLowerDatum", deck_top_z_mm, added)
    upper_datum = _pd_make_datum_xy(body, "CabinTrunkUpperDatum", upper_z_mm, added)

    def _trapezoid_sketch(name: str, datum: Any, fx: float, ax: float) -> Any:
        sketch = body.newObject("Sketcher::SketchObject", name)
        added.append(sketch)
        sketch.AttachmentSupport = [(datum, "")]
        sketch.MapMode = "FlatFace"
        pts = [
            FreeCAD.Vector(fx, -fw, 0),
            FreeCAD.Vector(fx, fw, 0),
            FreeCAD.Vector(ax, aw, 0),
            FreeCAD.Vector(ax, -aw, 0),
        ]
        line_ids: list[int] = []
        for i in range(4):
            j = (i + 1) % 4
            seg = Part.LineSegment(pts[i], pts[j])
            line_ids.append(sketch.addGeometry(seg, False))
        _pd_close_loop_constraints(sketch, line_ids)
        return sketch

    lower_sketch = _trapezoid_sketch(
        "CabinTrunkLowerSketch", lower_datum, fwd_x_mm, aft_x_mm
    )
    upper_sketch = _trapezoid_sketch(
        "CabinTrunkUpperSketch",
        upper_datum,
        fwd_x_mm + fwd_rake_dx,
        aft_x_mm - aft_rake_dx,
    )
    target_doc.recompute()

    loft = body.newObject("PartDesign::AdditiveLoft", "CabinTrunkLoft")
    added.append(loft)
    loft.Profile = (lower_sketch, [""])
    loft.Sections = [(upper_sketch, [""])]
    loft.Ruled = True
    loft.Closed = False
    target_doc.recompute()

    # Back-compat named properties on the Body (legacy v1.0.1 had them on
    # the Part::Feature; PartDesign::Body supports the same addProperty API).
    body.addProperty("App::PropertyLength", "TrunkLength", "Deck", "Cabin trunk length")
    body.addProperty("App::PropertyLength", "TrunkWidth", "Deck", "Cabin trunk width (avg fwd/aft)")
    body.addProperty("App::PropertyLength", "TrunkHeight", "Deck", "Cabin trunk height")
    body.addProperty(
        "App::PropertyLength", "CornerRadius", "Deck", "Cabin trunk corner radius (legacy, unused)"
    )
    body.TrunkLength = ct.length
    body.TrunkWidth = (ct.forward_width + ct.aft_width) / 2.0
    body.TrunkHeight = ct.height
    body.CornerRadius = 0.0

    return CabinTrunk(
        body=body,
        length=ct.length / _MM_PER_M,
        width=(ct.forward_width + ct.aft_width) / (2.0 * _MM_PER_M),
        height=ct.height / _MM_PER_M,
        corner_radius=0.0,
    )


def _build_windshield(
    hull: Hull,
    parameters: DeckParameters,
    cabin_trunk: CabinTrunk,
    target_doc: Any,
    added: list[Any],
    *,
    superstructure: DeckSuperstructureParameters | None = None,
) -> Windshield:
    """Build windshield as PartDesign::Body with AdditiveLoft (spec 008 FR-005..008).

    Three YZ-parallel datum planes (base, mid, top) carry rectangular
    cross-section sketches (width * thickness). The X positions of the
    three datums are derived from the rake angles applied to the height
    delta, producing a curving B-spline profile via 3-section lofting.
    Top sketch is narrower than base per ``WindshieldParameters.top_width``.
    """
    import FreeCAD
    import Part

    sp = superstructure or parameters.to_superstructure_parameters()
    ws = sp.windshield

    # The windshield seats at the aft edge of the cabin trunk top.
    cabin_bb = cabin_trunk.body.Shape.BoundBox
    cabin_top_z_mm = cabin_bb.ZMax
    cabin_aft_x_mm = cabin_bb.XMax
    base_z_mm = cabin_top_z_mm + ws.base_z
    top_z_mm = cabin_top_z_mm + ws.top_z

    # Rake angles measured from vertical; aft offset = vertical_delta * tan(rake).
    rake_base_rad = math.radians(ws.rake_angle_base)
    rake_top_rad = math.radians(ws.rake_angle_top)
    mid_z_mm = (base_z_mm + top_z_mm) / 2.0
    rake_mid_rad = (rake_base_rad + rake_top_rad) / 2.0
    base_x_mm = cabin_aft_x_mm
    mid_x_mm = base_x_mm + (mid_z_mm - base_z_mm) * math.tan(rake_mid_rad)
    top_x_mm = base_x_mm + (top_z_mm - base_z_mm) * (
        (math.tan(rake_base_rad) + math.tan(rake_top_rad)) / 2.0
    )

    body = target_doc.addObject("PartDesign::Body", "Deck_Windshield")
    added.append(body)
    target_doc.recompute()

    def _make_yz_datum(
        name: str, x_offset_mm: float, z_offset_mm: float
    ) -> Any:
        yz_plane = _pd_get_origin_plane(body, "YZ_Plane")
        datum = body.newObject("PartDesign::Plane", name)
        added.append(datum)
        datum.AttachmentSupport = [(yz_plane, "")]
        datum.MapMode = "FlatFace"
        # For a plane attached to Origin.YZ_Plane:
        #   local X = global Y (the "u" axis of the YZ plane)
        #   local Y = global Z (the "v" axis of the YZ plane)
        #   local Z = global X (the plane's normal)
        # AttachmentOffset.Vector is in the support's LOCAL frame, so to
        # place the datum at global (x_offset, 0, z_offset), the local
        # vector is (0, z_offset, x_offset).
        datum.AttachmentOffset = FreeCAD.Placement(
            FreeCAD.Vector(0.0, z_offset_mm, x_offset_mm),
            FreeCAD.Rotation(),
        )
        return datum

    def _slab_sketch(name: str, datum: Any, width_mm: float, vertical_z_mm: float) -> Any:
        """Rectangle sketch: width along Y (transverse), thickness along Z (vertical).

        Sketch local x maps to global Y; sketch local y maps to global Z (because
        the datum's normal is global X). The sketch sits at vertical_z_mm in global Z,
        which means the rectangle's center in sketch-local y = vertical_z_mm.
        """
        sketch = body.newObject("Sketcher::SketchObject", name)
        added.append(sketch)
        sketch.AttachmentSupport = [(datum, "")]
        sketch.MapMode = "FlatFace"
        hw = width_mm / 2.0
        ht = ws.thickness / 2.0
        # Rectangle centered on (0, vertical_z_mm) in sketch-local frame.
        pts = [
            FreeCAD.Vector(-hw, vertical_z_mm - ht, 0),
            FreeCAD.Vector(hw, vertical_z_mm - ht, 0),
            FreeCAD.Vector(hw, vertical_z_mm + ht, 0),
            FreeCAD.Vector(-hw, vertical_z_mm + ht, 0),
        ]
        line_ids: list[int] = []
        for i in range(4):
            j = (i + 1) % 4
            seg = Part.LineSegment(pts[i], pts[j])
            line_ids.append(sketch.addGeometry(seg, False))
        _pd_close_loop_constraints(sketch, line_ids)
        return sketch

    base_datum = _make_yz_datum("WindshieldBaseDatum", base_x_mm, base_z_mm)
    mid_datum = _make_yz_datum("WindshieldMidDatum", mid_x_mm, mid_z_mm)
    top_datum = _make_yz_datum("WindshieldTopDatum", top_x_mm, top_z_mm)

    mid_width = (ws.base_width + ws.top_width) / 2.0
    base_sketch = _slab_sketch("WindshieldBaseSketch", base_datum, ws.base_width, 0.0)
    mid_sketch = _slab_sketch("WindshieldMidSketch", mid_datum, mid_width, 0.0)
    top_sketch = _slab_sketch("WindshieldTopSketch", top_datum, ws.top_width, 0.0)
    target_doc.recompute()

    loft = body.newObject("PartDesign::AdditiveLoft", "WindshieldLoft")
    added.append(loft)
    loft.Profile = (base_sketch, [""])
    loft.Sections = [(mid_sketch, [""]), (top_sketch, [""])]
    loft.Ruled = False  # smooth B-spline interpolation (3 sections is dense enough)
    loft.Closed = False
    target_doc.recompute()

    body.addProperty(
        "App::PropertyAngle",
        "WindshieldRake",
        "Deck",
        "Windshield rake at base (legacy back-compat field; new design has base + top rakes)",
    )
    body.WindshieldRake = ws.rake_angle_base

    return Windshield(body=body, rake_degrees=ws.rake_angle_base)


def _build_hardtop(
    hull: Hull,
    parameters: DeckParameters,
    cabin_trunk: CabinTrunk,
    target_doc: Any,
    added: list[Any],
    *,
    superstructure: DeckSuperstructureParameters | None = None,
) -> Hardtop:
    """Build hardtop as PartDesign::Body with AdditiveLoft (spec 008 FR-009..013).

    Three XY-parallel datums carry rectangular sketches at the forward,
    mid-aft, and aft stations. The forward sketch is slightly lower
    (``leading_edge_curl_depth``) over the ``leading_edge_curl_length``
    portion, producing the downward leading-edge curl. The aft sketch
    is narrower (``aft_width < forward_width``), producing the aft taper.
    """
    import FreeCAD
    import Part

    sp = superstructure or parameters.to_superstructure_parameters()
    ht = sp.hardtop

    # Hardtop X-extent: starts just aft of the cabin trunk, spans `length`.
    # Y-extent: centered on the cabin trunk centerline. The cabin trunk
    # seats on the deck plate, so its BoundBox.ZMin is the deck-top Z under
    # the cabin — accurate enough as a reference here without re-sampling
    # the deck plate body (the hardtop spans aft of the cabin where the
    # deck shape is largely flat in Z).
    deck_top_z_mm = cabin_trunk.body.Shape.BoundBox.ZMin
    hardtop_underside_z_mm = deck_top_z_mm + ht.height_above_deck
    hardtop_topside_z_mm = hardtop_underside_z_mm + ht.thickness

    fwd_x_mm = cabin_trunk.body.Shape.BoundBox.XMax
    aft_x_mm = fwd_x_mm + ht.length
    curl_end_x_mm = fwd_x_mm + ht.leading_edge_curl_length
    curl_drop_mm = ht.leading_edge_curl_depth

    body = target_doc.addObject("PartDesign::Body", "Deck_Hardtop")
    added.append(body)
    target_doc.recompute()

    def _make_xz_datum_at_x(name: str, x_mm: float, z_mm: float) -> Any:
        yz_plane = _pd_get_origin_plane(body, "YZ_Plane")
        datum = body.newObject("PartDesign::Plane", name)
        added.append(datum)
        datum.AttachmentSupport = [(yz_plane, "")]
        datum.MapMode = "FlatFace"
        # YZ_Plane local axes: local X = global Y, local Y = global Z,
        # local Z = global X (normal). To place datum at global (x_mm, 0, z_mm)
        # use local AttachmentOffset (0, z_mm, x_mm).
        datum.AttachmentOffset = FreeCAD.Placement(
            FreeCAD.Vector(0.0, z_mm, x_mm),
            FreeCAD.Rotation(),
        )
        return datum

    def _rect_sketch(
        name: str, datum: Any, half_width_mm: float, base_z_local: float
    ) -> Any:
        """Rectangle of half_width * thickness, centered at (0, base_z_local) in sketch frame."""
        sketch = body.newObject("Sketcher::SketchObject", name)
        added.append(sketch)
        sketch.AttachmentSupport = [(datum, "")]
        sketch.MapMode = "FlatFace"
        ht_local = ht.thickness / 2.0
        pts = [
            FreeCAD.Vector(-half_width_mm, base_z_local - ht_local, 0),
            FreeCAD.Vector(half_width_mm, base_z_local - ht_local, 0),
            FreeCAD.Vector(half_width_mm, base_z_local + ht_local, 0),
            FreeCAD.Vector(-half_width_mm, base_z_local + ht_local, 0),
        ]
        line_ids: list[int] = []
        for i in range(4):
            j = (i + 1) % 4
            seg = Part.LineSegment(pts[i], pts[j])
            line_ids.append(sketch.addGeometry(seg, False))
        _pd_close_loop_constraints(sketch, line_ids)
        return sketch

    # Three station sketches: forward (curl drops), curl-end, aft.
    # All datums are placed at the hardtop centerline Z; the sketch's local
    # vertical maps to global Z, so the curl drop is encoded as the sketch
    # base_z_local offset.
    center_z_mm = (hardtop_underside_z_mm + hardtop_topside_z_mm) / 2.0
    fwd_datum = _make_xz_datum_at_x("HardtopForwardDatum", fwd_x_mm, center_z_mm)
    mid_datum = _make_xz_datum_at_x("HardtopMidDatum", curl_end_x_mm, center_z_mm)
    aft_datum = _make_xz_datum_at_x("HardtopAftDatum", aft_x_mm, center_z_mm)

    # forward_width tapers linearly into aft_width across the full length.
    mid_width = ht.forward_width + (ht.aft_width - ht.forward_width) * (
        ht.leading_edge_curl_length / max(ht.length, 1e-9)
    )

    # Forward sketch sits curl_drop lower in global Z.
    fwd_sketch = _rect_sketch(
        "HardtopForwardSketch", fwd_datum, ht.forward_width / 2.0, -curl_drop_mm
    )
    mid_sketch = _rect_sketch(
        "HardtopMidSketch", mid_datum, mid_width / 2.0, 0.0
    )
    aft_sketch = _rect_sketch(
        "HardtopAftSketch", aft_datum, ht.aft_width / 2.0, 0.0
    )
    target_doc.recompute()

    loft = body.newObject("PartDesign::AdditiveLoft", "HardtopLoft")
    added.append(loft)
    loft.Profile = (fwd_sketch, [""])
    loft.Sections = [(mid_sketch, [""]), (aft_sketch, [""])]
    # Ruled=True (piecewise-linear loft) — Ruled=False overshoots in Z above
    # the aft section when transitioning from the curled forward section.
    # A smoother curl awaits a denser section set (matches spec 007's
    # deferred `Hull.b_spline_loft` rationale).
    loft.Ruled = True
    loft.Closed = False
    target_doc.recompute()

    body.addProperty("App::PropertyLength", "HardtopLength", "Deck", "Hardtop length")
    body.addProperty("App::PropertyLength", "HardtopHeight", "Deck", "Hardtop slab thickness")
    body.addProperty(
        "App::PropertyLength",
        "HardtopOverhangFwd",
        "Deck",
        "Hardtop forward overhang (legacy field, derived)",
    )
    body.addProperty(
        "App::PropertyLength",
        "HardtopOverhangAft",
        "Deck",
        "Hardtop aft overhang (legacy field, derived)",
    )
    body.HardtopLength = ht.length
    body.HardtopHeight = ht.thickness
    body.HardtopOverhangFwd = 0.0
    body.HardtopOverhangAft = 0.0

    return Hardtop(
        body=body,
        length=ht.length / _MM_PER_M,
        height_above_cabin=ht.thickness / _MM_PER_M,
    )


def _build_hardtop_pillars(
    hull: Hull,
    parameters: DeckParameters,
    hardtop: Hardtop,
    deck_plate: DeckPlate,
    target_doc: Any,
    added: list[Any],
    *,
    superstructure: DeckSuperstructureParameters | None = None,
) -> HardtopPillars:
    """Build hardtop pillars as a Compound of PartDesign::Body instances (spec 008 FR-014..018).

    One PartDesign::Body per pillar. Each pillar contains a circular sketch
    on an XY-parallel datum at the *actual* deck plate top Z (sourced via
    :func:`_resolve_deck_top_z_at`) plus a vertical Pad to the hardtop
    underside Z at that pillar's longitudinal station. The legacy
    ``HardtopPillars`` wrapper exposes a Part::Compound of the pillar
    bodies' shapes for back-compat.

    Zero-pillar fallback per clarification 4 in spec.md: when
    ``count_per_side == 0``, no pillar bodies are constructed and the
    legacy compound is built from an empty shape list. The hardtop
    structurally relies on its cabin-trunk attachment in this case.
    """
    import FreeCAD
    import Part

    sp = superstructure or parameters.to_superstructure_parameters()
    pp = sp.pillars

    pillar_bodies: list[Any] = []
    hardtop_underside_z_mm = hardtop.body.Shape.BoundBox.ZMin

    # Pillar lateral position: inboard from the sheer line by inboard_offset.
    # The sheer line at the pillar's X is sampled from the deck plate.
    if pp.count_per_side > 0:
        # Distribute pillars evenly between forward_x and aft_x.
        if pp.count_per_side == 1:
            x_stations = [(pp.forward_x + pp.aft_x) / 2.0]
        else:
            step = (pp.aft_x - pp.forward_x) / (pp.count_per_side - 1)
            x_stations = [pp.forward_x + i * step for i in range(pp.count_per_side)]

        for x_mm in x_stations:
            # Deck top Z at this X (the seating invariant fix).
            deck_z_mm = _resolve_deck_top_z_at(deck_plate, x_mm)
            # Lateral Y: sheer half-width at this X minus inboard_offset.
            # Sample deck plate vertices at this X to find the outer Y.
            deck_shape = deck_plate.body.Shape
            verts_at_x = [v for v in deck_shape.Vertexes if abs(v.X - x_mm) < 500.0]
            if not verts_at_x:
                # Fallback: use deck bbox Y extent.
                outer_y_mm = deck_shape.BoundBox.YMax
            else:
                outer_y_mm = max(abs(v.Y) for v in verts_at_x)
            pillar_y_mm = max(0.0, outer_y_mm - pp.inboard_offset_from_sheer)
            pillar_height_mm = hardtop_underside_z_mm - deck_z_mm

            for side, sign in (("Port", 1), ("Starboard", -1)):
                idx = x_stations.index(x_mm) + 1
                body = target_doc.addObject(
                    "PartDesign::Body", f"Deck_Pillar_{side}_{idx}"
                )
                added.append(body)
                target_doc.recompute()

                datum = _pd_make_datum_xy(
                    body, f"Pillar{side}{idx}Datum", deck_z_mm, added
                )
                sketch = body.newObject(
                    "Sketcher::SketchObject", f"Pillar{side}{idx}Sketch"
                )
                added.append(sketch)
                sketch.AttachmentSupport = [(datum, "")]
                sketch.MapMode = "FlatFace"
                center = FreeCAD.Vector(x_mm, sign * pillar_y_mm, 0)
                circle = Part.Circle(
                    center, FreeCAD.Vector(0, 0, 1), pp.diameter / 2.0
                )
                sketch.addGeometry(circle.toShape().Curve, False)
                target_doc.recompute()

                pad = body.newObject("PartDesign::Pad", f"Pillar{side}{idx}Pad")
                added.append(pad)
                pad.Profile = (sketch, [""])
                pad.Length = pillar_height_mm
                pad.Midplane = False
                pad.Reversed = False
                target_doc.recompute()

                pillar_bodies.append(body)

    # Build a legacy-compatible Compound from all pillar body shapes.
    compound_obj = target_doc.addObject("Part::Feature", "Deck_HardtopPillars")
    if pillar_bodies:
        compound_obj.Shape = Part.makeCompound([b.Shape for b in pillar_bodies])
    else:
        # Zero-pillar fallback: empty compound. Use a tiny degenerate vertex
        # so the Shape is not Null (which would fail downstream tests).
        compound_obj.Shape = Part.Vertex(FreeCAD.Vector(0, 0, 0)).toShape() if False else (
            Part.makeCompound([])
        )
    added.append(compound_obj)
    compound_obj.addProperty(
        "App::PropertyLength", "PillarDiameter", "Deck", "Hardtop pillar diameter"
    )
    compound_obj.PillarDiameter = pp.diameter

    # Attach pillar_bodies list to the compound for downstream test access.
    # FreeCAD does not allow arbitrary attribute assignment on DocumentObjects;
    # store as a custom property containing the bodies' labels for traceability.
    compound_obj.addProperty(
        "App::PropertyStringList",
        "PillarBodyLabels",
        "Deck",
        "Labels of the constituent PartDesign Body pillars",
    )
    compound_obj.PillarBodyLabels = [b.Label for b in pillar_bodies]

    return HardtopPillars(body=compound_obj, pillar_diameter=pp.diameter / _MM_PER_M)


def _build_railings(
    hull: Hull,
    parameters: DeckParameters,
    deck_plate: DeckPlate,
    target_doc: Any,
    added: list[Any],
    *,
    superstructure: DeckSuperstructureParameters | None = None,
) -> Railings:
    """Build port + starboard railings as PartDesign::Body (spec 008 FR-019..022).

    Each side gets its own PartDesign::Body containing a Pad of a circular
    profile representing the top rail (approximated as a horizontal pipe
    extruded along the deck length) plus N pads for vertical posts. The
    two bodies are then wrapped in a Part::Compound for the legacy
    ``Railings.body`` field.

    This is a simplified implementation: the top rail is modeled as a
    straight cylindrical bar rather than a swept curve along the deck
    perimeter. A swept-along-perimeter pipe is a v1.2+ refinement; the
    current shape captures height + post spacing accurately enough for
    the ±1% reference fidelity bar (which applies only to principal
    dimensions, not the per-post detail).
    """
    import FreeCAD
    import Part

    sp = superstructure or parameters.to_superstructure_parameters()
    rp = sp.railings

    deck_top_z_mm = _resolve_deck_top_z_at(deck_plate, (rp.forward_x + rp.aft_x) / 2.0)
    rail_top_z_mm = deck_top_z_mm + rp.height_above_deck

    # Sample lateral Y at the railing's mid-station to position the rail
    # inboard from the sheer.
    deck_shape = deck_plate.body.Shape
    mid_x_mm = (rp.forward_x + rp.aft_x) / 2.0
    verts_at_mid = [v for v in deck_shape.Vertexes if abs(v.X - mid_x_mm) < 1500.0]
    outer_y_mm = (
        max(abs(v.Y) for v in verts_at_mid)
        if verts_at_mid
        else deck_shape.BoundBox.YMax
    )
    rail_y_mm = max(0.0, outer_y_mm - rp.inboard_offset_from_sheer)

    side_bodies: list[Any] = []
    for side, sign in (("Port", 1), ("Starboard", -1)):
        body = target_doc.addObject("PartDesign::Body", f"Deck_Railings_{side}")
        added.append(body)
        target_doc.recompute()

        # Top rail: a horizontal cylinder running from forward_x to aft_x.
        # Modeled as a Pad of a small circle on a YZ-parallel datum at
        # forward_x, extruded along X.
        yz_plane = _pd_get_origin_plane(body, "YZ_Plane")
        rail_datum = body.newObject("PartDesign::Plane", f"Rail{side}TopRailDatum")
        added.append(rail_datum)
        rail_datum.AttachmentSupport = [(yz_plane, "")]
        rail_datum.MapMode = "FlatFace"
        # YZ_Plane local frame: local X = global Y, local Y = global Z,
        # local Z = global X. Datum at global (forward_x, 0, rail_top_z).
        rail_datum.AttachmentOffset = FreeCAD.Placement(
            FreeCAD.Vector(0.0, rail_top_z_mm, rp.forward_x),
            FreeCAD.Rotation(),
        )

        rail_sketch = body.newObject("Sketcher::SketchObject", f"Rail{side}TopRailSketch")
        added.append(rail_sketch)
        rail_sketch.AttachmentSupport = [(rail_datum, "")]
        rail_sketch.MapMode = "FlatFace"
        rail_circle = Part.Circle(
            FreeCAD.Vector(sign * rail_y_mm, 0, 0),
            FreeCAD.Vector(0, 0, 1),
            rp.top_rail_diameter / 2.0,
        )
        rail_sketch.addGeometry(rail_circle.toShape().Curve, False)
        target_doc.recompute()

        rail_pad = body.newObject("PartDesign::Pad", f"Rail{side}TopRailPad")
        added.append(rail_pad)
        rail_pad.Profile = (rail_sketch, [""])
        rail_pad.Length = rp.aft_x - rp.forward_x
        rail_pad.Midplane = False
        rail_pad.Reversed = False
        target_doc.recompute()

        # Posts: one Pad per post, evenly spaced.
        if rp.post_count_per_side > 0:
            if rp.post_count_per_side == 1:
                post_xs = [(rp.forward_x + rp.aft_x) / 2.0]
            else:
                step = (rp.aft_x - rp.forward_x) / (rp.post_count_per_side - 1)
                post_xs = [
                    rp.forward_x + i * step for i in range(rp.post_count_per_side)
                ]
            for idx, px_mm in enumerate(post_xs, start=1):
                post_datum = _pd_make_datum_xy(
                    body, f"Rail{side}Post{idx}Datum", deck_top_z_mm, added
                )
                post_sketch = body.newObject(
                    "Sketcher::SketchObject", f"Rail{side}Post{idx}Sketch"
                )
                added.append(post_sketch)
                post_sketch.AttachmentSupport = [(post_datum, "")]
                post_sketch.MapMode = "FlatFace"
                post_circle = Part.Circle(
                    FreeCAD.Vector(px_mm, sign * rail_y_mm, 0),
                    FreeCAD.Vector(0, 0, 1),
                    rp.post_diameter / 2.0,
                )
                post_sketch.addGeometry(post_circle.toShape().Curve, False)
                target_doc.recompute()

                post_pad = body.newObject(
                    "PartDesign::Pad", f"Rail{side}Post{idx}Pad"
                )
                added.append(post_pad)
                post_pad.Profile = (post_sketch, [""])
                post_pad.Length = rp.height_above_deck
                post_pad.Midplane = False
                post_pad.Reversed = False
                target_doc.recompute()

        side_bodies.append(body)

    # Legacy compound wrapper.
    railings_compound = target_doc.addObject("Part::Feature", "Deck_Railings")
    railings_compound.Shape = Part.makeCompound([b.Shape for b in side_bodies])
    added.append(railings_compound)
    railings_compound.addProperty(
        "App::PropertyLength", "RailingHeight", "Deck", "Railing height above deck plate"
    )
    railings_compound.RailingHeight = rp.height_above_deck
    railings_compound.addProperty(
        "App::PropertyStringList",
        "SideBodyLabels",
        "Deck",
        "Labels of the port + starboard Railing PartDesign Bodies",
    )
    railings_compound.SideBodyLabels = [b.Label for b in side_bodies]

    return Railings(body=railings_compound, height=rp.height_above_deck / _MM_PER_M)


# ---------------------------------------------------------------------------
# Public builder (FR-001 + contracts/python-api.md)
# ---------------------------------------------------------------------------


def build_deck(
    hull: Hull,
    parameters: DeckParameters | None = None,
    *,
    parameters_superstructure: DeckSuperstructureParameters | None = None,
    document: Any = None,
    name: str = "Deck",
) -> Deck:
    """Build the six-Body parametric Storebro deck on a hull.

    Args:
        hull: A Hull returned by ``storebro.hull.build_hull``. Must have a
            non-empty ``.body.Shape``.
        parameters: Legacy 14-field deck dimensional parameters. ``None`` →
            use :class:`DeckParameters` defaults (Storebro RC34 1972
            estimate-grade values). Mutually exclusive with
            ``parameters_superstructure``.
        parameters_superstructure: Spec 008 per-component composite. When
            non-None, takes precedence over ``parameters`` for the
            superstructure shape; the deck plate still derives from the
            legacy fields. Mutually exclusive with ``parameters``.
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
            null hull, document mismatch, or both parameter forms passed.
            Raised BEFORE any FreeCAD call.
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

    if parameters is not None and parameters_superstructure is not None:
        raise DeckParameterError(
            "parameters<>parameters_superstructure",
            None,
            "pass only one of `parameters` or `parameters_superstructure`",
        )

    resolved_params = parameters if parameters is not None else DeckParameters()
    _validate_deck_parameters(resolved_params)
    _validate_cross_hull_constraints(hull, resolved_params)

    # Resolve the new sub-dataclass composite. If the caller passed an
    # explicit `parameters_superstructure`, use it; otherwise translate
    # the legacy form via the shim.
    sp = (
        parameters_superstructure
        if parameters_superstructure is not None
        else resolved_params.to_superstructure_parameters()
    )

    target_doc = _resolve_document(hull, document)
    label = name if name is not None else "Deck"

    started = time.perf_counter()
    added: list[Any] = []
    try:
        deck_plate = _build_deck_plate(hull, resolved_params, target_doc, added)
        cabin_trunk = _build_cabin_trunk(
            hull, resolved_params, deck_plate, target_doc, added, superstructure=sp
        )
        windshield = _build_windshield(
            hull, resolved_params, cabin_trunk, target_doc, added, superstructure=sp
        )
        hardtop = _build_hardtop(
            hull, resolved_params, cabin_trunk, target_doc, added, superstructure=sp
        )
        hardtop_pillars = _build_hardtop_pillars(
            hull,
            resolved_params,
            hardtop,
            deck_plate,
            target_doc,
            added,
            superstructure=sp,
        )
        railings = _build_railings(
            hull, resolved_params, deck_plate, target_doc, added, superstructure=sp
        )
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
