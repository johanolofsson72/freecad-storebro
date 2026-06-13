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
from dataclasses import dataclass, field, fields, replace
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from storebro.hull import Hull, HullParameters

if TYPE_CHECKING:
    pass

_MM_PER_M = 1000.0
"""FreeCAD's internal length unit is mm; DeckParameters / HullParameters are in meters."""

_WINDSHIELD_CROWN_SEGMENTS = 16
"""Spec 030: polyline segments approximating the windshield's transverse top-edge arch.

Even so a vertex lands exactly on the apex (Y=0). A straight-segment polyline (not a
Sketcher arc) keeps the section sketch byte-reproducible (no constraint solver)."""


def _vec_m(x: float, y: float, z: float) -> Any:
    """Build a FreeCAD.Vector from meter-valued coordinates (scaled to mm)."""
    import FreeCAD

    return FreeCAD.Vector(x * _MM_PER_M, y * _MM_PER_M, z * _MM_PER_M)


__all__ = [
    "AnchorLockerParameters",
    "BowPulpitParameters",
    "CabinTrunkParameters",
    "CabinWindowParameters",
    "CleatParameters",
    "Deck",
    "DeckConstructionError",
    "DeckGlazingParameters",
    "DeckHardwareParameters",
    "DeckParameterError",
    "DeckParameters",
    "DeckSuperstructureParameters",
    "Deckhouse",
    "DeckhouseParameters",
    "DsWindowParameters",
    "HardtopParameters",
    "LifelineParameters",
    "PillarParameters",
    "RailingParameters",
    "RubrailParameters",
    "WindshieldGlazingParameters",
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


def _reject_nonfinite_floats(instance: object) -> None:
    """spec 029: reject nan/inf in every float field of a deck parameter dataclass.

    A bare positivity/range check lets non-finite values through (inf passes
    ``> 0``; nan compares false to every bound). This guard runs first in each
    ``__post_init__``, finite-checking every declared float field (skipping ints,
    bools, strings, and nested dataclasses) and raising :class:`DeckParameterError`
    naming the field. Existing positivity/range checks still run for finite values.
    """
    for f in fields(instance):  # type: ignore[arg-type]
        value = getattr(instance, f.name)
        if isinstance(value, float) and not math.isfinite(value):
            raise DeckParameterError(f.name, value, "finite (not nan/inf)")


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
    # spec 033: cabin proportions re-derived from docs/references/storo34_side_lines.png —
    # the RC34 cabin is a long, tall greenhouse running ~half the LOA, not the low
    # estimate-grade box of v1.0.x. Length kept below the hardtop-pillar line (5.4 m).
    cabin_trunk_length: float = 5.20
    cabin_trunk_fwd_offset: float = 1.60
    cabin_trunk_width: float = 2.20
    cabin_trunk_height: float = 1.45
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
        "cabin_trunk_length": 5.20,
        "cabin_trunk_fwd_offset": 1.60,
        "cabin_trunk_width": 2.20,
        "cabin_trunk_height": 1.45,
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
        _reject_nonfinite_floats(self)
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
        _reject_nonfinite_floats(self)
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
    crown_height: float = 60.0
    """Spec 030: rise (mm) of the transverse top edge at the centerline (Y=0) above the
    corners. ``0.0`` is the OFF sentinel (flat top, byte-identical to pre-030). Valid range
    ``[0, top_width/2)`` — the strict upper bound excludes the degenerate over-arch."""

    def __post_init__(self) -> None:
        _reject_nonfinite_floats(self)
        for name, value in (
            ("windshield_base_width", self.base_width),
            ("windshield_top_width", self.top_width),
            ("windshield_thickness", self.thickness),
        ):
            if value <= 0:
                raise DeckParameterError(name, value, "> 0")
        # Spec 030 — crown rise: non-negative and strictly below half the (narrowest)
        # top width so the arc radius stays finite and the section never inverts.
        # _reject_nonfinite_floats above already rejected NaN/±inf.
        if not (0.0 <= self.crown_height < self.top_width / 2.0):
            raise DeckParameterError(
                "windshield_crown_height",
                self.crown_height,
                "[0, top_width/2) mm",
            )
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
    # spec 033: the RC34 hardtop is a continuous coupe roof at ~cabin-roof height,
    # not a high flybridge — lowered from 2050 so it integrates with the 1450 mm
    # cabin top instead of floating on tall stilts.
    height_above_deck: float = 1650.0
    leading_edge_curl_depth: float = 80.0
    leading_edge_curl_length: float = 250.0
    curl_sections: int = 7  # spec 020: dense Ruled=True sections tracing the curl

    def __post_init__(self) -> None:
        _reject_nonfinite_floats(self)
        if self.curl_sections < 2:
            raise DeckParameterError("hardtop_curl_sections", self.curl_sections, ">= 2")
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
        _reject_nonfinite_floats(self)
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
        _reject_nonfinite_floats(self)
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
        _reject_nonfinite_floats(self)
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
# Spec 010 — deck-hardware parameter dataclasses (data-model §1)
#
# Five per-item parameter shapes + a composite, mirroring the spec 008
# superstructure dataclasses. All lengths in mm, all angles in degrees.
# Defaults are RC34 1972 estimate-grade values (research.md §R7). Each
# __post_init__ raises DeckParameterError on out-of-range input.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RubrailParameters:
    """Rubrail (wooden sheer strip) parameters (data-model §1.1).

    The rubrail is lofted between rectangular cross-section sketches at the
    sampled sheer stations, on both port and starboard sides.

    Example:
        >>> p = RubrailParameters()
        >>> p.height, p.thickness
        (60.0, 40.0)
        >>> RubrailParameters(forward_x=300.0, aft_x=10000.0).aft_x
        10000.0
    """

    height: float = 60.0
    thickness: float = 40.0
    forward_x: float = 300.0
    aft_x: float = 10000.0
    # spec 022 — moulded profile + chrome insert (additive, defaulted).
    # The DEFAULT profile is the chamfered (straight-line) section: it is
    # byte-reproducible under cumulative FreeCAD state (constitution II). The
    # rounded (arc) outboard face is an explicit opt-in — its loft volume drifts
    # under accumulated OCC tessellation state (the spec 018 arc-instability
    # wall), so it is NOT used by default. ``outboard_fillet`` is the rounded
    # radius applied only when ``rounded_profile`` is True.
    rounded_profile: bool = False
    outboard_fillet: float = 12.0  # rounded outboard-face radius (opt-in)
    chamfer_width: float = 12.0  # chamfered outboard bevel (reproducible default)
    chrome_insert: bool = True
    insert_height: float = 18.0
    insert_thickness: float = 8.0

    def __post_init__(self) -> None:
        _reject_nonfinite_floats(self)
        for name, value in (
            ("rubrail_height", self.height),
            ("rubrail_thickness", self.thickness),
        ):
            if value <= 0:
                raise DeckParameterError(name, value, "> 0")
        if self.forward_x < 0:
            raise DeckParameterError("rubrail_forward_x", self.forward_x, ">= 0")
        if self.forward_x >= self.aft_x:
            raise DeckParameterError(
                "rubrail_forward_x<>aft_x",
                None,
                "forward_x must be < aft_x",
            )
        half_min = min(self.height, self.thickness) / 2.0
        for name, value in (
            ("rubrail_outboard_fillet", self.outboard_fillet),
            ("rubrail_chamfer_width", self.chamfer_width),
        ):
            if not (0 < value <= half_min):
                raise DeckParameterError(name, value, f"(0, {half_min}]")
        if not (0 < self.insert_height < self.height):
            raise DeckParameterError("rubrail_insert_height", self.insert_height, "(0, height)")
        if not (0 < self.insert_thickness <= self.thickness):
            raise DeckParameterError(
                "rubrail_insert_thickness", self.insert_thickness, "(0, thickness]"
            )


@dataclass(frozen=True)
class BowPulpitParameters:
    """Bow pulpit (tubular bow guard rail) parameters (data-model §1.2).

    Modeled as straight tubular stanchions + connecting top-rail segments
    at the bow, symmetric about the centerline.

    Example:
        >>> p = BowPulpitParameters()
        >>> p.tube_diameter, p.stanchion_count
        (25.0, 2)
    """

    tube_diameter: float = 25.0
    height: float = 600.0
    forward_extent: float = 400.0
    stanchion_count: int = 2
    # spec 022 — radiused bends + welded joints (additive, defaulted).
    bend_radius: float = 40.0  # corner-ball radius (0 → no rounding)
    weld_beads: bool = True
    weld_bead_radius: float = 4.0  # torus minor radius (bead proud of the tube)

    def __post_init__(self) -> None:
        _reject_nonfinite_floats(self)
        for name, value in (
            ("bow_pulpit_tube_diameter", self.tube_diameter),
            ("bow_pulpit_height", self.height),
        ):
            if value <= 0:
                raise DeckParameterError(name, value, "> 0")
        if self.forward_extent < 0:
            raise DeckParameterError("bow_pulpit_forward_extent", self.forward_extent, ">= 0")
        if self.stanchion_count < 0:
            raise DeckParameterError("bow_pulpit_stanchion_count", self.stanchion_count, ">= 0")
        if self.bend_radius < 0:
            raise DeckParameterError("bow_pulpit_bend_radius", self.bend_radius, ">= 0")
        if self.weld_bead_radius <= 0:
            raise DeckParameterError("bow_pulpit_weld_bead_radius", self.weld_bead_radius, "> 0")


@dataclass(frozen=True)
class LifelineParameters:
    """Lifeline (horizontal tube between railing posts) parameters (data-model §1.3).

    Defaults to a single upper line at full railing height. Lifelines are
    skipped entirely when the railing has zero posts (FR-017).

    Example:
        >>> p = LifelineParameters()
        >>> p.line_count, p.tube_diameter, p.height_fraction
        (1, 12.0, 1.0)
    """

    line_count: int = 1
    tube_diameter: float = 12.0
    height_fraction: float = 1.0
    # spec 022 — true catenary sag (additive, defaulted; 0 → straight tube).
    sag_depth: float = 25.0  # mid-span dip in mm

    def __post_init__(self) -> None:
        _reject_nonfinite_floats(self)
        if self.line_count < 0:
            raise DeckParameterError("lifeline_line_count", self.line_count, ">= 0")
        if self.tube_diameter <= 0:
            raise DeckParameterError("lifeline_tube_diameter", self.tube_diameter, "> 0")
        if not (0.0 < self.height_fraction <= 1.0):
            raise DeckParameterError(
                "lifeline_height_fraction",
                self.height_fraction,
                "(0, 1]",
            )
        if self.sag_depth < 0:
            raise DeckParameterError("lifeline_sag_depth", self.sag_depth, ">= 0")


@dataclass(frozen=True)
class AnchorLockerParameters:
    """Anchor locker (raised foredeck hatch box) parameters (data-model §1.4).

    A raised additive box near the bow (NOT a boolean recess). Footprint is
    validated against the deck plate + cabin trunk by :func:`build_deck`.

    Example:
        >>> p = AnchorLockerParameters()
        >>> p.length, p.width, p.height
        (500.0, 400.0, 150.0)
    """

    length: float = 500.0
    width: float = 400.0
    height: float = 150.0
    center_x: float = 8500.0  # foredeck, forward of the cabin trunk (bow = XMax)
    # spec 022 — functional recessed cavity + separate lid (additive, defaulted).
    cavity_depth: float = 90.0  # 0 → solid box, no cavity, no lid
    cavity_inset: float = 40.0  # wall thickness around the cavity
    lid: bool = True
    lid_thickness: float = 20.0

    def __post_init__(self) -> None:
        _reject_nonfinite_floats(self)
        for name, value in (
            ("anchor_locker_length", self.length),
            ("anchor_locker_width", self.width),
            ("anchor_locker_height", self.height),
        ):
            if value <= 0:
                raise DeckParameterError(name, value, "> 0")
        if self.center_x < 0:
            raise DeckParameterError("anchor_locker_center_x", self.center_x, ">= 0")
        if not (0 <= self.cavity_depth < self.height):
            raise DeckParameterError("anchor_locker_cavity_depth", self.cavity_depth, "[0, height)")
        if not (0 < self.cavity_inset < min(self.length, self.width) / 2.0):
            raise DeckParameterError(
                "anchor_locker_cavity_inset",
                self.cavity_inset,
                f"(0, {min(self.length, self.width) / 2.0})",
            )
        if self.lid_thickness <= 0:
            raise DeckParameterError("anchor_locker_lid_thickness", self.lid_thickness, "> 0")


@dataclass(frozen=True)
class CleatParameters:
    """Mooring cleat parameters (data-model §1.5).

    Per-side semantics: ``count_per_station`` cleats are placed per side at
    each of ``station_count`` longitudinal stations, mirrored port/starboard.
    Total cleats = ``count_per_station * station_count * 2`` (default 4).

    Example:
        >>> p = CleatParameters()
        >>> p.count_per_station, p.station_count
        (1, 2)
        >>> p.count_per_station * p.station_count * 2  # total cleats
        4
    """

    count_per_station: int = 1
    station_count: int = 2
    length: float = 200.0
    height: float = 80.0
    # spec 022 — contoured casting silhouette (additive, defaulted).
    base_taper: float = 0.7  # top-footprint fraction of the base (1 = no taper)
    horn_rise: float = 32.0  # how high the curved horn arcs above the base top

    def __post_init__(self) -> None:
        _reject_nonfinite_floats(self)
        if self.count_per_station < 0:
            raise DeckParameterError("cleat_count_per_station", self.count_per_station, ">= 0")
        if self.station_count < 0:
            raise DeckParameterError("cleat_station_count", self.station_count, ">= 0")
        for name, value in (
            ("cleat_length", self.length),
            ("cleat_height", self.height),
        ):
            if value <= 0:
                raise DeckParameterError(name, value, "> 0")
        if not (0 < self.base_taper <= 1.0):
            raise DeckParameterError("cleat_base_taper", self.base_taper, "(0, 1]")
        if self.horn_rise <= 0:
            raise DeckParameterError("cleat_horn_rise", self.horn_rise, "> 0")


@dataclass(frozen=True)
class DeckHardwareParameters:
    """Composite of the five deck-hardware parameter dataclasses (data-model §1.6).

    The optional ``parameters_hardware`` entry point for :func:`build_deck`,
    orthogonal to :class:`DeckSuperstructureParameters`. No composite-level
    cross-field invariants — the hardware items are mutually independent at
    the parameter layer; cross-deck collision checks live in build_deck.

    Example:
        >>> p = DeckHardwareParameters()
        >>> p.rubrail.height, p.cleats.station_count, p.lifelines.line_count
        (60.0, 2, 1)
    """

    rubrail: RubrailParameters = field(default_factory=RubrailParameters)
    bow_pulpit: BowPulpitParameters = field(default_factory=BowPulpitParameters)
    lifelines: LifelineParameters = field(default_factory=LifelineParameters)
    anchor_locker: AnchorLockerParameters = field(default_factory=AnchorLockerParameters)
    cleats: CleatParameters = field(default_factory=CleatParameters)


# ---------------------------------------------------------------------------
# Spec 011 — deck glazing parameters (data-model §2)
#
# Cabin-trunk side-window recesses (blind PartDesign::Pocket into the solid
# trunk) + the windshield frame/glass rework. All lengths in mm; validation
# raises DeckParameterError.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CabinWindowParameters:
    """Cabin-trunk side-window recess parameters (data-model §2.1).

    Blind rounded-rectangle recesses cut into each cabin-trunk side wall.
    Sentinel ``0.0`` on ``sill_height`` means "centre vertically on the wall".

    Example:
        >>> p = CabinWindowParameters()
        >>> p.count_per_side, p.length, p.height
        (1, 900.0, 350.0)
    """

    count_per_side: int = 1
    length: float = 900.0
    height: float = 350.0
    corner_radius: float = 80.0
    recess_depth: float = 15.0
    sill_height: float = 0.0
    glass_panes: bool = True  # spec 019: translucent pane seated in the recess
    glass_thickness: float = 6.0

    def __post_init__(self) -> None:
        _reject_nonfinite_floats(self)
        if self.count_per_side < 0:
            raise DeckParameterError(
                "cabin_window_count_per_side", self.count_per_side, ">= 0"
            )
        if self.glass_thickness <= 0:
            raise DeckParameterError(
                "cabin_window_glass_thickness", self.glass_thickness, "> 0"
            )
        for name, value in (
            ("cabin_window_length", self.length),
            ("cabin_window_height", self.height),
            ("cabin_window_recess_depth", self.recess_depth),
        ):
            if value <= 0:
                raise DeckParameterError(name, value, "> 0")
        if self.corner_radius < 0:
            raise DeckParameterError(
                "cabin_window_corner_radius", self.corner_radius, ">= 0"
            )
        if self.corner_radius * 2 > self.height or self.corner_radius * 2 > self.length:
            raise DeckParameterError(
                "cabin_window_corner_radius",
                self.corner_radius,
                "2*corner_radius must be <= both length and height",
            )
        if self.sill_height < 0:
            raise DeckParameterError("cabin_window_sill_height", self.sill_height, ">= 0")


@dataclass(frozen=True)
class WindshieldGlazingParameters:
    """Windshield frame + glass parameters (data-model §2.2).

    When ``enabled`` the windshield slab gets a central through-opening
    (leaving ``frame_border`` on all sides) plus a separate glass pane.
    When disabled, the spec 008 solid slab is kept (FR-011).

    Example:
        >>> p = WindshieldGlazingParameters()
        >>> p.enabled, p.frame_border, p.glass_thickness
        (True, 60.0, 6.0)
    """

    enabled: bool = True
    frame_border: float = 60.0
    glass_thickness: float = 6.0

    def __post_init__(self) -> None:
        _reject_nonfinite_floats(self)
        for name, value in (
            ("windshield_frame_border", self.frame_border),
            ("windshield_glass_thickness", self.glass_thickness),
        ):
            if value <= 0:
                raise DeckParameterError(name, value, "> 0")


@dataclass(frozen=True)
class DeckGlazingParameters:
    """Composite of the deck glazing parameter dataclasses (data-model §2.3).

    The optional ``parameters_glazing`` entry point for :func:`build_deck`.

    Example:
        >>> p = DeckGlazingParameters()
        >>> p.cabin_windows.count_per_side, p.windshield.enabled
        (1, True)
    """

    cabin_windows: CabinWindowParameters = field(default_factory=CabinWindowParameters)
    windshield: WindshieldGlazingParameters = field(
        default_factory=WindshieldGlazingParameters
    )


# ---------------------------------------------------------------------------
# Spec 016 — DS-variant deckhouse parameters (data-model §1)
#
# The DS (deck saloon / styrhytt) variant replaces the open-flybridge cabin
# trunk + windshield + hardtop + pillars with a single enclosed deckhouse
# solid. These dataclasses parameterize that solid + its blind side/front
# window recesses. All lengths in mm, all angles in degrees. Defaults are
# estimate-grade visual measurements from docs/references/storo34_side_lines.png
# at the canonical RC34 LOA (research.md §R6).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DsWindowParameters:
    """DS deckhouse side/front window blind-recess parameters (data-model §1.1).

    Plain rectangular blind recesses (no rounded corners, no glass panes —
    both deferred). Mirrors :class:`CabinWindowParameters` but for the
    enclosed deckhouse. ``recess_depth`` must stay shallower than the
    deckhouse ``wall_inset`` (enforced on :class:`DeckhouseParameters`) so a
    recess can never split the solid (the spec 009 manifold guard).

    Example:
        >>> p = DsWindowParameters()
        >>> p.count_per_side, p.length, p.height
        (3, 1000.0, 500.0)
    """

    count_per_side: int = 3
    length: float = 1000.0
    height: float = 500.0
    recess_depth: float = 15.0
    glass_panes: bool = True  # spec 019: translucent pane seated in the recess
    glass_thickness: float = 6.0
    # spec 023 — front-window recess on the raked screen, side-window mullions,
    # and a helm-door recess (all blind, all on the deckhouse body only).
    front_window: bool = True
    front_length: float = 1400.0
    front_height: float = 420.0
    mullions_per_window: int = 1
    mullion_width: float = 40.0
    helm_door: bool = True
    helm_door_length: float = 650.0
    helm_door_height: float = 1100.0
    helm_door_side: str = "Starboard"

    def __post_init__(self) -> None:
        _reject_nonfinite_floats(self)
        if self.count_per_side < 0:
            raise DeckParameterError(
                "ds_window_count_per_side", self.count_per_side, ">= 0"
            )
        if self.glass_thickness <= 0:
            raise DeckParameterError(
                "ds_window_glass_thickness", self.glass_thickness, "> 0"
            )
        for name, value in (
            ("ds_window_length", self.length),
            ("ds_window_height", self.height),
            ("ds_window_recess_depth", self.recess_depth),
        ):
            if value <= 0:
                raise DeckParameterError(name, value, "> 0")
        # spec 023 additions.
        if self.mullions_per_window < 0:
            raise DeckParameterError(
                "ds_window_mullions_per_window", self.mullions_per_window, ">= 0"
            )
        if self.helm_door_side not in ("Port", "Starboard"):
            raise DeckParameterError(
                "ds_window_helm_door_side", None, "Port | Starboard"
            )
        for name, value in (
            ("ds_window_front_length", self.front_length),
            ("ds_window_front_height", self.front_height),
            ("ds_window_mullion_width", self.mullion_width),
            ("ds_window_helm_door_length", self.helm_door_length),
            ("ds_window_helm_door_height", self.helm_door_height),
        ):
            if value <= 0:
                raise DeckParameterError(name, value, "> 0")


@dataclass(frozen=True)
class DeckhouseParameters:
    """Enclosed DS deckhouse reshape parameters (data-model §1.2).

    The deckhouse is built as a single filled :class:`PartDesign.AdditiveLoft`
    solid (raked front wall + tapered side walls + flat roof top-face),
    carrying blind window recesses — not a hollowed shell (clarified). All
    lengths in millimeters, all angles in degrees. Defaults derived from
    docs/references/storo34_side_lines.png at LOA = 10360 mm.

    Example:
        >>> p = DeckhouseParameters()
        >>> p.length, p.forward_width, p.aft_width
        (6200.0, 2000.0, 2200.0)
        >>> tall = DeckhouseParameters(height_above_deck=1600.0)
        >>> tall.height_above_deck
        1600.0
    """

    length: float = 6200.0
    forward_width: float = 2000.0
    aft_width: float = 2200.0
    height_above_deck: float = 1500.0
    front_rake_angle: float = 30.0
    roof_thickness: float = 60.0
    wall_inset: float = 250.0
    fwd_offset: float = 2200.0
    windows: DsWindowParameters = field(default_factory=DsWindowParameters)

    REFERENCE_STOREBRO_DECKHOUSE_DS: ClassVar[dict[str, float]] = {
        "length": 6200.0,
        "forward_width": 2000.0,
        "aft_width": 2200.0,
        "height_above_deck": 1500.0,
        "front_rake_angle": 30.0,
        "roof_thickness": 60.0,
        "wall_inset": 250.0,
        "fwd_offset": 2200.0,
    }

    def __post_init__(self) -> None:
        _reject_nonfinite_floats(self)
        for name, value in (
            ("deckhouse_length", self.length),
            ("deckhouse_forward_width", self.forward_width),
            ("deckhouse_aft_width", self.aft_width),
            ("deckhouse_height_above_deck", self.height_above_deck),
            ("deckhouse_roof_thickness", self.roof_thickness),
        ):
            if value <= 0:
                raise DeckParameterError(name, value, "> 0")
        for name, value in (
            ("deckhouse_wall_inset", self.wall_inset),
            ("deckhouse_fwd_offset", self.fwd_offset),
        ):
            if value < 0:
                raise DeckParameterError(name, value, ">= 0")
        if self.forward_width > self.aft_width:
            raise DeckParameterError(
                "deckhouse_forward_width<>aft_width",
                None,
                "forward_width must be <= aft_width (tapered silhouette invariant)",
            )
        if not (0.0 <= self.front_rake_angle <= 60.0):
            raise DeckParameterError(
                "deckhouse_front_rake_angle",
                self.front_rake_angle,
                "[0, 60] degrees",
            )
        # Recesses must stay shallower than the wall they cut into, else the
        # deckhouse splits into multiple solids (spec 009 non-manifold guard).
        if self.windows.recess_depth >= self.wall_inset:
            raise DeckParameterError(
                "deckhouse_window_recess_depth<>wall_inset",
                self.windows.recess_depth,
                f"< wall_inset ({self.wall_inset:.0f} mm) so each recess stays blind",
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
class WindshieldGlass:
    """Wrapper around the windshield glass-pane PartDesign::Body (spec 011).

    Its transparency/material is assigned later by spec 015.

    Example:
        >>> # Accessed via Deck.windshield.glass_pane.
    """

    body: Any
    thickness: float


@dataclass(frozen=True)
class Windshield:
    """Wrapper around the FreeCAD Body representing the windshield.

    Spec 011: when glazing is enabled the ``body`` is the frame (slab with a
    central through-opening) and ``glass_pane`` carries the recessed pane;
    when disabled ``body`` is the spec 008 solid slab and ``glass_pane`` is
    ``None``.

    Example:
        >>> # Accessed via Deck.windshield.
    """

    body: Any
    rake_degrees: float
    glass_pane: WindshieldGlass | None = None


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
# Spec 010 — deck-hardware sub-Body wrappers (data-model §2)
# All length fields are in METERS at the wrapper boundary (matching the
# spec 003/008 wrappers); the FreeCAD geometry is built in mm.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Rubrail:
    """Wrapper around the Part::Compound of the port + starboard rubrail bodies.

    Example:
        >>> # Accessed via Deck.rubrail.
    """

    body: Any
    height: float
    thickness: float
    # spec 022 — present when the chrome insert strip was built.
    has_chrome_insert: bool = False
    insert_body: Any = None


@dataclass(frozen=True)
class BowPulpit:
    """Wrapper around the FreeCAD Body representing the tubular bow pulpit.

    Example:
        >>> # Accessed via Deck.bow_pulpit.
    """

    body: Any
    tube_diameter: float
    height: float
    # spec 022 — True when radiused bends + weld beads were built (False on the
    # spec 010 straight-tube fallback).
    has_radiused_bends: bool = False
    has_weld_beads: bool = False


@dataclass(frozen=True)
class Lifelines:
    """Wrapper around the Part::Compound of the lifeline tubes.

    ``body`` is an empty compound when the railing has zero posts (FR-017).

    Example:
        >>> # Accessed via Deck.lifelines.
    """

    body: Any
    line_count: int


@dataclass(frozen=True)
class AnchorLocker:
    """Wrapper around the FreeCAD Body representing the raised anchor-locker box.

    Example:
        >>> # Accessed via Deck.anchor_locker.
    """

    body: Any
    length: float
    width: float
    height: float
    # spec 022 — present when the recessed cavity + separate lid were built.
    has_cavity: bool = False
    lid_body: Any = None


@dataclass(frozen=True)
class Cleats:
    """Wrapper around the Part::Compound of the mooring cleat bodies.

    Example:
        >>> # Accessed via Deck.cleats.
    """

    body: Any
    count: int


@dataclass(frozen=True)
class CabinWindows:
    """Wrapper describing the side windows cut into the cabin trunk (spec 011).

    ``body`` is the cabin-trunk body (the windows are Pocket features on it).

    Example:
        >>> # Accessed via Deck.cabin_windows.
    """

    body: Any
    count: int


@dataclass(frozen=True)
class Deckhouse:
    """Wrapper around the enclosed DS deckhouse PartDesign::Body (spec 016).

    Built only in the ``ds`` superstructure variant; replaces the open-
    flybridge cabin trunk + windshield + hardtop + pillars. The blind window
    recesses are Pocket features on ``body``. Length fields in meters at the
    wrapper boundary (matching the spec 003/008 wrappers; geometry in mm).

    Example:
        >>> # Accessed via Deck.deckhouse after build_deck(superstructure_variant="ds").
    """

    body: Any
    length: float
    forward_width: float
    aft_width: float
    height: float
    window_count: int
    # spec 023 — detailing flags (additive, defaulted for back-compat).
    has_front_window: bool = False
    front_window_skipped: bool = False
    mullion_count: int = 0
    has_helm_door: bool = False


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
    # Spec 016 — the four open-flybridge bodies are None in the "ds" variant
    # (replaced by `deckhouse`); populated as before in the "standard" variant.
    cabin_trunk: CabinTrunk | None
    windshield: Windshield | None
    hardtop: Hardtop | None
    hardtop_pillars: HardtopPillars | None
    railings: Railings
    # Spec 010 — deck hardware (appended after the six superstructure bodies
    # so existing field order is preserved; Deck is only constructed inside
    # build_deck, so adding fields is non-breaking for external callers).
    rubrail: Rubrail
    bow_pulpit: BowPulpit
    lifelines: Lifelines
    anchor_locker: AnchorLocker
    cleats: Cleats
    parameters_hardware: DeckHardwareParameters
    # spec 011 — glazing (appended; Deck is only constructed inside build_deck).
    # spec 016 — None in the "ds" variant (no cabin trunk to cut windows into).
    cabin_windows: CabinWindows | None
    parameters_glazing: DeckGlazingParameters
    # spec 016 — DS variant: the selected silhouette + the enclosed deckhouse
    # (populated iff superstructure_variant == "ds"; None in "standard").
    superstructure_variant: str = "standard"
    deckhouse: Deckhouse | None = None


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
        sketch.addConstraint(Sketcher.Constraint("Coincident", line_ids[i], 2, line_ids[j], 1))


def _slab_sketch_rect(
    body: Any,
    datum: Any,
    name: str,
    half_w_mm: float,
    half_h_mm: float,
    vertical_center_mm: float,
    added: list[Any],
    center_w_mm: float = 0.0,
) -> Any:
    """Centered rectangle sketch on a YZ-parallel datum (spec 011 helper).

    Sketch local x = global Y, local y = global Z (datum normal = global X).
    The rectangle is centered at (``center_w_mm``, ``vertical_center_mm``) with
    the given half-width (Y) and half-height (Z). ``center_w_mm`` defaults to 0
    (the centerline) so existing spec 011 callers are unchanged; spec 022's
    chrome insert offsets it to the rubrail outboard face. Used for the
    windshield frame opening, the glass pane, and the rubrail chrome insert.
    """
    import FreeCAD
    import Part

    sketch = body.newObject("Sketcher::SketchObject", name)
    added.append(sketch)
    sketch.AttachmentSupport = [(datum, "")]
    sketch.MapMode = "FlatFace"
    cz = vertical_center_mm
    cw = center_w_mm
    pts = [
        FreeCAD.Vector(cw - half_w_mm, cz - half_h_mm, 0),
        FreeCAD.Vector(cw + half_w_mm, cz - half_h_mm, 0),
        FreeCAD.Vector(cw + half_w_mm, cz + half_h_mm, 0),
        FreeCAD.Vector(cw - half_w_mm, cz + half_h_mm, 0),
    ]
    line_ids: list[int] = []
    for i in range(4):
        j = (i + 1) % 4
        line_ids.append(sketch.addGeometry(Part.LineSegment(pts[i], pts[j]), False))
    _pd_close_loop_constraints(sketch, line_ids)
    return sketch


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

    lower_sketch = _trapezoid_sketch("CabinTrunkLowerSketch", lower_datum, fwd_x_mm, aft_x_mm)
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
    glazing: DeckGlazingParameters | None = None,
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

    def _make_yz_datum(name: str, x_offset_mm: float, z_offset_mm: float) -> Any:
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

    def _slab_sketch_arched(
        name: str, datum: Any, width_mm: float, vertical_z_mm: float
    ) -> Any:
        """Spec 030: like ``_slab_sketch`` but with an upward-arched (crowned) top edge.

        The single flat top segment becomes a ``_WINDSHIELD_CROWN_SEGMENTS``-segment
        polyline tracing a circular arc of half-width ``hw`` and apex rise
        ``r = ws.crown_height``: ``y(x) = sqrt(R^2 - x^2) - (R - r)`` with
        ``R = (hw^2 + r^2) / (2r)``. The arch returns to 0 rise at ``x = ±hw`` (corners
        keep the flat-top Z, so the frame margin is preserved) and peaks at ``+r`` at
        ``x = 0``. Bottom and side edges are unchanged. Deterministic — straight segments
        only, no Sketcher arc/solver — so the section stays byte-reproducible.
        """
        sketch = body.newObject("Sketcher::SketchObject", name)
        added.append(sketch)
        sketch.AttachmentSupport = [(datum, "")]
        sketch.MapMode = "FlatFace"
        hw = width_mm / 2.0
        ht = ws.thickness / 2.0
        r = ws.crown_height
        top_base = vertical_z_mm + ht
        # r < hw is guaranteed by WindshieldParameters validation (crown_height <
        # top_width/2 <= width/2 for every section), so radius > r and the arc is real.
        radius = (hw * hw + r * r) / (2.0 * r)
        n = _WINDSHIELD_CROWN_SEGMENTS
        # CCW: bottom-left, bottom-right, then the arch top sampled from x=+hw to x=-hw.
        pts = [
            FreeCAD.Vector(-hw, vertical_z_mm - ht, 0),
            FreeCAD.Vector(hw, vertical_z_mm - ht, 0),
        ]
        for k in range(n + 1):
            x = hw - (2.0 * hw) * k / n  # +hw -> -hw; even n puts the apex (x=0) on a vertex
            rise = math.sqrt(max(radius * radius - x * x, 0.0)) - (radius - r)
            pts.append(FreeCAD.Vector(x, top_base + rise, 0))
        line_ids: list[int] = []
        m = len(pts)
        for i in range(m):
            j = (i + 1) % m
            line_ids.append(sketch.addGeometry(Part.LineSegment(pts[i], pts[j]), False))
        _pd_close_loop_constraints(sketch, line_ids)
        return sketch

    base_datum = _make_yz_datum("WindshieldBaseDatum", base_x_mm, base_z_mm)
    mid_datum = _make_yz_datum("WindshieldMidDatum", mid_x_mm, mid_z_mm)
    top_datum = _make_yz_datum("WindshieldTopDatum", top_x_mm, top_z_mm)

    mid_width = (ws.base_width + ws.top_width) / 2.0

    def _make_sections_and_loft(crowned: bool) -> tuple[Any, list[Any]]:
        """Build the three section sketches + the AdditiveLoft; return (loft, created).

        ``crowned`` selects the arched top edge (uniform rise ``ws.crown_height`` on all
        three sections, matching vertex topology for a robust ``Ruled=False`` loft); the
        flat path is byte-identical to the pre-030 windshield. ``created`` lists every
        object so the manifold-or-fallback gate can discard them on a non-manifold result.
        """
        make = _slab_sketch_arched if crowned else _slab_sketch
        bs = make("WindshieldBaseSketch", base_datum, ws.base_width, 0.0)
        ms = make("WindshieldMidSketch", mid_datum, mid_width, 0.0)
        ts = make("WindshieldTopSketch", top_datum, ws.top_width, 0.0)
        target_doc.recompute()
        lft = body.newObject("PartDesign::AdditiveLoft", "WindshieldLoft")
        added.append(lft)
        lft.Profile = (bs, [""])
        lft.Sections = [(ms, [""]), (ts, [""])]
        lft.Ruled = False  # smooth B-spline interpolation (3 sections is dense enough)
        lft.Closed = False
        target_doc.recompute()
        with contextlib.suppress(BaseException):
            body.Tip = lft
        return lft, [bs, ms, ts, lft]

    # Spec 030 — crown the transverse top edge when crown_height > 0, with a
    # manifold-or-fallback gate (FR-009): if the crowned loft is not a single valid
    # solid, discard it and rebuild the flat-top slab. crown_height == 0.0 takes the
    # flat path directly, byte-identical to pre-030 (FR-006).
    want_crown = ws.crown_height > 0.0
    _loft, _crown_created = _make_sections_and_loft(want_crown)
    if want_crown and not _is_single_valid_solid(body.Shape):
        for obj in _crown_created:
            added[:] = [a for a in added if getattr(a, "Name", None) != obj.Name]
            with contextlib.suppress(BaseException):
                target_doc.removeObject(obj.Name)
        with contextlib.suppress(BaseException):
            body.Tip = None
        _loft, _crown_created = _make_sections_and_loft(False)
        target_doc.recompute()

    body.addProperty(
        "App::PropertyAngle",
        "WindshieldRake",
        "Deck",
        "Windshield rake at base (legacy back-compat field; new design has base + top rakes)",
    )
    body.WindshieldRake = ws.rake_angle_base

    # Spec 011 — frame + glass rework. When enabled, pocket a central opening
    # ThroughAll along X (a projection cut through the raked panel) leaving
    # `frame_border` on all sides, then build a separate thin glass pane that
    # fills the opening. When disabled, keep the spec 008 solid slab (FR-011).
    wg = (glazing or DeckGlazingParameters()).windshield
    glass_pane: WindshieldGlass | None = None
    if wg.enabled:
        opening_half_w = ws.base_width / 2.0 - wg.frame_border
        opening_half_h = (top_z_mm - base_z_mm) / 2.0 - wg.frame_border
        if opening_half_w <= 0 or opening_half_h <= 0:
            raise DeckParameterError(
                "windshield_frame_border<>opening",
                wg.frame_border,
                "2*frame_border must be < windshield width and height (a "
                "positive opening must remain)",
            )
        # Frame opening: rectangle on the base YZ datum (normal = global X),
        # centered at (Y=0, Z=mid_z), ThroughAll along X.
        opening_sketch = _slab_sketch_rect(
            body, base_datum, "WindshieldOpeningSketch", opening_half_w, opening_half_h, mid_z_mm, added
        )
        pocket = body.newObject("PartDesign::Pocket", "WindshieldFrameOpening")
        added.append(pocket)
        pocket.Profile = (opening_sketch, [""])
        pocket.Type = "ThroughAll"
        pocket.Midplane = True
        target_doc.recompute()

        # Glass pane: a separate thin body filling the opening, X-thin.
        glass_body = target_doc.addObject("PartDesign::Body", "Deck_WindshieldGlass")
        added.append(glass_body)
        target_doc.recompute()
        gp_yz = _pd_get_origin_plane(glass_body, "YZ_Plane")
        gp_datum = glass_body.newObject("PartDesign::Plane", "WindshieldGlassDatum")
        added.append(gp_datum)
        gp_datum.AttachmentSupport = [(gp_yz, "")]
        gp_datum.MapMode = "FlatFace"
        gp_datum.AttachmentOffset = FreeCAD.Placement(
            FreeCAD.Vector(0.0, 0.0, mid_x_mm), FreeCAD.Rotation()
        )
        gp_sketch = _slab_sketch_rect(
            glass_body, gp_datum, "WindshieldGlassSketch", opening_half_w, opening_half_h, mid_z_mm, added
        )
        gp_pad = glass_body.newObject("PartDesign::Pad", "WindshieldGlassPad")
        added.append(gp_pad)
        gp_pad.Profile = (gp_sketch, [""])
        gp_pad.Length = wg.glass_thickness
        gp_pad.Midplane = True
        target_doc.recompute()
        glass_pane = WindshieldGlass(
            body=glass_body, thickness=wg.glass_thickness / _MM_PER_M
        )

    return Windshield(
        body=body, rake_degrees=ws.rake_angle_base, glass_pane=glass_pane
    )


def _cut_cabin_windows(
    cabin_trunk: CabinTrunk,
    glazing: DeckGlazingParameters,
    target_doc: Any,
    added: list[Any],
) -> tuple[CabinWindows, list[Any]]:
    """Cut blind side-window recesses into the cabin trunk (spec 011 FR-002).

    Per side, a rectangular `PartDesign::Pocket` of depth ``recess_depth`` into
    the trunk side wall, on an XZ-parallel datum (normal = global Y) at the
    trunk side outer-Y. Plain rectangle: the rounded corners are deferred
    (Sketcher fillet fragility, spec 009 lesson). Zero-count → no cuts.

    Raises :class:`DeckParameterError` if the recess would reach the far side
    of the solid trunk or the opening would not fit the wall.
    """
    import FreeCAD
    import Part

    cw = glazing.cabin_windows
    body = cabin_trunk.body
    glass_bodies: list[Any] = []
    if cw.count_per_side == 0:
        return (CabinWindows(body=body, count=0), glass_bodies)

    bb = body.Shape.BoundBox
    half_width = bb.YLength / 2.0
    if cw.recess_depth >= half_width:
        raise DeckParameterError(
            "cabin_window_recess_depth<>wall",
            cw.recess_depth,
            f"< trunk half-width ({half_width:.0f} mm) so the recess stays blind",
        )
    length_avail = bb.XLength
    height_avail = bb.ZLength
    if cw.length >= length_avail or cw.height >= height_avail:
        raise DeckParameterError(
            "cabin_window_opening<>wall",
            None,
            f"window {cw.length:.0f}x{cw.height:.0f} mm must fit within the "
            f"trunk wall ({length_avail:.0f}x{height_avail:.0f} mm)",
        )

    # Longitudinal stations for the windows, inset 12% from each end.
    lo, hi = bb.XMin + 0.12 * length_avail, bb.XMax - 0.12 * length_avail
    if cw.count_per_side == 1:
        x_stations = [(lo + hi) / 2.0]
    else:
        step = (hi - lo) / (cw.count_per_side - 1)
        x_stations = [lo + i * step for i in range(cw.count_per_side)]
    cz = (
        bb.ZMin + cw.sill_height + cw.height / 2.0
        if cw.sill_height > 0.0
        else (bb.ZMin + bb.ZMax) / 2.0
    )
    outer_y = bb.YMax
    half_l = cw.length / 2.0
    half_h = cw.height / 2.0

    xz_plane = _pd_get_origin_plane(body, "XZ_Plane")
    count = 0
    for x_mm in x_stations:
        for side, sign in (("Port", 1.0), ("Starboard", -1.0)):
            count += 1
            datum = body.newObject("PartDesign::Plane", f"CabinWindowDatum{side}{count}")
            added.append(datum)
            datum.AttachmentSupport = [(xz_plane, "")]
            datum.MapMode = "FlatFace"
            # XZ_Plane: local X = global X, local Y = global Z, local Z = global Y.
            datum.AttachmentOffset = FreeCAD.Placement(
                FreeCAD.Vector(x_mm, cz, sign * (outer_y + 2.0)),
                FreeCAD.Rotation(),
            )
            sketch = body.newObject(
                "Sketcher::SketchObject", f"CabinWindowSketch{side}{count}"
            )
            added.append(sketch)
            sketch.AttachmentSupport = [(datum, "")]
            sketch.MapMode = "FlatFace"
            # Sketch local x = global X, local y = global Z; centered at datum origin.
            pts = [
                FreeCAD.Vector(-half_l, -half_h, 0),
                FreeCAD.Vector(half_l, -half_h, 0),
                FreeCAD.Vector(half_l, half_h, 0),
                FreeCAD.Vector(-half_l, half_h, 0),
            ]
            line_ids: list[int] = []
            for i in range(4):
                j = (i + 1) % 4
                line_ids.append(sketch.addGeometry(Part.LineSegment(pts[i], pts[j]), False))
            _pd_close_loop_constraints(sketch, line_ids)
            pocket = body.newObject("PartDesign::Pocket", f"CabinWindowPocket{side}{count}")
            added.append(pocket)
            pocket.Profile = (sketch, [""])
            pocket.Length = cw.recess_depth + 2.0
            pocket.Reversed = sign > 0.0  # cut toward the centerline
            pocket.Midplane = False

            if cw.glass_panes:
                glass_bodies.append(
                    _build_window_glass(
                        target_doc,
                        f"Deck_CabinWindowGlass{side}{count}",
                        x_mm,
                        cz,
                        sign * (outer_y - cw.recess_depth * 0.5),
                        half_l,
                        half_h,
                        cw.glass_thickness,
                        added,
                    )
                )

    return (CabinWindows(body=body, count=count), glass_bodies)


def _build_window_glass(
    target_doc: Any,
    name: str,
    x_mm: float,
    cz_mm: float,
    inset_y_mm: float,
    half_l_mm: float,
    half_h_mm: float,
    thickness_mm: float,
    added: list[Any],
) -> Any:
    """Build one translucent rectangular glass-pane Body seated in a window recess.

    spec 019: a separate additive ``PartDesign::Body`` (never a boolean on the
    host trunk/deckhouse), centred at global ``(x_mm, inset_y_mm, cz_mm)`` on an
    XZ-parallel datum (normal = global Y), X-thin by ``thickness_mm``. Returns
    the glass Body. Mirrors the windshield-glass / porthole-glass idiom.
    """
    import FreeCAD
    import Part

    g_body = target_doc.addObject("PartDesign::Body", name)
    added.append(g_body)
    target_doc.recompute()
    g_xz = _pd_get_origin_plane(g_body, "XZ_Plane")
    g_datum = g_body.newObject("PartDesign::Plane", f"{name}Datum")
    added.append(g_datum)
    g_datum.AttachmentSupport = [(g_xz, "")]
    g_datum.MapMode = "FlatFace"
    g_datum.AttachmentOffset = FreeCAD.Placement(
        FreeCAD.Vector(x_mm, cz_mm, inset_y_mm), FreeCAD.Rotation()
    )
    g_sketch = g_body.newObject("Sketcher::SketchObject", f"{name}Sketch")
    added.append(g_sketch)
    g_sketch.AttachmentSupport = [(g_datum, "")]
    g_sketch.MapMode = "FlatFace"
    pts = [
        FreeCAD.Vector(-half_l_mm, -half_h_mm, 0),
        FreeCAD.Vector(half_l_mm, -half_h_mm, 0),
        FreeCAD.Vector(half_l_mm, half_h_mm, 0),
        FreeCAD.Vector(-half_l_mm, half_h_mm, 0),
    ]
    line_ids: list[int] = []
    for i in range(4):
        j = (i + 1) % 4
        line_ids.append(g_sketch.addGeometry(Part.LineSegment(pts[i], pts[j]), False))
    _pd_close_loop_constraints(g_sketch, line_ids)
    g_pad = g_body.newObject("PartDesign::Pad", f"{name}Pad")
    added.append(g_pad)
    g_pad.Profile = (g_sketch, [""])
    g_pad.Length = thickness_mm
    g_pad.Midplane = True
    return g_body


def _assert_solid_manifold(body: Any, label: str) -> None:
    """Spec 011 FR-008: a cut body must remain a single closed solid.

    Raises :class:`DeckConstructionError` on a non-manifold result (the spec
    009 regression guard).
    """
    shape = body.Shape
    if len(shape.Solids) != 1 or not shape.isValid():
        raise DeckConstructionError(
            f"{label} is non-manifold after glazing cuts "
            f"(solids={len(shape.Solids)}, valid={shape.isValid()})"
        )


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

    def _rect_sketch(name: str, datum: Any, half_width_mm: float, base_z_local: float) -> Any:
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

    # spec 020 — dense Ruled=True curl. The forward `curl_sections` stations
    # trace a cosine drop over `leading_edge_curl_length` (smooth curve, 0 mm
    # Z-overshoot — spike-confirmed), then a final aft station gives the taper.
    # Ruled=False is NOT used (it overshoots Z; spec 018 evidence).
    center_z_mm = (hardtop_underside_z_mm + hardtop_topside_z_mm) / 2.0
    curl_len = min(ht.leading_edge_curl_length, ht.length)

    def _width_at(x_local: float) -> float:
        t = x_local / max(ht.length, 1e-9)
        return ht.forward_width + (ht.aft_width - ht.forward_width) * t

    def _curl_drop_at(x_local: float) -> float:
        # Cosine ease from full drop at the leading edge to 0 at curl end.
        if x_local >= curl_len:
            return 0.0
        return curl_drop_mm * (0.5 + 0.5 * math.cos(math.pi * x_local / curl_len))

    # Station X positions: dense across the curl, plus the aft end.
    curl_xs = [
        fwd_x_mm + curl_len * (i / (ht.curl_sections - 1)) for i in range(ht.curl_sections)
    ]
    station_xs = [*curl_xs, aft_x_mm]
    sketches: list[Any] = []
    for idx, x_mm in enumerate(station_xs):
        x_local = x_mm - fwd_x_mm
        datum = _make_xz_datum_at_x(f"HardtopDatum{idx}", x_mm, center_z_mm)
        sketch = _rect_sketch(
            f"HardtopSketch{idx}", datum, _width_at(x_local) / 2.0, -_curl_drop_at(x_local)
        )
        sketches.append(sketch)
    target_doc.recompute()

    loft = body.newObject("PartDesign::AdditiveLoft", "HardtopLoft")
    added.append(loft)
    loft.Profile = (sketches[0], [""])
    loft.Sections = [(s, [""]) for s in sketches[1:]]
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
                body = target_doc.addObject("PartDesign::Body", f"Deck_Pillar_{side}_{idx}")
                added.append(body)
                target_doc.recompute()

                datum = _pd_make_datum_xy(body, f"Pillar{side}{idx}Datum", deck_z_mm, added)
                sketch = body.newObject("Sketcher::SketchObject", f"Pillar{side}{idx}Sketch")
                added.append(sketch)
                sketch.AttachmentSupport = [(datum, "")]
                sketch.MapMode = "FlatFace"
                center = FreeCAD.Vector(x_mm, sign * pillar_y_mm, 0)
                circle = Part.Circle(center, FreeCAD.Vector(0, 0, 1), pp.diameter / 2.0)
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
        compound_obj.Shape = (
            Part.Vertex(FreeCAD.Vector(0, 0, 0)).toShape() if False else (Part.makeCompound([]))
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
    dimensions, not the per-post detail). spec 020 sweeps the top rail along
    the sheer via PartDesign::AdditivePipe (with a straight-Pad fallback).
    """
    import FreeCAD
    import Part
    import Sketcher

    sp = superstructure or parameters.to_superstructure_parameters()
    rp = sp.railings

    deck_top_z_mm = _resolve_deck_top_z_at(deck_plate, (rp.forward_x + rp.aft_x) / 2.0)
    rail_top_z_mm = deck_top_z_mm + rp.height_above_deck

    # Sample lateral Y at the railing's mid-station to position the rail
    # inboard from the sheer.
    deck_shape = deck_plate.body.Shape
    mid_x_mm = (rp.forward_x + rp.aft_x) / 2.0
    verts_at_mid = [v for v in deck_shape.Vertexes if abs(v.X - mid_x_mm) < 1500.0]
    outer_y_mm = max(abs(v.Y) for v in verts_at_mid) if verts_at_mid else deck_shape.BoundBox.YMax
    rail_y_mm = max(0.0, outer_y_mm - rp.inboard_offset_from_sheer)

    side_bodies: list[Any] = []
    for side, sign in (("Port", 1), ("Starboard", -1)):
        body = target_doc.addObject("PartDesign::Body", f"Deck_Railings_{side}")
        added.append(body)
        target_doc.recompute()

        # spec 020 — swept perimeter top-rail: a PartDesign::AdditivePipe of a
        # circular profile along a path that traces the sheer (Z rises toward
        # the bow), so the rail follows the deck edge instead of a flat bar.
        # Falls back to the spec 008 straight Pad if the sweep fails (FR-005).
        yz_plane = _pd_get_origin_plane(body, "YZ_Plane")

        def _straight_rail(
            body: Any = body, side: str = side, sign: int = sign, yz_plane: Any = yz_plane
        ) -> None:
            rail_datum = body.newObject("PartDesign::Plane", f"Rail{side}TopRailDatum")
            added.append(rail_datum)
            rail_datum.AttachmentSupport = [(yz_plane, "")]
            rail_datum.MapMode = "FlatFace"
            rail_datum.AttachmentOffset = FreeCAD.Placement(
                FreeCAD.Vector(0.0, rail_top_z_mm, rp.forward_x), FreeCAD.Rotation()
            )
            rail_sketch = body.newObject("Sketcher::SketchObject", f"Rail{side}TopRailSketch")
            added.append(rail_sketch)
            rail_sketch.AttachmentSupport = [(rail_datum, "")]
            rail_sketch.MapMode = "FlatFace"
            rail_sketch.addGeometry(
                Part.Circle(
                    FreeCAD.Vector(sign * rail_y_mm, 0, 0),
                    FreeCAD.Vector(0, 0, 1),
                    rp.top_rail_diameter / 2.0,
                ).toShape().Curve,
                False,
            )
            target_doc.recompute()
            rail_pad = body.newObject("PartDesign::Pad", f"Rail{side}TopRailPad")
            added.append(rail_pad)
            rail_pad.Profile = (rail_sketch, [""])
            rail_pad.Length = rp.aft_x - rp.forward_x
            rail_pad.Midplane = False
            rail_pad.Reversed = False
            target_doc.recompute()

        swept_ok = False
        try:
            # Path on an XZ-parallel datum offset to Y = sign*rail_y; tracing
            # (x, deck_top_z(x)+height) so the rail Z follows the sheer.
            xz_plane = _pd_get_origin_plane(body, "XZ_Plane")
            path_datum = body.newObject("PartDesign::Plane", f"Rail{side}PathDatum")
            added.append(path_datum)
            path_datum.AttachmentSupport = [(xz_plane, "")]
            path_datum.MapMode = "FlatFace"
            # XZ_Plane normal = global Y (local Z); offset to Y = sign*rail_y.
            path_datum.AttachmentOffset = FreeCAD.Placement(
                FreeCAD.Vector(0.0, 0.0, sign * rail_y_mm), FreeCAD.Rotation()
            )
            path_sketch = body.newObject("Sketcher::SketchObject", f"Rail{side}PathSketch")
            added.append(path_sketch)
            path_sketch.AttachmentSupport = [(path_datum, "")]
            path_sketch.MapMode = "FlatFace"
            n_path = 7
            ppts = []
            for i in range(n_path):
                xi = rp.forward_x + (rp.aft_x - rp.forward_x) * (i / (n_path - 1))
                zi = _resolve_deck_top_z_at(deck_plate, xi) + rp.height_above_deck
                ppts.append(FreeCAD.Vector(xi, zi, 0))  # local x=globalX, y=globalZ
            pids = [
                path_sketch.addGeometry(Part.LineSegment(ppts[k], ppts[k + 1]), False)
                for k in range(n_path - 1)
            ]
            for k in range(n_path - 2):
                path_sketch.addConstraint(
                    Sketcher.Constraint("Coincident", pids[k], 2, pids[k + 1], 1)
                )
            # Profile circle on YZ datum at the forward end (normal = path tangent).
            prof_datum = body.newObject("PartDesign::Plane", f"Rail{side}ProfDatum")
            added.append(prof_datum)
            prof_datum.AttachmentSupport = [(yz_plane, "")]
            prof_datum.MapMode = "FlatFace"
            prof_datum.AttachmentOffset = FreeCAD.Placement(
                FreeCAD.Vector(0.0, 0.0, rp.forward_x), FreeCAD.Rotation()
            )
            prof_sketch = body.newObject("Sketcher::SketchObject", f"Rail{side}ProfSketch")
            added.append(prof_sketch)
            prof_sketch.AttachmentSupport = [(prof_datum, "")]
            prof_sketch.MapMode = "FlatFace"
            z0 = _resolve_deck_top_z_at(deck_plate, rp.forward_x) + rp.height_above_deck
            prof_sketch.addGeometry(
                Part.Circle(
                    FreeCAD.Vector(sign * rail_y_mm, z0, 0),
                    FreeCAD.Vector(0, 0, 1),
                    rp.top_rail_diameter / 2.0,
                ).toShape().Curve,
                False,
            )
            target_doc.recompute()
            pipe = body.newObject("PartDesign::AdditivePipe", f"Rail{side}TopRailPipe")
            added.append(pipe)
            pipe.Profile = prof_sketch
            pipe.Spine = path_sketch
            target_doc.recompute()
            sh = pipe.Shape
            swept_ok = sh is not None and not sh.isNull() and sh.isValid() and len(sh.Solids) == 1
        except BaseException:
            swept_ok = False
        if not swept_ok:
            _straight_rail()

        # Posts: one Pad per post, evenly spaced.
        if rp.post_count_per_side > 0:
            if rp.post_count_per_side == 1:
                post_xs = [(rp.forward_x + rp.aft_x) / 2.0]
            else:
                step = (rp.aft_x - rp.forward_x) / (rp.post_count_per_side - 1)
                post_xs = [rp.forward_x + i * step for i in range(rp.post_count_per_side)]
            for idx, px_mm in enumerate(post_xs, start=1):
                post_datum = _pd_make_datum_xy(
                    body, f"Rail{side}Post{idx}Datum", deck_top_z_mm, added
                )
                post_sketch = body.newObject("Sketcher::SketchObject", f"Rail{side}Post{idx}Sketch")
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

                post_pad = body.newObject("PartDesign::Pad", f"Rail{side}Post{idx}Pad")
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
# Spec 010 — deck-hardware helpers + sub-Body builders (data-model §2, §5)
#
# Every hardware item is a PartDesign::Body (or a Part::Compound of bodies),
# seated on the ACTUAL sampled hull/deck geometry via _sample_hull_sheer +
# _resolve_deck_top_z_at (FR-004), mirroring the spec 008 superstructure
# builders. All shapes are deterministic functions of (hull, deck, params).
# ---------------------------------------------------------------------------


def _sheer_samples_mm(hull: Hull) -> list[tuple[float, float, float]]:
    """The five sheer-line samples in mm (port half, positive Y), ascending X."""
    return [(x * _MM_PER_M, y * _MM_PER_M, z * _MM_PER_M) for x, y, z in _sample_hull_sheer(hull)]


def _interp_outer_y_at(samples_mm: list[tuple[float, float, float]], x_mm: float) -> float:
    """Linearly interpolate the sheer half-beam (outer Y, mm) at longitudinal X."""
    pts = sorted(samples_mm, key=lambda p: p[0])
    if x_mm <= pts[0][0]:
        return pts[0][1]
    if x_mm >= pts[-1][0]:
        return pts[-1][1]
    for i in range(len(pts) - 1):
        x1, y1, _ = pts[i]
        x2, y2, _ = pts[i + 1]
        if x1 <= x_mm <= x2:
            if x2 == x1:
                return (y1 + y2) / 2.0
            t = (x_mm - x1) / (x2 - x1)
            return y1 + t * (y2 - y1)
    return pts[-1][1]


def _pd_make_datum_yz(body: Any, name: str, x_mm: float, z_mm: float, added: list[Any]) -> Any:
    """PartDesign datum parallel to YZ at global (x_mm, 0, z_mm).

    YZ_Plane local frame: local X = global Y, local Y = global Z, local Z =
    global X (normal). So the local AttachmentOffset vector is (0, z_mm, x_mm).
    """
    import FreeCAD

    yz_plane = _pd_get_origin_plane(body, "YZ_Plane")
    datum = body.newObject("PartDesign::Plane", name)
    added.append(datum)
    datum.AttachmentSupport = [(yz_plane, "")]
    datum.MapMode = "FlatFace"
    datum.AttachmentOffset = FreeCAD.Placement(FreeCAD.Vector(0.0, z_mm, x_mm), FreeCAD.Rotation())
    return datum


def _pd_make_datum_xz(
    body: Any, name: str, x_mm: float, y_mm: float, z_mm: float, added: list[Any]
) -> Any:
    """PartDesign datum parallel to XZ at global (x_mm, y_mm, z_mm).

    XZ_Plane local frame: local X = global X, local Y = global Z, local Z =
    global Y (normal). So the local AttachmentOffset vector is (x_mm, z_mm, y_mm).
    Padding a sketch on this datum extrudes along +global Y (transverse).
    """
    import FreeCAD

    xz_plane = _pd_get_origin_plane(body, "XZ_Plane")
    datum = body.newObject("PartDesign::Plane", name)
    added.append(datum)
    datum.AttachmentSupport = [(xz_plane, "")]
    datum.MapMode = "FlatFace"
    datum.AttachmentOffset = FreeCAD.Placement(FreeCAD.Vector(x_mm, z_mm, y_mm), FreeCAD.Rotation())
    return datum


def _pd_circle_pad(
    body: Any,
    datum: Any,
    name: str,
    center_u: float,
    center_v: float,
    radius: float,
    length: float,
    added: list[Any],
) -> Any:
    """Add a circular sketch on a datum + a Pad of given length (a tube/cylinder)."""
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
    pad.Midplane = False
    pad.Reversed = False
    return pad


# ---------------------------------------------------------------------------
# Spec 022 — deck-hardware detailing helpers (contoured/swept refinements).
#
# All construction stays PartDesign (Sketcher + AdditiveLoft/AdditivePipe/
# Revolution/Pad/Pocket) so the parametric history survives GUI editing
# (constitution III). A FreeCAD 1.1.1 spike de-risked each construction:
#   - rounded rubrail section AdditiveLoft (Solids==1, valid)
#   - catenary AdditivePipe (a = span^2 / 8*sag, horizontal-start profile)
#   - Revolution elbow/weld-bead torus (section plane MUST contain the axis)
#   - tapered base AdditiveLoft + 180-deg Revolution horn (one body, Solids==1)
# ---------------------------------------------------------------------------


def _discard_body(body: Any, target_doc: Any, added: list[Any]) -> None:
    """Remove a failed PartDesign body (and its tracked features) from the doc.

    Used by manifold-or-fallback gates: when a refined construction does not
    yield a single valid solid, the partial body is discarded before the
    fallback rebuilds it, so neither the document nor the rollback list keeps a
    dangling object. Tolerant of already-removed children.
    """
    names = {body.Name}
    for child in list(getattr(body, "Group", []) or []):
        names.add(child.Name)
    added[:] = [o for o in added if getattr(o, "Name", None) not in names]
    with contextlib.suppress(BaseException):
        target_doc.removeObject(body.Name)


def _rubrail_section_sketch(
    body: Any,
    name: str,
    x_along_mm: float,
    y_center_mm: float,
    top_z_mm: float,
    half_t_mm: float,
    half_h_mm: float,
    profile_radius_mm: float,
    *,
    rounded: bool,
    sign: int,
    added: list[Any],
) -> Any:
    """A moulded rubrail cross-section on a YZ-parallel datum at ``x_along_mm``.

    Local frame (YZ datum): local x = global Y, local y = global Z. The OUTBOARD
    face is the ``sign``-ward Y side (port = +Y). When ``rounded`` the two
    outboard corners are arc-filleted (the moulded-teak look); otherwise they are
    chamfered with straight segments (the manifold-safe fallback, FR-001).
    """
    import FreeCAD
    import Part

    datum = _pd_make_datum_yz(body, f"{name}Datum", x_along_mm, 0.0, added)
    sketch = body.newObject("Sketcher::SketchObject", name)
    added.append(sketch)
    sketch.AttachmentSupport = [(datum, "")]
    sketch.MapMode = "FlatFace"

    f = min(profile_radius_mm, half_t_mm * 0.95, half_h_mm * 0.95)
    inb = y_center_mm - sign * half_t_mm  # inboard Y (toward centerline)
    out = y_center_mm + sign * half_t_mm  # outboard Y
    bot = top_z_mm - half_h_mm
    top = top_z_mm + half_h_mm

    def v(yy: float, zz: float) -> Any:
        return FreeCAD.Vector(yy, zz, 0)

    gids: list[int] = []
    if rounded:
        out_b = out - sign * f
        out_a1 = FreeCAD.Vector(out, bot + f, 0)
        out_a2 = FreeCAD.Vector(out, top - f, 0)
        out_t = out - sign * f
        # arc midpoints (45 deg) for the two outboard corners
        m1 = FreeCAD.Vector(out - sign * f + sign * f * math.cos(math.pi / 4), bot + f - f * math.cos(math.pi / 4), 0)
        m2 = FreeCAD.Vector(out - sign * f + sign * f * math.cos(math.pi / 4), top - f + f * math.cos(math.pi / 4), 0)
        gids.append(sketch.addGeometry(Part.LineSegment(v(inb, bot), v(out_b, bot)), False))
        gids.append(sketch.addGeometry(Part.Arc(v(out_b, bot), m1, out_a1), False))
        gids.append(sketch.addGeometry(Part.LineSegment(out_a1, out_a2), False))
        gids.append(sketch.addGeometry(Part.Arc(out_a2, m2, v(out_t, top)), False))
        gids.append(sketch.addGeometry(Part.LineSegment(v(out_t, top), v(inb, top)), False))
        gids.append(sketch.addGeometry(Part.LineSegment(v(inb, top), v(inb, bot)), False))
    else:
        # Chamfered: bevel the two outboard corners with straight segments.
        out_b = out - sign * f
        out_t = out - sign * f
        gids.append(sketch.addGeometry(Part.LineSegment(v(inb, bot), v(out_b, bot)), False))
        gids.append(sketch.addGeometry(Part.LineSegment(v(out_b, bot), v(out, bot + f)), False))
        gids.append(sketch.addGeometry(Part.LineSegment(v(out, bot + f), v(out, top - f)), False))
        gids.append(sketch.addGeometry(Part.LineSegment(v(out, top - f), v(out_t, top)), False))
        gids.append(sketch.addGeometry(Part.LineSegment(v(out_t, top), v(inb, top)), False))
        gids.append(sketch.addGeometry(Part.LineSegment(v(inb, top), v(inb, bot)), False))
    _pd_close_loop_constraints(sketch, gids)
    return sketch


def _is_single_valid_solid(shape: Any) -> bool:
    """True iff ``shape`` is a non-null, valid, single-solid B-rep (FR-009)."""
    return (
        shape is not None
        and not shape.isNull()
        and shape.isValid()
        and len(shape.Solids) == 1
    )


def _pd_swept_tube_xz(
    body: Any,
    name: str,
    y_mm: float,
    xz_points: list[tuple[float, float]],
    radius_mm: float,
    added: list[Any],
) -> Any:
    """Sweep a circular tube of ``radius_mm`` along a planar XZ path.

    The spine lies in the XZ plane offset to global Y = ``y_mm``; ``xz_points``
    are ``(global_x, global_z)`` waypoints joined by line segments (sample curves
    finely). The profile circle sits on a YZ datum at the first waypoint, so the
    section is perpendicular to the spine when the path starts roughly horizontal
    (the lifeline catenary and the cleat horn arch both do). Returns the
    ``PartDesign::AdditivePipe`` feature.
    """
    import FreeCAD
    import Part
    import Sketcher

    x0, z0 = xz_points[0]
    xz_plane = _pd_get_origin_plane(body, "XZ_Plane")
    path_datum = body.newObject("PartDesign::Plane", f"{name}PathDatum")
    added.append(path_datum)
    path_datum.AttachmentSupport = [(xz_plane, "")]
    path_datum.MapMode = "FlatFace"
    path_datum.AttachmentOffset = FreeCAD.Placement(
        FreeCAD.Vector(0.0, 0.0, y_mm), FreeCAD.Rotation()
    )
    path_sketch = body.newObject("Sketcher::SketchObject", f"{name}PathSketch")
    added.append(path_sketch)
    path_sketch.AttachmentSupport = [(path_datum, "")]
    path_sketch.MapMode = "FlatFace"
    pts = [FreeCAD.Vector(px, pz, 0) for (px, pz) in xz_points]  # local x=globalX, y=globalZ
    pids = [
        path_sketch.addGeometry(Part.LineSegment(pts[k], pts[k + 1]), False)
        for k in range(len(pts) - 1)
    ]
    for k in range(len(pts) - 2):
        path_sketch.addConstraint(Sketcher.Constraint("Coincident", pids[k], 2, pids[k + 1], 1))

    yz_plane = _pd_get_origin_plane(body, "YZ_Plane")
    prof_datum = body.newObject("PartDesign::Plane", f"{name}ProfDatum")
    added.append(prof_datum)
    prof_datum.AttachmentSupport = [(yz_plane, "")]
    prof_datum.MapMode = "FlatFace"
    prof_datum.AttachmentOffset = FreeCAD.Placement(
        FreeCAD.Vector(0.0, 0.0, x0), FreeCAD.Rotation()
    )
    prof_sketch = body.newObject("Sketcher::SketchObject", f"{name}ProfSketch")
    added.append(prof_sketch)
    prof_sketch.AttachmentSupport = [(prof_datum, "")]
    prof_sketch.MapMode = "FlatFace"
    prof_sketch.addGeometry(
        Part.Circle(FreeCAD.Vector(y_mm, z0, 0), FreeCAD.Vector(0, 0, 1), radius_mm).toShape().Curve,
        False,
    )
    pipe = body.newObject("PartDesign::AdditivePipe", f"{name}Pipe")
    added.append(pipe)
    pipe.Profile = prof_sketch
    pipe.Spine = path_sketch
    return pipe


def _pd_catenary_pipe(
    body: Any,
    name: str,
    y_mm: float,
    forward_x_mm: float,
    aft_x_mm: float,
    base_z_mm: float,
    sag_depth_mm: float,
    radius_mm: float,
    added: list[Any],
    *,
    n_samples: int = 10,
) -> Any | None:
    """Sweep a circular tube along a true catenary between two railing posts.

    The tube dips ``sag_depth_mm`` at mid-span following ``z(x) = a*cosh(x/a) - a``
    with ``a = span^2 / (8*sag)`` (the standard shallow-catenary coefficient).
    Returns the AdditivePipe feature, or ``None`` for a degenerate span/sag (the
    caller then uses the straight fallback, FR-008).
    """
    span = aft_x_mm - forward_x_mm
    if span <= 0 or sag_depth_mm <= 0:
        return None
    a = span * span / (8.0 * sag_depth_mm)
    pts: list[tuple[float, float]] = []
    for i in range(n_samples + 1):
        xg = forward_x_mm + span * i / n_samples
        xx = -span / 2.0 + span * i / n_samples
        dip = a * math.cosh(xx / a) - a
        pts.append((xg, base_z_mm - dip))
    return _pd_swept_tube_xz(body, name, y_mm, pts, radius_mm, added)


def _validate_cross_deck_hardware(
    deck_plate: DeckPlate,
    cabin_trunk: CabinTrunk,
    hardware: DeckHardwareParameters,
) -> None:
    """Cross-deck hardware collision checks (FR-018, data-model §6).

    Runs after the deck plate + cabin trunk exist (their extents are needed),
    but before any hardware body is built. Raises :class:`DeckParameterError`
    so build_deck's rollback restores the pre-call document state.

    Coordinate convention (from the hull module): the transom (stern) is at
    X = XMin and the stem (bow) is at X = XMax, so the foredeck — and anything
    "forward of the cabin trunk" — is the high-X region beyond the cabin's
    bow-facing (XMax) edge.
    """
    deck_bb = deck_plate.body.Shape.BoundBox
    cabin_bb = cabin_trunk.body.Shape.BoundBox

    rb = hardware.rubrail
    if rb.forward_x < deck_bb.XMin - 1.0 or rb.aft_x > deck_bb.XMax + 1.0:
        raise DeckParameterError(
            "rubrail_extent<>deck_extent",
            None,
            f"rubrail [forward_x, aft_x] must lie within the deck X-extent "
            f"[{deck_bb.XMin:.0f}, {deck_bb.XMax:.0f}] mm",
        )

    al = hardware.anchor_locker
    locker_aft = al.center_x - al.length / 2.0  # stern-facing edge (lower X)
    locker_fwd = al.center_x + al.length / 2.0  # bow-facing edge (higher X)
    if locker_aft < cabin_bb.XMax:
        raise DeckParameterError(
            "anchor_locker_center_x<>cabin_trunk",
            al.center_x,
            f"anchor locker must sit forward of the cabin trunk "
            f"(stern edge {locker_aft:.0f} mm must be >= cabin bow edge "
            f"{cabin_bb.XMax:.0f} mm)",
        )
    if locker_fwd > deck_bb.XMax:
        raise DeckParameterError(
            "anchor_locker_center_x<>deck_forward_edge",
            al.center_x,
            f"anchor locker must fit within the deck (bow edge {locker_fwd:.0f} mm "
            f"must be <= deck bow edge {deck_bb.XMax:.0f} mm)",
        )


def _build_rubrail(
    hull: Hull,
    deck_plate: DeckPlate,
    target_doc: Any,
    added: list[Any],
    *,
    hardware: DeckHardwareParameters,
) -> Rubrail:
    """Build the rubrail as a Part::Compound of port + starboard PartDesign Bodies.

    spec 022: each side is an AdditiveLoft (Ruled=True) of a MOULDED section —
    a rounded outboard face by default, with a manifold-or-fallback gate to a
    chamfered (straight-line) section if the rounded loft fails (FR-001). A
    separate chrome insert strip body runs the rubrail length per side (FR-002).
    Implements spec 008's deferred ``SuperstructureBundle.rubrail`` (FR-005).
    """
    import Part

    rp = hardware.rubrail
    samples = _sheer_samples_mm(hull)

    # Stations: the forward/aft bounds plus every sampled station strictly
    # between them, ascending — so the loft follows the sheer curvature.
    inner = [p[0] for p in samples if rp.forward_x < p[0] < rp.aft_x]
    stations = [rp.forward_x, *sorted(inner), rp.aft_x]

    half_h = rp.height / 2.0
    half_t = rp.thickness / 2.0

    def _build_side(side: str, sign: int, *, rounded: bool) -> Any:
        body = target_doc.addObject("PartDesign::Body", f"Deck_Rubrail_{side}")
        added.append(body)
        target_doc.recompute()
        section_sketches: list[Any] = []
        for idx, x_mm in enumerate(stations):
            outer_y = _interp_outer_y_at(samples, x_mm)
            top_z = _resolve_deck_top_z_at(deck_plate, x_mm)
            section_sketches.append(
                _rubrail_section_sketch(
                    body,
                    f"Rubrail{side}{'R' if rounded else 'C'}Sketch{idx}",
                    x_mm,
                    sign * outer_y,
                    top_z,
                    half_t,
                    half_h,
                    rp.outboard_fillet if rounded else rp.chamfer_width,
                    rounded=rounded,
                    sign=sign,
                    added=added,
                )
            )
        target_doc.recompute()
        loft = body.newObject("PartDesign::AdditiveLoft", f"Rubrail{side}Loft")
        added.append(loft)
        loft.Profile = (section_sketches[0], [""])
        loft.Sections = [(s, [""]) for s in section_sketches[1:]]
        loft.Ruled = True  # spec 009: Ruled=False overshoots on this profile
        loft.Closed = False
        target_doc.recompute()
        return body

    side_bodies: list[Any] = []
    for side, sign in (("Port", 1), ("Starboard", -1)):
        if rp.rounded_profile:
            # Opt-in rounded face, guarded by a manifold-or-fallback gate to the
            # deterministic chamfer (FR-001).
            try:
                body = _build_side(side, sign, rounded=True)
                ok = _is_single_valid_solid(body.Shape)
            except BaseException:
                ok = False
                body = None
            if not ok:
                if body is not None:
                    _discard_body(body, target_doc, added)
                body = _build_side(side, sign, rounded=False)
        else:
            # Default: the chamfered (straight-line) section is byte-reproducible
            # under cumulative FreeCAD state (constitution II).
            body = _build_side(side, sign, rounded=False)
        side_bodies.append(body)

    # Chrome insert: a thin strip lofted along the outboard face of each side.
    insert_bodies: list[Any] = []
    if rp.chrome_insert:
        for side, sign in (("Port", 1), ("Starboard", -1)):
            ins = target_doc.addObject("PartDesign::Body", f"Deck_RubrailChromeInsert_{side}")
            added.append(ins)
            target_doc.recompute()
            ins_sketches: list[Any] = []
            for idx, x_mm in enumerate(stations):
                outer_y = _interp_outer_y_at(samples, x_mm)
                top_z = _resolve_deck_top_z_at(deck_plate, x_mm)
                out = sign * (outer_y + half_t)
                ins_sketches.append(
                    _slab_sketch_rect(
                        ins,
                        _pd_make_datum_yz(ins, f"Insert{side}Datum{idx}", x_mm, 0.0, added),
                        f"Insert{side}Sketch{idx}",
                        rp.insert_thickness / 2.0,
                        rp.insert_height / 2.0,
                        top_z,
                        added,
                        center_w_mm=out - sign * rp.insert_thickness / 2.0,
                    )
                )
            target_doc.recompute()
            iloft = ins.newObject("PartDesign::AdditiveLoft", f"Insert{side}Loft")
            added.append(iloft)
            iloft.Profile = (ins_sketches[0], [""])
            iloft.Sections = [(s, [""]) for s in ins_sketches[1:]]
            iloft.Ruled = True
            iloft.Closed = False
            target_doc.recompute()
            insert_bodies.append(ins)

    # Teak rubrail compound (role "Deck_Rubrail" → trim).
    compound = target_doc.addObject("Part::Feature", "Deck_Rubrail")
    compound.Shape = Part.makeCompound([b.Shape for b in side_bodies])
    added.append(compound)
    compound.addProperty("App::PropertyLength", "RubrailHeight", "Deck", "Rubrail height")
    compound.RubrailHeight = rp.height
    compound.addProperty(
        "App::PropertyStringList", "SideBodyLabels", "Deck", "Port + starboard rubrail bodies"
    )
    compound.SideBodyLabels = [b.Label for b in side_bodies]

    # Chrome insert compound (separate render target so it colours metal, not
    # teak — apply_render_attributes does not recurse into compound members).
    insert_compound = None
    if insert_bodies:
        insert_compound = target_doc.addObject("Part::Feature", "Deck_RubrailChromeInsert")
        insert_compound.Shape = Part.makeCompound([b.Shape for b in insert_bodies])
        added.append(insert_compound)
        insert_compound.addProperty(
            "App::PropertyStringList", "SideBodyLabels", "Deck", "Port + starboard insert bodies"
        )
        insert_compound.SideBodyLabels = [b.Label for b in insert_bodies]

    return Rubrail(
        body=compound,
        height=rp.height / _MM_PER_M,
        thickness=rp.thickness / _MM_PER_M,
        has_chrome_insert=insert_compound is not None,
        insert_body=insert_compound,
    )


def _build_bow_pulpit(
    hull: Hull,
    deck_plate: DeckPlate,
    target_doc: Any,
    added: list[Any],
    *,
    hardware: DeckHardwareParameters,
) -> BowPulpit:
    """Build the bow pulpit as a single tubular PartDesign::Body (FR-006).

    Per side: a vertical stanchion (cylinder padded +Z from the deck top) plus
    a fore-aft top-rail tube (cylinder padded +X) at the stanchion-top height.
    A transverse tube (padded +Y) joins the two forward ends across the bow.
    Symmetric about the centerline. Zero-stanchion fallback yields an empty
    body footprint (FR-016).

    spec 022: the hard L-joints are rounded by ``AdditiveSphere`` corner balls
    (radiused-bend reading) and ``AdditiveTorus`` weld beads wrap each joint
    (welded-joint reading), all parametric primitives fused into the body. A
    manifold-or-fallback gate (FR-008) keeps just the straight tubes if the
    refinement fails to stay a single valid solid.
    """
    import FreeCAD

    bp = hardware.bow_pulpit
    samples = _sheer_samples_mm(hull)
    radius = bp.tube_diameter / 2.0

    # Stanchion seat: near the bow (XMax = stem) but set back so the deck
    # still has beam. The very stem sample has outer_y = 0 (collapses to a
    # vertex), so seating exactly there would give a zero-width pulpit;
    # 90% of the deck X range keeps a non-degenerate base.
    deck_bb = deck_plate.body.Shape.BoundBox
    x_range = deck_bb.XMax - deck_bb.XMin
    stanchion_x = deck_bb.XMin + 0.90 * x_range
    deck_top_z = _resolve_deck_top_z_at(deck_plate, stanchion_x)
    outer_y = max(_interp_outer_y_at(samples, stanchion_x), 50.0)
    rail_z = deck_top_z + bp.height
    fwd_x = stanchion_x + bp.forward_extent

    body = target_doc.addObject("PartDesign::Body", "Deck_BowPulpit")
    added.append(body)
    target_doc.recompute()

    # Number of stanchions split across sides (default 2 → one per side).
    per_side = max(bp.stanchion_count // 2, 1 if bp.stanchion_count > 0 else 0)
    if per_side > 0:
        for side, sign in (("Port", 1), ("Starboard", -1)):
            y = sign * outer_y
            # Vertical stanchion: XY datum at deck top, circle padded +Z.
            v_datum = _pd_make_datum_xy(body, f"Pulpit{side}StanchionDatum", deck_top_z, added)
            _pd_circle_pad(
                body, v_datum, f"Pulpit{side}Stanchion", stanchion_x, y, radius, bp.height, added
            )
            target_doc.recompute()
            # Fore-aft top rail: YZ datum at (stanchion_x, rail_z), circle padded +X.
            if bp.forward_extent > 0:
                r_datum = _pd_make_datum_yz(
                    body, f"Pulpit{side}RailDatum", stanchion_x, rail_z, added
                )
                _pd_circle_pad(
                    body, r_datum, f"Pulpit{side}Rail", y, 0.0, radius, bp.forward_extent, added
                )
                target_doc.recompute()
        # Transverse tube across the bow forward ends (padded +Y from starboard to port).
        t_datum = _pd_make_datum_xz(body, "PulpitCrossDatum", fwd_x, -outer_y, rail_z, added)
        _pd_circle_pad(body, t_datum, "PulpitCross", 0.0, 0.0, radius, 2.0 * outer_y, added)
        target_doc.recompute()

    # spec 022 — radiused-bend corner balls + welded-joint beads. Each is an
    # additive primitive placed at a joint; the gate reverts to the straight
    # tubes (already built above) on any failure.
    has_bends = False
    has_beads = False
    if per_side > 0 and (bp.bend_radius > 0 or bp.weld_beads):
        prev_tip = body.Tip  # restore on fallback so the body keeps a valid Tip
        refinement: list[Any] = []

        # Additive primitives have no AttachmentSupport, so MapMode is
        # 'Deactivated' and AttachmentOffset is IGNORED — position via .Placement.
        def _ball(name: str, x: float, y: float, z: float, r: float) -> None:
            sph = body.newObject("PartDesign::AdditiveSphere", name)
            added.append(sph)
            refinement.append(sph)
            sph.Radius = r
            sph.Placement = FreeCAD.Placement(FreeCAD.Vector(x, y, z), FreeCAD.Rotation())

        def _bead(name: str, x: float, y: float, z: float, rot: Any) -> None:
            tor = body.newObject("PartDesign::AdditiveTorus", name)
            added.append(tor)
            refinement.append(tor)
            tor.Radius1 = radius
            tor.Radius2 = bp.weld_bead_radius
            tor.Placement = FreeCAD.Placement(FreeCAD.Vector(x, y, z), rot)

        try:
            for side, sign in (("Port", 1), ("Starboard", -1)):
                y = sign * outer_y
                if bp.bend_radius > 0:
                    # Corner ball rounds the stanchion-to-rail L-joint. Sized to
                    # robustly engulf both tube ends (a marginal/tangent ball
                    # leaves a 2-solid body), so the fuse stays a single solid.
                    _ball(
                        f"Pulpit{side}CornerBall",
                        stanchion_x,
                        y,
                        rail_z,
                        radius + max(bp.bend_radius * 0.4, radius * 0.8),
                    )
                if bp.weld_beads:
                    # Bead at the stanchion base (tube along Z → torus axis Z).
                    _bead(
                        f"Pulpit{side}BaseBead",
                        stanchion_x,
                        y,
                        deck_top_z + radius,
                        FreeCAD.Rotation(),
                    )
                    if bp.forward_extent > 0:
                        # Bead at the rail/cross forward corner (tube along Y → axis Y).
                        _bead(
                            f"Pulpit{side}FwdBead",
                            fwd_x,
                            y,
                            rail_z,
                            FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), 90),
                        )
            target_doc.recompute()
            if not _is_single_valid_solid(body.Shape):
                raise DeckConstructionError("pulpit refinement non-manifold")
            has_bends = bp.bend_radius > 0
            has_beads = bp.weld_beads
        except BaseException:
            # Roll back just the refinement features; keep the straight tubes.
            for obj in refinement:
                added[:] = [a for a in added if getattr(a, "Name", None) != obj.Name]
                with contextlib.suppress(BaseException):
                    target_doc.removeObject(obj.Name)
            # Restore the Tip to the last straight-tube feature so the body keeps
            # a valid Shape (removing the refinement features orphaned the Tip).
            with contextlib.suppress(BaseException):
                body.Tip = prev_tip
            target_doc.recompute()

    body.addProperty("App::PropertyLength", "TubeDiameter", "Deck", "Bow pulpit tube diameter")
    body.TubeDiameter = bp.tube_diameter
    return BowPulpit(
        body=body,
        tube_diameter=bp.tube_diameter / _MM_PER_M,
        height=bp.height / _MM_PER_M,
        has_radiused_bends=has_bends,
        has_weld_beads=has_beads,
    )


def _build_anchor_locker(
    deck_plate: DeckPlate,
    cabin_trunk: CabinTrunk,
    target_doc: Any,
    added: list[Any],
    *,
    hardware: DeckHardwareParameters,
) -> AnchorLocker:
    """Build the anchor locker as a raised box PartDesign::Body (FR-008).

    A rectangular sketch (length x width) on an XY-parallel datum at the
    foredeck top Z near the bow, padded up by ``height``. NOT a boolean on the
    hull/deck. Placement validated by build_deck before this runs.

    spec 022: a blind ``PartDesign::Pocket`` cavity is cut into the locker TOP
    (on the locker body only — FR-007 keeps the hull/deck untouched), leaving a
    floor + walls; a separate teak lid body is seated over the cavity (FR-006).
    ``cavity_depth == 0`` reproduces the spec 010 solid box (no cavity, no lid).
    """
    import FreeCAD
    import Part

    al = hardware.anchor_locker
    deck_top_z = _resolve_deck_top_z_at(deck_plate, al.center_x)
    fwd_x = al.center_x - al.length / 2.0
    aft_x = al.center_x + al.length / 2.0
    half_w = al.width / 2.0
    top_z = deck_top_z + al.height

    body = target_doc.addObject("PartDesign::Body", "Deck_AnchorLocker")
    added.append(body)
    target_doc.recompute()

    datum = _pd_make_datum_xy(body, "AnchorLockerDatum", deck_top_z, added)
    sketch = body.newObject("Sketcher::SketchObject", "AnchorLockerSketch")
    added.append(sketch)
    sketch.AttachmentSupport = [(datum, "")]
    sketch.MapMode = "FlatFace"
    # XY datum: sketch local x = global X, local y = global Y.
    pts = [
        FreeCAD.Vector(fwd_x, -half_w, 0),
        FreeCAD.Vector(aft_x, -half_w, 0),
        FreeCAD.Vector(aft_x, half_w, 0),
        FreeCAD.Vector(fwd_x, half_w, 0),
    ]
    line_ids: list[int] = []
    for i in range(4):
        j = (i + 1) % 4
        line_ids.append(sketch.addGeometry(Part.LineSegment(pts[i], pts[j]), False))
    _pd_close_loop_constraints(sketch, line_ids)
    target_doc.recompute()

    pad = body.newObject("PartDesign::Pad", "AnchorLockerPad")
    added.append(pad)
    pad.Profile = (sketch, [""])
    pad.Length = al.height
    pad.Midplane = False
    pad.Reversed = False
    target_doc.recompute()

    # spec 022 — recessed cavity (Pocket from the top face, blind) + separate lid.
    has_cavity = False
    lid_body: Any = None
    if al.cavity_depth > 0:
        cav_datum = _pd_make_datum_xy(body, "LockerCavityDatum", top_z, added)
        cav_sketch = body.newObject("Sketcher::SketchObject", "LockerCavitySketch")
        added.append(cav_sketch)
        cav_sketch.AttachmentSupport = [(cav_datum, "")]
        cav_sketch.MapMode = "FlatFace"
        cpts = [
            FreeCAD.Vector(fwd_x + al.cavity_inset, -half_w + al.cavity_inset, 0),
            FreeCAD.Vector(aft_x - al.cavity_inset, -half_w + al.cavity_inset, 0),
            FreeCAD.Vector(aft_x - al.cavity_inset, half_w - al.cavity_inset, 0),
            FreeCAD.Vector(fwd_x + al.cavity_inset, half_w - al.cavity_inset, 0),
        ]
        cids: list[int] = []
        for i in range(4):
            j = (i + 1) % 4
            cids.append(cav_sketch.addGeometry(Part.LineSegment(cpts[i], cpts[j]), False))
        _pd_close_loop_constraints(cav_sketch, cids)
        target_doc.recompute()
        pocket = body.newObject("PartDesign::Pocket", "LockerCavityPocket")
        added.append(pocket)
        pocket.Profile = (cav_sketch, [""])
        pocket.Length = al.cavity_depth
        pocket.Reversed = False
        target_doc.recompute()
        if not _is_single_valid_solid(body.Shape):
            raise DeckConstructionError("anchor-locker cavity produced a non-manifold solid")
        has_cavity = True

        if al.lid:
            lid_body = target_doc.addObject("PartDesign::Body", "Deck_AnchorLockerLid")
            added.append(lid_body)
            target_doc.recompute()
            lid_datum = _pd_make_datum_xy(lid_body, "LockerLidDatum", top_z, added)
            lid_sketch = lid_body.newObject("Sketcher::SketchObject", "LockerLidSketch")
            added.append(lid_sketch)
            lid_sketch.AttachmentSupport = [(lid_datum, "")]
            lid_sketch.MapMode = "FlatFace"
            # Lid footprint covers the cavity opening with a small overlap onto
            # the rim so it reads as a seated lid (half the inset).
            margin = al.cavity_inset / 2.0
            lpts = [
                FreeCAD.Vector(fwd_x + margin, -half_w + margin, 0),
                FreeCAD.Vector(aft_x - margin, -half_w + margin, 0),
                FreeCAD.Vector(aft_x - margin, half_w - margin, 0),
                FreeCAD.Vector(fwd_x + margin, half_w - margin, 0),
            ]
            lids: list[int] = []
            for i in range(4):
                j = (i + 1) % 4
                lids.append(lid_sketch.addGeometry(Part.LineSegment(lpts[i], lpts[j]), False))
            _pd_close_loop_constraints(lid_sketch, lids)
            target_doc.recompute()
            lid_pad = lid_body.newObject("PartDesign::Pad", "LockerLidPad")
            added.append(lid_pad)
            lid_pad.Profile = (lid_sketch, [""])
            lid_pad.Length = al.lid_thickness
            lid_pad.Midplane = False
            lid_pad.Reversed = False
            target_doc.recompute()

    body.addProperty("App::PropertyLength", "LockerLength", "Deck", "Anchor locker length")
    body.LockerLength = al.length
    return AnchorLocker(
        body=body,
        length=al.length / _MM_PER_M,
        width=al.width / _MM_PER_M,
        height=al.height / _MM_PER_M,
        has_cavity=has_cavity,
        lid_body=lid_body,
    )


def _build_cleats(
    hull: Hull,
    deck_plate: DeckPlate,
    target_doc: Any,
    added: list[Any],
    *,
    hardware: DeckHardwareParameters,
) -> Cleats:
    """Build mooring cleats as a Part::Compound of PartDesign Bodies (FR-009).

    ``count_per_station`` cleats per side at each of ``station_count`` stations
    (per-side semantics), mirrored port/starboard, each seated on the actual
    deck top. Each cleat = a base block Pad + a horizontal horn-bar tube.
    Zero-count fallback yields an empty compound (FR-016).
    """
    import FreeCAD
    import Part

    cp = hardware.cleats
    samples = _sheer_samples_mm(hull)
    deck_bb = deck_plate.body.Shape.BoundBox
    loa_mm = deck_bb.XMax - deck_bb.XMin

    cleat_bodies: list[Any] = []
    if cp.count_per_station > 0 and cp.station_count > 0:
        # Stations spread across [0.12, 0.88] of the deck X range.
        if cp.station_count == 1:
            fractions = [0.5]
        else:
            lo, hi = 0.12, 0.88
            step = (hi - lo) / (cp.station_count - 1)
            fractions = [lo + i * step for i in range(cp.station_count)]
        station_xs = [deck_bb.XMin + f * loa_mm for f in fractions]

        inboard = cp.length  # nudge cleats inboard from the sheer by ~one length
        half_w = cp.length * 0.18
        horn_radius = cp.height * 0.18
        hl = cp.length / 2.0
        base_h = cp.height * 0.5

        def _local_rect_sketch(
            body: Any, name: str, hx: float, hy: float, z: float
        ) -> Any:
            datum = _pd_make_datum_xy(body, name + "Datum", z, added)
            sk = body.newObject("Sketcher::SketchObject", name)
            added.append(sk)
            sk.AttachmentSupport = [(datum, "")]
            sk.MapMode = "FlatFace"
            p = [
                FreeCAD.Vector(-hx, -hy, 0),
                FreeCAD.Vector(hx, -hy, 0),
                FreeCAD.Vector(hx, hy, 0),
                FreeCAD.Vector(-hx, hy, 0),
            ]
            ids = [sk.addGeometry(Part.LineSegment(p[i], p[(i + 1) % 4]), False) for i in range(4)]
            _pd_close_loop_constraints(sk, ids)
            return sk

        seq = 0
        for x_mm in station_xs:
            outer_y = _interp_outer_y_at(samples, x_mm)
            deck_top_z = _resolve_deck_top_z_at(deck_plate, x_mm)
            for side, sign in (("Port", 1), ("Starboard", -1)):
                for k in range(cp.count_per_station):
                    seq += 1
                    # Multiple per-side cleats at a station nudge slightly aft.
                    cx = x_mm + k * (cp.length * 1.5)
                    cy = sign * max(0.0, outer_y - inboard)
                    body = target_doc.addObject("PartDesign::Body", f"Deck_Cleat_{side}_{seq}")
                    added.append(body)
                    target_doc.recompute()

                    # spec 022 — contoured casting: tapered base (Ruled=True loft,
                    # bottom footprint > top) + an arched horn (180-deg Revolution
                    # about the local Y axis whose arms drop into the base so the
                    # body fuses to a single solid). Built in LOCAL coordinates and
                    # seated via body.Placement.
                    s_bot = _local_rect_sketch(body, f"Cleat{seq}Bot", hl, half_w, 0.0)
                    s_top = _local_rect_sketch(
                        body, f"Cleat{seq}Top", hl * cp.base_taper, half_w * cp.base_taper, base_h
                    )
                    target_doc.recompute()
                    loft = body.newObject("PartDesign::AdditiveLoft", f"Cleat{seq}BaseLoft")
                    added.append(loft)
                    loft.Profile = (s_bot, [""])
                    loft.Sections = [(s_top, [""])]
                    loft.Ruled = True
                    target_doc.recompute()

                    # Arched horn: a shallow upward bulge swept along an XZ path
                    # (same proven AdditivePipe pattern as the lifeline catenary,
                    # bulging up instead of sagging). The arms sit on the base top
                    # (z=base_h) and the tube dips into the base so the body fuses
                    # to a single solid. Sample the parabolic arch into waypoints.
                    hl_horn = hl * 0.55
                    n_arch = 8
                    arch_pts: list[tuple[float, float]] = []
                    for i in range(n_arch + 1):
                        xx = -hl_horn + 2.0 * hl_horn * i / n_arch
                        rise = cp.horn_rise * (1.0 - (xx / hl_horn) ** 2)  # parabola, 0 at arms
                        arch_pts.append((xx, base_h + rise))
                    _pd_swept_tube_xz(body, f"Cleat{seq}Horn", 0.0, arch_pts, horn_radius, added)
                    target_doc.recompute()

                    # Seat the locally-built cleat on the actual deck station.
                    body.Placement = FreeCAD.Placement(
                        FreeCAD.Vector(cx, cy, deck_top_z), FreeCAD.Rotation()
                    )
                    target_doc.recompute()
                    if not _is_single_valid_solid(body.Shape):
                        raise DeckConstructionError(
                            f"cleat {side}{seq} produced a non-manifold solid"
                        )
                    cleat_bodies.append(body)

    compound = target_doc.addObject("Part::Feature", "Deck_Cleats")
    compound.Shape = (
        Part.makeCompound([b.Shape for b in cleat_bodies])
        if cleat_bodies
        else Part.makeCompound([])
    )
    added.append(compound)
    compound.addProperty("App::PropertyInteger", "CleatCount", "Deck", "Total cleat count")
    compound.CleatCount = len(cleat_bodies)
    compound.addProperty(
        "App::PropertyStringList", "CleatBodyLabels", "Deck", "Constituent cleat bodies"
    )
    compound.CleatBodyLabels = [b.Label for b in cleat_bodies]
    return Cleats(body=compound, count=len(cleat_bodies))


def _build_lifelines(
    deck_plate: DeckPlate,
    target_doc: Any,
    added: list[Any],
    *,
    hardware: DeckHardwareParameters,
    superstructure: DeckSuperstructureParameters,
) -> Lifelines:
    """Build lifelines as a Part::Compound of tubes (FR-007, FR-017).

    One tube per side per line, strung between the railing posts at
    ``railing.height_above_deck * height_fraction``. Skipped entirely (empty
    compound) when the railing has zero posts.

    spec 022: when ``sag_depth > 0`` each tube follows a true catenary
    (``_pd_catenary_pipe``); a manifold-or-fallback gate (FR-008) reverts to the
    spec 010 straight ``_pd_circle_pad`` tube on sweep failure. ``sag_depth == 0``
    reproduces the spec 010 straight tube exactly.
    """
    import Part

    ll = hardware.lifelines
    rail = superstructure.railings
    deck_top_z = _resolve_deck_top_z_at(deck_plate, (rail.forward_x + rail.aft_x) / 2.0)

    line_bodies: list[Any] = []
    if ll.line_count > 0 and rail.post_count_per_side > 0:
        # Lateral Y matches the railing posts (sheer outer minus inboard offset).
        deck_shape = deck_plate.body.Shape
        mid_x = (rail.forward_x + rail.aft_x) / 2.0
        verts_at_mid = [v for v in deck_shape.Vertexes if abs(v.X - mid_x) < 1500.0]
        outer_y = max(abs(v.Y) for v in verts_at_mid) if verts_at_mid else deck_shape.BoundBox.YMax
        rail_y = max(0.0, outer_y - rail.inboard_offset_from_sheer)
        radius = ll.tube_diameter / 2.0
        span = rail.aft_x - rail.forward_x

        def _straight_tube(body: Any, name: str, sign: int, line_z: float) -> None:
            datum = _pd_make_datum_yz(body, f"{name}Datum", rail.forward_x, line_z, added)
            _pd_circle_pad(body, datum, name, sign * rail_y, 0.0, radius, span, added)

        for line_idx in range(ll.line_count):
            # Distribute multiple lines evenly below the railing top.
            if ll.line_count == 1:
                frac = ll.height_fraction
            else:
                frac = ll.height_fraction * (line_idx + 1) / ll.line_count
            line_z = deck_top_z + rail.height_above_deck * frac
            for side, sign in (("Port", 1), ("Starboard", -1)):
                name = f"Lifeline{side}{line_idx + 1}"
                body = target_doc.addObject(
                    "PartDesign::Body", f"Deck_Lifeline_{side}_{line_idx + 1}"
                )
                added.append(body)
                target_doc.recompute()
                made = False
                if ll.sag_depth > 0:
                    try:
                        pipe = _pd_catenary_pipe(
                            body,
                            name,
                            sign * rail_y,
                            rail.forward_x,
                            rail.aft_x,
                            line_z,
                            ll.sag_depth,
                            radius,
                            added,
                        )
                        target_doc.recompute()
                        made = pipe is not None and _is_single_valid_solid(body.Shape)
                    except BaseException:
                        made = False
                    if not made:
                        # Discard the failed pipe features, fall back to straight.
                        _discard_body(body, target_doc, added)
                        body = target_doc.addObject(
                            "PartDesign::Body", f"Deck_Lifeline_{side}_{line_idx + 1}"
                        )
                        added.append(body)
                        target_doc.recompute()
                if not made:
                    _straight_tube(body, name, sign, line_z)
                    target_doc.recompute()
                line_bodies.append(body)

    compound = target_doc.addObject("Part::Feature", "Deck_Lifelines")
    compound.Shape = (
        Part.makeCompound([b.Shape for b in line_bodies]) if line_bodies else Part.makeCompound([])
    )
    added.append(compound)
    compound.addProperty("App::PropertyInteger", "LineCount", "Deck", "Lifeline count")
    compound.LineCount = len(line_bodies)
    return Lifelines(body=compound, line_count=len(line_bodies))


# ---------------------------------------------------------------------------
# Spec 016 — DS-variant deckhouse builders (data-model §4.2)
# ---------------------------------------------------------------------------


def _validate_cross_hull_deckhouse(hull: Hull, dh: DeckhouseParameters) -> None:
    """FR-012: the DS deckhouse must fit within the hull before construction.

    HullParameters are in meters; DeckhouseParameters in mm — compare in mm.
    """
    hp = hull.parameters
    loa_mm = hp.loa * _MM_PER_M
    beam_mm = hp.beam_max * _MM_PER_M
    if dh.fwd_offset + dh.length > loa_mm:
        raise DeckParameterError(
            "deckhouse_fwd_offset+length<>hull.loa",
            None,
            f"deckhouse fwd_offset + length ({dh.fwd_offset + dh.length:.0f} mm) "
            f"must not exceed hull LOA ({loa_mm:.0f} mm)",
        )
    if dh.aft_width + 2.0 * dh.wall_inset > beam_mm:
        raise DeckParameterError(
            "deckhouse_aft_width+walls<>hull.beam_max",
            None,
            f"deckhouse aft_width + 2*wall_inset ({dh.aft_width + 2.0 * dh.wall_inset:.0f} mm) "
            f"must not exceed hull beam_max ({beam_mm:.0f} mm)",
        )


def _build_deckhouse(
    hull: Hull,
    deck_plate: DeckPlate,
    dh: DeckhouseParameters,
    target_doc: Any,
    added: list[Any],
) -> Deckhouse:
    """Build the enclosed DS deckhouse as a PartDesign::Body (spec 016 FR-003..005).

    Mirrors :func:`_build_cabin_trunk`: two trapezoidal sketches on XY-parallel
    datums (lower at the sampled deck-plate top, upper at deck top + height)
    are lofted into a single filled solid (Ruled=True). The upper forward edge
    is shifted aft by ``height * tan(front_rake)`` to rake the front wall; the
    aft wall stays vertical and the side taper comes from forward_width <=
    aft_width. The top face of the loft is the flat roof; the result is a
    manifold solid (Solids == 1) by construction (the spec 009 guard).
    """
    import FreeCAD
    import Part

    deck_bb = deck_plate.body.Shape.BoundBox
    fwd_x_mm = deck_bb.XMin + dh.fwd_offset
    aft_x_mm = fwd_x_mm + dh.length
    deck_top_z_mm = _resolve_deck_top_z_at(deck_plate, (fwd_x_mm + aft_x_mm) / 2.0)
    upper_z_mm = deck_top_z_mm + dh.height_above_deck
    front_rake_dx = dh.height_above_deck * math.tan(math.radians(dh.front_rake_angle))
    fw = dh.forward_width / 2.0
    aw = dh.aft_width / 2.0

    body = target_doc.addObject("PartDesign::Body", "Deck_Deckhouse")
    added.append(body)
    target_doc.recompute()

    lower_datum = _pd_make_datum_xy(body, "DeckhouseLowerDatum", deck_top_z_mm, added)
    upper_datum = _pd_make_datum_xy(body, "DeckhouseUpperDatum", upper_z_mm, added)

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
            line_ids.append(sketch.addGeometry(Part.LineSegment(pts[i], pts[j]), False))
        _pd_close_loop_constraints(sketch, line_ids)
        return sketch

    lower_sketch = _trapezoid_sketch("DeckhouseLowerSketch", lower_datum, fwd_x_mm, aft_x_mm)
    upper_sketch = _trapezoid_sketch(
        "DeckhouseUpperSketch", upper_datum, fwd_x_mm + front_rake_dx, aft_x_mm
    )
    target_doc.recompute()

    loft = body.newObject("PartDesign::AdditiveLoft", "DeckhouseLoft")
    added.append(loft)
    loft.Profile = (lower_sketch, [""])
    loft.Sections = [(upper_sketch, [""])]
    loft.Ruled = True
    loft.Closed = False
    target_doc.recompute()

    body.addProperty("App::PropertyLength", "DeckhouseLength", "Deck", "Deckhouse length")
    body.addProperty(
        "App::PropertyLength", "DeckhouseHeight", "Deck", "Deckhouse height above deck"
    )
    body.DeckhouseLength = dh.length
    body.DeckhouseHeight = dh.height_above_deck

    return Deckhouse(
        body=body,
        length=dh.length / _MM_PER_M,
        forward_width=dh.forward_width / _MM_PER_M,
        aft_width=dh.aft_width / _MM_PER_M,
        height=dh.height_above_deck / _MM_PER_M,
        window_count=0,
    )


def _cut_deckhouse_windows(
    deckhouse: Deckhouse,
    win: DsWindowParameters,
    target_doc: Any,
    added: list[Any],
) -> tuple[Deckhouse, list[Any]]:
    """Cut blind wraparound side-window recesses into the deckhouse (spec 016 FR-006).

    Mirrors :func:`_cut_cabin_windows`: ``count_per_side`` rectangular
    ``PartDesign::Pocket`` recesses per side on XZ-parallel datums (normal =
    global Y) at the deckhouse side outer-Y, depth ``recess_depth`` toward the
    centerline. Blind by construction (recess_depth < half-width), so the
    deckhouse stays a single manifold solid. Zero count → no cuts. The raked
    front face itself reads as the windscreen; a separate front-face recess is
    deferred (novel rotated-datum geometry).

    Raises :class:`DeckParameterError` if the recess would reach the far side
    or the opening would not fit the wall.
    """
    import FreeCAD
    import Part

    body = deckhouse.body
    glass_bodies: list[Any] = []
    if win.count_per_side == 0:
        return (deckhouse, glass_bodies)

    bb = body.Shape.BoundBox
    half_width = bb.YLength / 2.0
    if win.recess_depth >= half_width:
        raise DeckParameterError(
            "ds_window_recess_depth<>wall",
            win.recess_depth,
            f"< deckhouse half-width ({half_width:.0f} mm) so the recess stays blind",
        )
    length_avail = bb.XLength
    height_avail = bb.ZLength
    if win.length >= length_avail or win.height >= height_avail:
        raise DeckParameterError(
            "ds_window_opening<>wall",
            None,
            f"window {win.length:.0f}x{win.height:.0f} mm must fit within the "
            f"deckhouse wall ({length_avail:.0f}x{height_avail:.0f} mm)",
        )

    lo, hi = bb.XMin + 0.12 * length_avail, bb.XMax - 0.12 * length_avail
    if win.count_per_side == 1:
        x_stations = [(lo + hi) / 2.0]
    else:
        step = (hi - lo) / (win.count_per_side - 1)
        x_stations = [lo + i * step for i in range(win.count_per_side)]
    cz = (bb.ZMin + bb.ZMax) / 2.0
    outer_y = bb.YMax
    half_l = win.length / 2.0
    half_h = win.height / 2.0

    xz_plane = _pd_get_origin_plane(body, "XZ_Plane")
    count = 0
    for x_mm in x_stations:
        for side, sign in (("Port", 1.0), ("Starboard", -1.0)):
            count += 1
            datum = body.newObject("PartDesign::Plane", f"DeckhouseWindowDatum{side}{count}")
            added.append(datum)
            datum.AttachmentSupport = [(xz_plane, "")]
            datum.MapMode = "FlatFace"
            datum.AttachmentOffset = FreeCAD.Placement(
                FreeCAD.Vector(x_mm, cz, sign * (outer_y + 2.0)),
                FreeCAD.Rotation(),
            )
            sketch = body.newObject(
                "Sketcher::SketchObject", f"DeckhouseWindowSketch{side}{count}"
            )
            added.append(sketch)
            sketch.AttachmentSupport = [(datum, "")]
            sketch.MapMode = "FlatFace"
            pts = [
                FreeCAD.Vector(-half_l, -half_h, 0),
                FreeCAD.Vector(half_l, -half_h, 0),
                FreeCAD.Vector(half_l, half_h, 0),
                FreeCAD.Vector(-half_l, half_h, 0),
            ]
            line_ids: list[int] = []
            for i in range(4):
                j = (i + 1) % 4
                line_ids.append(sketch.addGeometry(Part.LineSegment(pts[i], pts[j]), False))
            _pd_close_loop_constraints(sketch, line_ids)
            pocket = body.newObject(
                "PartDesign::Pocket", f"DeckhouseWindowPocket{side}{count}"
            )
            added.append(pocket)
            pocket.Profile = (sketch, [""])
            pocket.Length = win.recess_depth + 2.0
            pocket.Reversed = sign > 0.0  # cut toward the centerline
            pocket.Midplane = False

            if win.glass_panes:
                glass_bodies.append(
                    _build_window_glass(
                        target_doc,
                        f"Deck_DeckhouseWindowGlass{side}{count}",
                        x_mm,
                        cz,
                        sign * (outer_y - win.recess_depth * 0.5),
                        half_l,
                        half_h,
                        win.glass_thickness,
                        added,
                    )
                )

    return (
        Deckhouse(
            body=body,
            length=deckhouse.length,
            forward_width=deckhouse.forward_width,
            aft_width=deckhouse.aft_width,
            height=deckhouse.height,
            window_count=count,
        ),
        glass_bodies,
    )


def _detail_deckhouse(
    deckhouse: Deckhouse,
    dh: DeckhouseParameters,
    target_doc: Any,
    added: list[Any],
) -> tuple[Deckhouse, list[Any]]:
    """spec 023 — finish the DS deckhouse: front-window recess on the raked
    screen (rotated datum), side-window mullion bosses, and a helm-door recess.

    All cuts/bosses act on the deckhouse body only (FR-006). The deckhouse stays
    a single valid solid (FR-005). The front recess carries a manifold-or-skip
    gate (FR-001) — if its rotated-datum cut would not leave a single valid
    solid, it is rolled back deterministically and the rest still builds. Returns
    the updated wrapper + any new glass-pane bodies.
    """
    import FreeCAD
    import Part

    win = dh.windows
    body = deckhouse.body
    glass_bodies: list[Any] = []
    bb = body.Shape.BoundBox
    front_x = bb.XMin
    deck_top_z = bb.ZMin
    upper_z = bb.ZMax
    rake_dx = (upper_z - deck_top_z) * math.tan(math.radians(dh.front_rake_angle))
    face_cx = front_x + rake_dx / 2.0
    face_cz = (deck_top_z + upper_z) / 2.0
    rot = FreeCAD.Rotation(FreeCAD.Vector(0, 1, 0), dh.front_rake_angle)

    has_front = False
    front_skipped = False
    if win.front_window:
        prev_tip = body.Tip
        refinement: list[Any] = []
        try:
            datum = body.newObject("PartDesign::Plane", "DeckhouseFrontWinDatum")
            added.append(datum)
            refinement.append(datum)
            datum.AttachmentSupport = [(_pd_get_origin_plane(body, "YZ_Plane"), "")]
            datum.MapMode = "FlatFace"
            datum.AttachmentOffset = FreeCAD.Placement(
                FreeCAD.Vector(0.0, face_cz, face_cx), rot
            )
            sketch = body.newObject("Sketcher::SketchObject", "DeckhouseFrontWinSketch")
            added.append(sketch)
            refinement.append(sketch)
            sketch.AttachmentSupport = [(datum, "")]
            sketch.MapMode = "FlatFace"
            hl = win.front_length / 2.0
            hh = win.front_height / 2.0
            pts = [
                FreeCAD.Vector(-hl, -hh, 0),
                FreeCAD.Vector(hl, -hh, 0),
                FreeCAD.Vector(hl, hh, 0),
                FreeCAD.Vector(-hl, hh, 0),
            ]
            ids = [
                sketch.addGeometry(Part.LineSegment(pts[i], pts[(i + 1) % 4]), False)
                for i in range(4)
            ]
            _pd_close_loop_constraints(sketch, ids)
            pocket = body.newObject("PartDesign::Pocket", "DeckhouseFrontWinPocket")
            added.append(pocket)
            refinement.append(pocket)
            pocket.Profile = (sketch, [""])
            pocket.Length = win.recess_depth + 3.0
            pocket.Reversed = False
            pocket.Midplane = False
            target_doc.recompute()
            if not _is_single_valid_solid(body.Shape):
                raise DeckConstructionError("front-window recess non-manifold")
            has_front = True
        except BaseException:
            # Deterministic skip: roll back the front recess, keep the rest.
            for obj in refinement:
                added[:] = [a for a in added if getattr(a, "Name", None) != obj.Name]
                with contextlib.suppress(BaseException):
                    target_doc.removeObject(obj.Name)
            with contextlib.suppress(BaseException):
                body.Tip = prev_tip
            target_doc.recompute()
            front_skipped = True

        if has_front and win.glass_panes:
            # Thin glass pane on the raked face, just proud of the recess mouth.
            glass = target_doc.addObject("PartDesign::Body", "Deck_DeckhouseWindowGlassFront")
            added.append(glass)
            target_doc.recompute()
            g_datum = glass.newObject("PartDesign::Plane", "FrontGlassDatum")
            added.append(g_datum)
            g_datum.AttachmentSupport = [(_pd_get_origin_plane(glass, "YZ_Plane"), "")]
            g_datum.MapMode = "FlatFace"
            g_datum.AttachmentOffset = FreeCAD.Placement(
                FreeCAD.Vector(0.0, face_cz, face_cx - win.glass_thickness), rot
            )
            g_sketch = glass.newObject("Sketcher::SketchObject", "FrontGlassSketch")
            added.append(g_sketch)
            g_sketch.AttachmentSupport = [(g_datum, "")]
            g_sketch.MapMode = "FlatFace"
            hl = win.front_length / 2.0
            hh = win.front_height / 2.0
            gpts = [
                FreeCAD.Vector(-hl, -hh, 0),
                FreeCAD.Vector(hl, -hh, 0),
                FreeCAD.Vector(hl, hh, 0),
                FreeCAD.Vector(-hl, hh, 0),
            ]
            gids = [
                g_sketch.addGeometry(Part.LineSegment(gpts[i], gpts[(i + 1) % 4]), False)
                for i in range(4)
            ]
            _pd_close_loop_constraints(g_sketch, gids)
            g_pad = glass.newObject("PartDesign::Pad", "FrontGlassPad")
            added.append(g_pad)
            g_pad.Profile = (g_sketch, [""])
            g_pad.Length = win.glass_thickness
            g_pad.Midplane = False
            target_doc.recompute()
            glass_bodies.append(glass)

    # The deckhouse is tapered, so the side surface Y varies with X. A boss/cut
    # placed at bb.YMax would float outside the wall at forward stations → a
    # disconnected solid. Use the actual tapered half-width at each X.
    fw_half = dh.forward_width / 2.0
    aw_half = dh.aft_width / 2.0
    x_span = bb.XMax - bb.XMin

    def _wall_y(x_mm: float) -> float:
        t = (x_mm - bb.XMin) / x_span if x_span > 0 else 0.0
        return fw_half + (aw_half - fw_half) * t

    # Mullions: thin vertical divider bars across each side-window opening. Built
    # as SEPARATE bodies sitting in the recess (like the spec 019 glass panes) so
    # they never have to fuse into the recessed wall — robust, and they resolve to
    # the deckhouse superstructure role by their "Deck_Deckhouse..." label.
    mullion_count = 0
    mullion_bodies: list[Any] = []
    if win.mullions_per_window > 0 and win.count_per_side > 0:
        length_avail = bb.XLength
        lo, hi = bb.XMin + 0.12 * length_avail, bb.XMax - 0.12 * length_avail
        if win.count_per_side == 1:
            x_stations = [(lo + hi) / 2.0]
        else:
            step = (hi - lo) / (win.count_per_side - 1)
            x_stations = [lo + i * step for i in range(win.count_per_side)]
        cz = (bb.ZMin + bb.ZMax) / 2.0
        half_h = win.height / 2.0
        hw = win.mullion_width / 2.0
        for x_mm in x_stations:
            for m in range(win.mullions_per_window):
                frac = (m + 1) / (win.mullions_per_window + 1)
                bx = x_mm - win.length / 2.0 + frac * win.length
                wy = _wall_y(bx)
                for side, sign in (("Port", 1.0), ("Starboard", -1.0)):
                    mullion_count += 1
                    mbody = target_doc.addObject(
                        "PartDesign::Body", f"Deck_DeckhouseMullion{side}{mullion_count}"
                    )
                    added.append(mbody)
                    mullion_bodies.append(mbody)
                    target_doc.recompute()
                    # Bar fills the recess depth + a little proud, at the window
                    # centre. Datum at the recess floor, padded outward.
                    floor_y = sign * (wy - win.recess_depth)
                    datum = _pd_make_datum_xz(
                        mbody, f"Mullion{side}{mullion_count}Datum", bx, floor_y, cz, added
                    )
                    sk = mbody.newObject(
                        "Sketcher::SketchObject", f"Mullion{side}{mullion_count}Sketch"
                    )
                    added.append(sk)
                    sk.AttachmentSupport = [(datum, "")]
                    sk.MapMode = "FlatFace"
                    mpts = [
                        FreeCAD.Vector(bx - hw, cz - half_h, 0),
                        FreeCAD.Vector(bx + hw, cz - half_h, 0),
                        FreeCAD.Vector(bx + hw, cz + half_h, 0),
                        FreeCAD.Vector(bx - hw, cz + half_h, 0),
                    ]
                    mids = [
                        sk.addGeometry(Part.LineSegment(mpts[i], mpts[(i + 1) % 4]), False)
                        for i in range(4)
                    ]
                    _pd_close_loop_constraints(sk, mids)
                    pad = mbody.newObject("PartDesign::Pad", f"Mullion{side}{mullion_count}Pad")
                    added.append(pad)
                    pad.Profile = (sk, [""])
                    pad.Length = win.recess_depth + 4.0
                    pad.Midplane = False
                    pad.Reversed = sign < 0.0
                    target_doc.recompute()
        glass_bodies.extend(mullion_bodies)

    # Helm door: a tall blind door-shaped recess in the helm-side wall, placed in
    # the widest clear X-gap between side windows so it never overlaps a window
    # recess (two intersecting pockets would go non-manifold). Manifold-or-skip.
    has_helm = False
    if win.helm_door:
        # Reconstruct the side-window X footprints (same stations as the cut).
        length_avail = bb.XLength
        lo, hi = bb.XMin + 0.12 * length_avail, bb.XMax - 0.12 * length_avail
        if win.count_per_side <= 0:
            win_centers: list[float] = []
        elif win.count_per_side == 1:
            win_centers = [(lo + hi) / 2.0]
        else:
            step = (hi - lo) / (win.count_per_side - 1)
            win_centers = [lo + i * step for i in range(win.count_per_side)]
        half_wl = win.length / 2.0
        # Occupied X-intervals (windows) + the deckhouse end margins.
        occupied = sorted((c - half_wl, c + half_wl) for c in win_centers)
        margin = 0.06 * length_avail
        free_lo = bb.XMin + margin
        free_hi = bb.XMax - margin
        # Build the free gaps between occupied intervals.
        gaps: list[tuple[float, float]] = []
        cursor = free_lo
        for a, b in occupied:
            if a - cursor > 0:
                gaps.append((cursor, min(a, free_hi)))
            cursor = max(cursor, b)
        if cursor < free_hi:
            gaps.append((cursor, free_hi))
        widest = max(gaps, key=lambda g: g[1] - g[0], default=(free_lo, free_hi))
        door_x = (widest[0] + widest[1]) / 2.0
        gap_fits = (widest[1] - widest[0]) >= win.helm_door_length

        if gap_fits:
            sign = 1.0 if win.helm_door_side == "Port" else -1.0
            door_cz = bb.ZMin + win.helm_door_height / 2.0 + 30.0
            wy = _wall_y(door_x)
            datum = _pd_make_datum_xz(
                body, "DeckhouseHelmDoorDatum", door_x, sign * (wy + 2.0), door_cz, added
            )
            sk = body.newObject("Sketcher::SketchObject", "DeckhouseHelmDoorSketch")
            added.append(sk)
            sk.AttachmentSupport = [(datum, "")]
            sk.MapMode = "FlatFace"
            hl = win.helm_door_length / 2.0
            hh = win.helm_door_height / 2.0
            dpts = [
                FreeCAD.Vector(door_x - hl, door_cz - hh, 0),
                FreeCAD.Vector(door_x + hl, door_cz - hh, 0),
                FreeCAD.Vector(door_x + hl, door_cz + hh, 0),
                FreeCAD.Vector(door_x - hl, door_cz + hh, 0),
            ]
            dids = [
                sk.addGeometry(Part.LineSegment(dpts[i], dpts[(i + 1) % 4]), False)
                for i in range(4)
            ]
            _pd_close_loop_constraints(sk, dids)
            pocket = body.newObject("PartDesign::Pocket", "DeckhouseHelmDoorPocket")
            added.append(pocket)
            pocket.Profile = (sk, [""])
            pocket.Length = win.recess_depth + 2.0
            pocket.Reversed = sign > 0.0
            pocket.Midplane = False
            target_doc.recompute()
            if not _is_single_valid_solid(body.Shape):
                raise DeckConstructionError("helm-door recess non-manifold")
            has_helm = True

    return (
        Deckhouse(
            body=body,
            length=deckhouse.length,
            forward_width=deckhouse.forward_width,
            aft_width=deckhouse.aft_width,
            height=deckhouse.height,
            window_count=deckhouse.window_count,
            has_front_window=has_front,
            front_window_skipped=front_skipped,
            mullion_count=mullion_count,
            has_helm_door=has_helm,
        ),
        glass_bodies,
    )


# ---------------------------------------------------------------------------
# Public builder (FR-001 + contracts/python-api.md)
# ---------------------------------------------------------------------------


def build_deck(
    hull: Hull,
    parameters: DeckParameters | None = None,
    *,
    superstructure_variant: Literal["standard", "ds"] = "standard",
    parameters_superstructure: DeckSuperstructureParameters | None = None,
    parameters_deckhouse: DeckhouseParameters | None = None,
    parameters_hardware: DeckHardwareParameters | None = None,
    parameters_glazing: DeckGlazingParameters | None = None,
    document: Any = None,
    name: str = "Deck",
    apply_render_attributes: bool = True,
) -> Deck:
    """Build the parametric Storebro deck (superstructure + hardware) on a hull.

    Args:
        hull: A Hull returned by ``storebro.hull.build_hull``. Must have a
            non-empty ``.body.Shape``.
        parameters: Legacy 14-field deck dimensional parameters. ``None`` →
            use :class:`DeckParameters` defaults (Storebro RC34 1972
            estimate-grade values). Mutually exclusive with
            ``parameters_superstructure``.
        superstructure_variant: Which topsides silhouette to build —
            ``"standard"`` (spec 008 open flybridge: cabin trunk + windshield +
            hardtop + pillars, the default) or ``"ds"`` (spec 016 enclosed deck
            saloon: a single :class:`Deckhouse` solid). The deck plate,
            railings, and all hardware are shared by both variants.
        parameters_superstructure: Spec 008 per-component composite. When
            non-None, takes precedence over ``parameters`` for the
            superstructure shape; the deck plate still derives from the
            legacy fields. Mutually exclusive with ``parameters``. Forbidden
            together with ``superstructure_variant="ds"`` (the DS variant has
            no open-flybridge superstructure).
        parameters_deckhouse: Spec 016 DS deckhouse composite. ``None`` → use
            :class:`DeckhouseParameters` defaults. Only consulted when
            ``superstructure_variant="ds"``.
        parameters_hardware: Spec 010 deck-hardware composite (rubrail, bow
            pulpit, lifelines, anchor locker, cleats). ``None`` → use
            :class:`DeckHardwareParameters` defaults, so existing callers get
            the hardware automatically. Independent of the ``parameters`` ⊕
            ``parameters_superstructure`` mutual-exclusivity rule.
        document: Target FreeCAD document. ``None`` → use ``hull.document``.
            Must equal ``hull.document`` if non-None — cross-document deck
            building is rejected with :class:`DeckParameterError`.
        name: Base label for the Deck aggregate. Defaults to ``"Deck"``. The
            six superstructure sub-Bodies are labeled ``Deck_DeckPlate``,
            ``Deck_CabinTrunk``, ``Deck_Windshield``, ``Deck_Hardtop``,
            ``Deck_HardtopPillars``, ``Deck_Railings``; the five hardware items
            are ``Deck_Rubrail``, ``Deck_BowPulpit``, ``Deck_Lifelines``,
            ``Deck_AnchorLocker``, ``Deck_Cleats``. FreeCAD auto-numbering
            applies on collision.

    Returns:
        :class:`Deck` aggregate holding all sub-Body wrappers + inputs.

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
        >>> # DS enclosed deck saloon (styrhytt) — one deckhouse, no flybridge:
        >>> # ds = build_deck(build_hull(), superstructure_variant="ds")  # doctest: +SKIP
        >>> # ds.deckhouse is not None and ds.cabin_trunk is None  # doctest: +SKIP
        >>> # True
    """
    # spec 016 — variant selector guards (before ANY FreeCAD call, so they are
    # unit-testable without a FreeCAD runtime and fail fast on contradictions).
    if superstructure_variant not in ("standard", "ds"):
        raise DeckParameterError(
            "superstructure_variant",
            None,
            "one of {'standard', 'ds'}",
        )
    if superstructure_variant == "ds" and parameters_superstructure is not None:
        raise DeckParameterError(
            "superstructure_variant<>parameters_superstructure",
            None,
            "the 'ds' variant has no open-flybridge superstructure — do not pass "
            "parameters_superstructure (use parameters_deckhouse instead)",
        )

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

    # spec 016 — resolve + validate the DS deckhouse composite (DS variant only).
    dh = parameters_deckhouse if parameters_deckhouse is not None else DeckhouseParameters()
    if superstructure_variant == "ds":
        _validate_cross_hull_deckhouse(hull, dh)

    # Resolve the new sub-dataclass composite. If the caller passed an
    # explicit `parameters_superstructure`, use it; otherwise translate
    # the legacy form via the shim.
    sp = (
        parameters_superstructure
        if parameters_superstructure is not None
        else resolved_params.to_superstructure_parameters()
    )

    # Resolve the spec 010 hardware composite (defaults → hardware on by default).
    hw = parameters_hardware if parameters_hardware is not None else DeckHardwareParameters()
    # spec 011 — resolve glazing (cabin windows + framed windshield, on by default).
    glz = parameters_glazing if parameters_glazing is not None else DeckGlazingParameters()

    target_doc = _resolve_document(hull, document)
    label = name if name is not None else "Deck"

    started = time.perf_counter()
    added: list[Any] = []
    # spec 016 — the four open-flybridge bodies + cabin windows exist only in
    # the standard variant; the deckhouse exists only in the ds variant.
    cabin_trunk: CabinTrunk | None = None
    windshield: Windshield | None = None
    hardtop: Hardtop | None = None
    hardtop_pillars: HardtopPillars | None = None
    cabin_windows: CabinWindows | None = None
    deckhouse: Deckhouse | None = None
    _window_glass: list[Any] = []  # spec 019 translucent panes (cabin + DS windows)
    try:
        deck_plate = _build_deck_plate(hull, resolved_params, target_doc, added)
        if superstructure_variant == "ds":
            # Enclosed DS deck saloon: one filled deckhouse solid replaces the
            # cabin trunk + windshield + hardtop + pillars.
            deckhouse = _build_deckhouse(hull, deck_plate, dh, target_doc, added)
            deckhouse, _deckhouse_glass = _cut_deckhouse_windows(
                deckhouse, dh.windows, target_doc, added
            )
            _window_glass.extend(_deckhouse_glass)
            # spec 023 — front-window recess, side mullions, helm-door recess.
            deckhouse, _detail_glass = _detail_deckhouse(deckhouse, dh, target_doc, added)
            _window_glass.extend(_detail_glass)
            railings = _build_railings(
                hull, resolved_params, deck_plate, target_doc, added, superstructure=sp
            )
            target_doc.recompute()

            # The cabin-trunk-shaped hardware checks treat the deckhouse as the
            # obstruction the anchor locker must clear; adapt it via a CabinTrunk
            # wrapper (both helpers only read `.body.Shape.BoundBox`).
            obstruction = CabinTrunk(
                body=deckhouse.body,
                length=deckhouse.length,
                width=(deckhouse.forward_width + deckhouse.aft_width) / 2.0,
                height=deckhouse.height,
                corner_radius=0.0,
            )
            # The long DS deckhouse overruns the standard anchor-locker default
            # (tuned for the shorter cabin trunk); when the caller did not
            # override hardware, reposition the locker onto the foredeck forward
            # of the deckhouse so the default DS build does not self-collide.
            if parameters_hardware is None:
                deck_xmax = deck_plate.body.Shape.BoundBox.XMax
                house_xmax = deckhouse.body.Shape.BoundBox.XMax
                foredeck_mid = (house_xmax + deck_xmax) / 2.0
                hw = replace(
                    hw, anchor_locker=replace(hw.anchor_locker, center_x=foredeck_mid)
                )

            _validate_cross_deck_hardware(deck_plate, obstruction, hw)
            rubrail = _build_rubrail(hull, deck_plate, target_doc, added, hardware=hw)
            bow_pulpit = _build_bow_pulpit(hull, deck_plate, target_doc, added, hardware=hw)
            anchor_locker = _build_anchor_locker(
                deck_plate, obstruction, target_doc, added, hardware=hw
            )
            cleats = _build_cleats(hull, deck_plate, target_doc, added, hardware=hw)
            lifelines = _build_lifelines(
                deck_plate, target_doc, added, hardware=hw, superstructure=sp
            )
            target_doc.recompute()
            _assert_solid_manifold(deckhouse.body, "deckhouse")
            target_doc.recompute()
        else:
            cabin_trunk = _build_cabin_trunk(
                hull, resolved_params, deck_plate, target_doc, added, superstructure=sp
            )
            windshield = _build_windshield(
                hull, resolved_params, cabin_trunk, target_doc, added, superstructure=sp, glazing=glz
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

            # Spec 010 — deck hardware. Cross-deck collision checks run now that
            # the deck plate + cabin trunk geometry exists; they raise
            # DeckParameterError (caught + rolled back below). Build order per
            # plan §Build Sequence; lifelines LAST (they need the railing).
            _validate_cross_deck_hardware(deck_plate, cabin_trunk, hw)
            rubrail = _build_rubrail(hull, deck_plate, target_doc, added, hardware=hw)
            bow_pulpit = _build_bow_pulpit(hull, deck_plate, target_doc, added, hardware=hw)
            anchor_locker = _build_anchor_locker(
                deck_plate, cabin_trunk, target_doc, added, hardware=hw
            )
            cleats = _build_cleats(hull, deck_plate, target_doc, added, hardware=hw)
            lifelines = _build_lifelines(
                deck_plate, target_doc, added, hardware=hw, superstructure=sp
            )

            # Spec 011 — cabin-trunk side windows (cut last, after every consumer
            # of the trunk geometry has read it), then the manifold guards (FR-008).
            cabin_windows, _cabin_glass = _cut_cabin_windows(
                cabin_trunk, glz, target_doc, added
            )
            _window_glass.extend(_cabin_glass)
            target_doc.recompute()
            _assert_solid_manifold(cabin_trunk.body, "cabin trunk")
            if glz.windshield.enabled:
                _assert_solid_manifold(windshield.body, "windshield frame")
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

    # spec 015 — cosmetic render attributes on every top-level deck body
    # (superstructure white, rubrail teak, hardware chrome, glass translucent).
    from storebro.render import apply_render_attributes as _apply_render_attributes

    _render_targets: list[Any] = [
        deck_plate.body,
        railings.body,
        rubrail.body,
        bow_pulpit.body,
        lifelines.body,
        anchor_locker.body,
        cleats.body,
    ]
    # spec 022 — the chrome rubrail insert + teak locker lid are separate bodies
    # so they resolve to their own render roles (metal / trim).
    if rubrail.insert_body is not None:
        _render_targets.append(rubrail.insert_body)
    if anchor_locker.lid_body is not None:
        _render_targets.append(anchor_locker.lid_body)
    if deckhouse is not None:
        # spec 016 — the deckhouse colours white via the "Deck_Deckhouse"
        # render role (see render._ROLE_RULES).
        _render_targets.append(deckhouse.body)
    if cabin_trunk is not None:
        _render_targets.append(cabin_trunk.body)
    if windshield is not None:
        _render_targets.append(windshield.body)
        if windshield.glass_pane is not None:
            _render_targets.append(windshield.glass_pane.body)
    if hardtop is not None:
        _render_targets.append(hardtop.body)
    if hardtop_pillars is not None:
        _render_targets.append(hardtop_pillars.body)
    _render_targets.extend(_window_glass)  # spec 019 translucent window panes
    _apply_render_attributes(_render_targets, enabled=apply_render_attributes)

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
        rubrail=rubrail,
        bow_pulpit=bow_pulpit,
        lifelines=lifelines,
        anchor_locker=anchor_locker,
        cleats=cleats,
        parameters_hardware=hw,
        cabin_windows=cabin_windows,
        parameters_glazing=glz,
        superstructure_variant=superstructure_variant,
        deckhouse=deckhouse,
    )
