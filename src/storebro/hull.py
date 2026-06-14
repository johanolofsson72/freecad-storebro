"""Parametric Storebro hull module.

Public surface:
    build_hull        — function. Build a parametric Storebro hull Body.
    HullParameters    — frozen dataclass. Hull dimensional inputs.
    Hull              — dataclass. Builder return type wrapping the FreeCAD Body.
    HullParameterError — exception. Pre-FreeCAD parameter validation failure.
    HullConstructionError — exception. FreeCAD-side construction failure.

See specs/001-hull-module/ for the full specification.
"""

from __future__ import annotations

import contextlib
import enum
import math
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Literal

if TYPE_CHECKING:
    pass

__all__ = [
    "Hull",
    "HullConstructionError",
    "HullGlazingParameters",
    "HullParameterError",
    "HullParameters",
    "Porthole",
    "PortholeParameters",
    "StationTopology",
    "build_hull",
]


# ---------------------------------------------------------------------------
# Module-level constants (spec 009 T001 — Constitution I: no magic numbers)
# ---------------------------------------------------------------------------

# spec 018: smoothness comes from station density under Ruled=True (exact,
# manifold), not from Ruled=False B-spline interpolation. A FreeCAD spike
# confirmed Ruled=False overshoots the beam >=12% for this profile while
# Ruled=True is exact (0%), so the default is densified (9 -> 31) and the cap
# raised (21 -> 81); facets then drop below visual resolution.
DEFAULT_STATION_COUNT = 31
DEFAULT_BILGE_RADIUS_M = 0.10
STATION_COUNT_MIN = 3
STATION_COUNT_MAX = 81
B_SPLINE_STATION_COUNT_THRESHOLD = 8
# spec 031: hard-chine hull variant. The "hard_chine" variant moves the v1
# chine vertex of each non-stem PENTAGON_LEGACY station outboard toward the
# topside half-beam (flatter bottom, sharper chine) and up (shallower chine).
# Named so the variant carries no magic numbers (constitution I). "standard"
# keeps the v1 vertex at today's position (chine_z_factor = 0.6).
_HARD_CHINE_BEAM_BLEND = 0.5
"""Fraction the chine half-beam moves from half_beam_bottom toward half_beam_top."""
_HARD_CHINE_CHINE_Z_FACTOR = 0.35
"""Chine-depth factor for hard-chine stations (vs the 0.6 standard default)."""
# spec 032: topside flare — the waterline turn is pulled inboard of the deck edge
# (which stays at max beam) as a FRACTION of the local half-beam, more strongly
# toward the bow (spray-deflecting flare). Proportional so it vanishes at the thin
# stem and never inverts a tapering section. fraction(s) = base + slope * s.
_FLARE_FRACTION_BASE = 0.06
_FLARE_FRACTION_SLOPE = 0.10
# spec 032: rounded-bilge default for the reference displacement hull. The chine
# corner is replaced by a 3-facet rounded bilge (7-vertex section) on every station.
# hull_variant="hard_chine" uses 0.0 (sharp 5-vertex chine), keeping that variant.
_BILGE_ROUND_STANDARD = 0.35
OVERSHOOT_TOLERANCE_MM = 1.0
REFERENCE_FIDELITY_TOLERANCE_PCT = 1.0
HULL_BUILD_TIME_BUDGET_SECONDS = 10.0
# spec 009 implementation drift (documented in closure note): the
# "zero forefoot" stem is implemented as a thin 5 mm half-width pentagon
# rather than a true degenerate vertex. FreeCAD's AdditiveLoft with
# Ruled=False produces a wildly-overshooting "blend to point" surface
# when interpolating from a 5-vertex pentagon to a 1-vertex section, even
# at station_count = 21. The thin pentagon is below visual resolution at
# boat scale (10 mm stem face vs spec 007's 80 mm) and preserves the
# B-spline convergence the spec asks for.
THIN_STEM_HALF_WIDTH_M = 0.005


class StationTopology(enum.Enum):
    """Cross-section topology of a single hull station sketch (spec 009 T005).

    Branching strategy:
        - PENTAGON_THIN_STEM: stem station when ``station_count >= 8``;
          a 5-vertex pentagon with half-beam = THIN_STEM_HALF_WIDTH_M
          (5 mm half-width). Visually "zero forefoot" at boat scale, but
          topology stays consistent across stations so PartDesign's
          AdditiveLoft can interpolate without overshoot.
        - PENTAGON_LEGACY: the spec 007 5-vertex pentagon with straight
          bottom-to-topside diagonal. Used by every non-stem station when
          ``bilge_radius == 0``, and by the stem when ``station_count < 8``
          (preserves the 80 mm forefoot for known-working AdditiveLoft
          vertex mapping at low station counts).
        - PENTAGON_WITH_ARC: 5-element cross-section where the
          bottom-to-topside diagonal is replaced by a quarter-circle bilge
          arc tangent to the bottom edge and to the topside edge. Used by
          every non-stem station when ``bilge_radius > 0``.

    Spec drift documented in spec 009 closure note:
        - The data-model.md document references a fourth topology
          ``SHARP_CHINE_QUADRILATERAL`` (4 vertices); this is NOT
          implemented in v1.0.3 because a 4-vertex non-stem station would
          not be AdditiveLoft-compatible with the 5-vertex stem. Legacy
          sharp-chine behavior is preserved instead via PENTAGON_LEGACY
          (5-vertex pentagon with straight diagonal — geometrically a chine).
        - The spec.md ``DEGENERATE_VERTEX`` topology (zero half-width
          stem) was discovered to overshoot wildly under Ruled=False loft
          interpolation. The implementation substitutes PENTAGON_THIN_STEM,
          preserving the spec's visual intent.

    Example:
        >>> StationTopology.PENTAGON_THIN_STEM.value
        'pentagon_thin_stem'
        >>> StationTopology.PENTAGON_WITH_ARC.name
        'PENTAGON_WITH_ARC'
    """

    PENTAGON_THIN_STEM = "pentagon_thin_stem"
    PENTAGON_LEGACY = "pentagon_legacy"
    PENTAGON_WITH_ARC = "pentagon_with_arc"


# ---------------------------------------------------------------------------
# Exception classes (FR-015 + data-model §3/§4)
# ---------------------------------------------------------------------------


class HullParameterError(ValueError):
    """Raised before any FreeCAD call when a hull parameter is invalid.

    Carries structured attributes so callers can introspect the failure
    without parsing the message string.

    Attributes:
        parameter_name: Name of the offending field. For cross-field
            violations, a composite key like ``"loa<>beam_max"``.
        parameter_value: The supplied value, or ``None`` for cross-field
            violations where no single value is "the" offender.
        valid_range: Human-readable range, e.g. ``"> 0"`` or ``"[0, 30]"``.

    Example:
        >>> err = HullParameterError("loa", -5.0, "> 0")
        >>> err.parameter_name
        'loa'
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
            message = (
                f"HullParameterError: invalid parameter combination — "
                f"{parameter_name} ({valid_range})"
            )
        else:
            message = (
                f"HullParameterError: {parameter_name} = {parameter_value!r} "
                f"is outside the valid range {valid_range}"
            )
        super().__init__(message)


class HullConstructionError(RuntimeError):
    """Raised when FreeCAD fails to construct the hull, or when the running
    FreeCAD version is outside the supported range.

    Attributes:
        parameters: The :class:`HullParameters` that triggered the failure,
            or ``None`` if the failure was a version-check failure.
        underlying: The FreeCAD-side exception, or ``None``.
        detected_version: ``(major, minor)`` of the running FreeCAD when the
            failure was a version-check failure, else ``None``.
        supported_range: Human-readable supported range when this is a
            version-check failure, else ``None``.

    Example:
        >>> err = HullConstructionError("unsupported FreeCAD version: 0.20",
        ...                             detected_version=(0, 20),
        ...                             supported_range=">=1.1,<2.0")
        >>> err.detected_version
        (0, 20)
        >>> isinstance(err, RuntimeError)
        True
    """

    def __init__(
        self,
        message: str,
        *,
        parameters: HullParameters | None = None,
        underlying: BaseException | None = None,
        detected_version: tuple[int, int] | None = None,
        supported_range: str | None = None,
    ) -> None:
        self.parameters = parameters
        self.underlying = underlying
        self.detected_version = detected_version
        self.supported_range = supported_range
        super().__init__(f"HullConstructionError: {message}")


# ---------------------------------------------------------------------------
# Parameter dataclass (FR-002, FR-004, FR-008 + data-model §1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HullParameters:
    """Named hull dimensional inputs for :func:`build_hull`.

    All lengths in meters, all angles in degrees. Defaults match the historical
    Storebro Royal Cruiser 34 (1972 model year) within ±1% on the citation-grade
    pair (LOA, beam); the remaining six fields are estimate-grade — see
    ``specs/001-hull-module/research.md`` §R1 for sourcing details.

    Validated at construction. A successfully-constructed instance is
    guaranteed to satisfy every per-field and cross-field constraint
    documented on the field.

    Example:
        >>> p = HullParameters()
        >>> p.loa, p.beam_max
        (10.35, 3.2)
        >>> custom = HullParameters(loa=11.0, beam_max=3.5)
        >>> custom.aspect_ratio
        3.142857142857143
    """

    loa: float = 10.35
    beam_max: float = 3.20
    draft: float = 1.10
    freeboard: float = 0.95
    deadrise_amidships: float = 8.0
    sheer_height_aft: float = 0.95
    sheer_height_fwd: float = 1.16
    transom_angle: float = 5.0
    stem_rake_angle: float = 6.0
    # spec 009 additive fields (v1.0.3): denser station set + parametric
    # bilge arc. Both default to the v1.0.3 reference-fidelity values.
    station_count: int = DEFAULT_STATION_COUNT
    bilge_radius: float = DEFAULT_BILGE_RADIUS_M

    REFERENCE_STOREBRO_ROYAL_CRUISER_34_1972: ClassVar[dict[str, float]] = {
        "loa": 10.35,
        "beam_max": 3.20,
        "draft": 1.10,
        "freeboard": 0.95,
        "deadrise_amidships": 8.0,
        "sheer_height_aft": 0.95,
        "sheer_height_fwd": 1.16,
        "transom_angle": 5.0,
        "stem_rake_angle": 6.0,
    }

    def __post_init__(self) -> None:
        _validate_hull_parameters(self)

    @property
    def aspect_ratio(self) -> float:
        """LOA / beam_max — informational only, does not affect geometry."""
        return self.loa / self.beam_max

    @property
    def is_planing_hull(self) -> bool:
        """True iff aspect ratio exceeds the rough planing-hull threshold."""
        return self.aspect_ratio > 3.2

    # spec 009 computed properties (T003).

    @property
    def uses_b_spline_loft(self) -> bool:
        """Always ``False`` — the B-spline loft is permanently infeasible here.

        Spec 009 originally wired this flag to ``station_count >= 8`` and used
        it to switch the AdditiveLoft to ``Ruled=False``. A spec 018 FreeCAD
        spike re-confirmed with hard numbers that ``Ruled=False`` overshoots
        the beam by 12-141% for the Storebro profile across uniform, Chebyshev,
        stem-clustered, and amidships-clustered station spacing (vs the ±1%
        fidelity bar), while ``Ruled=True`` is exact (0%). A raw
        ``Part.BSplineSurface`` skin could force smoothness but is not a
        PartDesign-editable feature (constitution III). Smoothness is therefore
        delivered by station *density* under ``Ruled=True`` (spec 018), not by
        interpolation. The flag is retained as a forward-compat hook but always
        reports ``False``.
        """
        _ = self.station_count
        return False

    @property
    def uses_zero_forefoot_stem(self) -> bool:
        """True iff the stem uses the thin (5 mm half-width) pentagon topology.

        At ``station_count >= 8`` the stem station uses
        ``StationTopology.PENTAGON_THIN_STEM`` — a thin 5-vertex stem section for
        AdditiveLoft compatibility. (The name is historical: spec 033 deepened the
        stem forefoot to 0.30 m for a fuller bow, so it is no longer a literal
        zero-forefoot stem — only the section *width* is thin.) Below the threshold
        the stem retains the spec 007 80 mm-forefoot pentagon (``PENTAGON_LEGACY``).
        """
        return self.station_count >= B_SPLINE_STATION_COUNT_THRESHOLD

    @property
    def uses_bilge_arc(self) -> bool:
        """Always ``False`` — the quarter-circle bilge arc re-defers to the
        sharp chine.

        Spec 009 wired this flag to ``bilge_radius > 0`` and used it to replace
        the chine corner with a quarter-circle arc via ``Sketcher.fillet()``.
        A spec 018 spike re-tested it at the new dense default: the filleted
        B-rep is a valid single solid (``Solids == 1``, ``isValid()``), but its
        tessellated mesh is **not watertight**, so STL export fails
        (``ExportWriteError: mesh is not watertight``) — the spec 009 failure,
        re-confirmed at n=9 and n=21. Per the spec 018 clarification the arc is
        kept only if STL stays manifold, so it falls back to the sharp-chine
        pentagon. The flag is retained as a forward-compat hook but reports
        ``False``; ``bilge_radius`` and the ``PENTAGON_WITH_ARC`` machinery are
        preserved for a future FreeCAD that fixes the tessellation.
        """
        _ = self.bilge_radius
        return False

    @property
    def max_bilge_radius(self) -> float:
        """Geometric upper bound for ``bilge_radius`` given ``beam_max`` and ``draft``."""
        return min(self.beam_max / 2.0, self.draft)


def _validate_hull_parameters(p: HullParameters) -> None:
    """Per-field then cross-field validation. Raises HullParameterError on
    the first violation."""
    # Per-field positivity (FR-004 + Edge Cases)
    for name, value in (
        ("loa", p.loa),
        ("beam_max", p.beam_max),
        ("draft", p.draft),
        ("freeboard", p.freeboard),
        ("sheer_height_aft", p.sheer_height_aft),
        ("sheer_height_fwd", p.sheer_height_fwd),
    ):
        # spec 029: reject non-finite first — inf passes `<= 0` (inf <= 0 is
        # False) and nan passes every comparison, so a bare positivity check
        # would let them through into the geometry build.
        if not math.isfinite(value) or value <= 0:
            raise HullParameterError(name, value, "> 0")

    # Angular ranges (FR-008 + Edge Cases)
    if not (0.0 <= p.deadrise_amidships <= 30.0):
        raise HullParameterError("deadrise_amidships", p.deadrise_amidships, "[0, 30] degrees")
    if not (0.0 <= p.transom_angle <= 45.0):
        raise HullParameterError("transom_angle", p.transom_angle, "[0, 45] degrees")
    if not (0.0 <= p.stem_rake_angle <= 30.0):
        raise HullParameterError("stem_rake_angle", p.stem_rake_angle, "[0, 30] degrees")

    # Cross-field geometric impossibility (FR-012 + Edge Cases)
    if p.loa <= p.beam_max:
        raise HullParameterError("loa<>beam_max", None, "loa must exceed beam_max")
    if p.sheer_height_fwd < p.sheer_height_aft:
        raise HullParameterError(
            "sheer_height_fwd<>sheer_height_aft",
            None,
            "sheer_height_fwd must not be below sheer_height_aft (inverted sheer)",
        )

    # spec 009 T004: station_count + bilge_radius range checks. The
    # offending-field message format is enforced by the existing
    # HullParameterError constructor; the message string includes the
    # supplied value and the valid range.
    if not (STATION_COUNT_MIN <= p.station_count <= STATION_COUNT_MAX):
        raise HullParameterError(
            "station_count",
            float(p.station_count),
            f"[{STATION_COUNT_MIN}, {STATION_COUNT_MAX}]",
        )
    # spec 029: nan slips past both `< 0` and `> max` (nan compares false to
    # everything), so guard finiteness explicitly before the range checks.
    if not math.isfinite(p.bilge_radius) or p.bilge_radius < 0:
        raise HullParameterError(
            "bilge_radius",
            p.bilge_radius,
            f"[0, {p.max_bilge_radius:.3f}]",
        )
    if p.bilge_radius > p.max_bilge_radius:
        raise HullParameterError(
            "bilge_radius",
            p.bilge_radius,
            f"[0, {p.max_bilge_radius:.3f}]",
        )


# ---------------------------------------------------------------------------
# Internal station profile (data-model §5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _StationProfile:
    """One of the hull cross-sections used by the lofted-stations construction
    strategy (research.md R2 + spec 007 R3/R4 + spec 009 T006).

    Spec 009 extends the spec 007 dataclass with three additive fields:
    ``topology``, ``bilge_radius_m`` and ``vertex_count``. The legacy
    ``is_terminal`` boolean is preserved (read by no consumer in v1.0.3 —
    kept for migration safety in case downstream code reads it).
    """

    name: str
    x_position: float
    half_beam_at_top: float
    half_beam_at_bottom: float
    keel_depth: float
    freeboard: float
    is_terminal: bool
    # spec 007: additive field. Non-zero only for the Stem profile so
    # _create_datum_plane knows to tilt the stem datum forward.
    stem_rake_angle_deg: float = 0.0
    # spec 009 additive fields (T006).
    topology: StationTopology = StationTopology.PENTAGON_LEGACY
    bilge_radius_m: float = 0.0
    vertex_count: int = 5
    # spec 031: chine-depth multiplier for the v1 bottom-outer vertex
    # (z = -keel_depth * chine_z_factor). Default 0.6 reproduces the pre-031
    # hull byte-identically; the hard_chine variant raises the chine (0.35).
    chine_z_factor: float = 0.6
    # spec 032: topside flare — the sheer (deck-edge) half-beam is widened by this
    # many metres beyond the waterline turn so the topsides flare outboard instead of
    # standing vertical. Default 0.0 = no flare (pre-032 vertical slab side).
    flare_m: float = 0.0
    # spec 032: rounded bilge — fraction (of the shorter adjacent edge) by which the
    # sharp chine corner is trimmed back and replaced by a 3-facet rounded bilge, so
    # every station is a 7-vertex section. Consistent topology keeps the Ruled=True
    # loft manifold + watertight (unlike spec 018's single arc, which broke it).
    # 0.0 = sharp chine (5-vertex legacy); > 0 = rounded (7-vertex).
    bilge_round_frac: float = 0.0


def _compute_stations(
    p: HullParameters, hull_variant: str = "standard"
) -> list[_StationProfile]:
    """Compute N station profiles for the half-hull, evenly spaced along LOA.

    Spec 009 T012: replaces the spec 007 fixed 5-station list with a
    parametric loop over ``p.station_count``. Stations are evenly spaced
    from X = 0 (transom) to X = LOA (stem), inclusive of both endpoints,
    matching the spec 007 convention.

    Per-station shape is governed by interpolation of the canonical
    spec 007 anchors (Transom, Aft, Amidships, Fwd, Stem) using a normalized
    longitudinal coordinate s ∈ [0, 1] where s = 0 at the transom and s = 1
    at the stem. The anchors live at s ∈ {0.0, 0.25, 0.5, 0.75, 1.0}; for
    arbitrary N >= 3 each station's profile is computed by piecewise-linear
    interpolation of (half_beam_top, half_beam_bottom, keel_depth, freeboard)
    between the bracketing anchors.

    Topology branches:
        - Stem (s = 1.0) AND ``p.uses_zero_forefoot_stem``: DEGENERATE_VERTEX.
        - Stem (s = 1.0) AND NOT ``p.uses_zero_forefoot_stem``:
          PENTAGON_LEGACY with 80 mm forefoot (spec 007 stem topology).
        - Non-stem AND ``p.uses_bilge_arc``: PENTAGON_WITH_ARC.
        - Non-stem AND NOT ``p.uses_bilge_arc``: PENTAGON_LEGACY.
    """
    half_beam_max = p.beam_max / 2.0
    deadrise_rad = math.radians(p.deadrise_amidships)
    _ = deadrise_rad  # reserved for future deadrise-driven sketches

    # spec 032: rounded bilge for the reference displacement hull. hard_chine keeps
    # the sharp 5-vertex chine; standard rounds it into a 7-vertex section. Every
    # station in a build shares the same vertex count (loft-compatibility).
    bilge_round = 0.0 if hull_variant == "hard_chine" else _BILGE_ROUND_STANDARD
    vcount = 7 if bilge_round > 0.0 else 5

    # Canonical anchor profiles. Each tuple is
    # (s, half_beam_top, half_beam_bottom, keel_depth, freeboard) in meters.
    # spec 009 adjustment: keel-depth anchors smoothed near the stem to
    # prevent B-spline overshoot under Ruled=False loft (spec 007 used
    # 0.55*draft / 0.08m which causes a 1.9m undershoot in B-spline
    # interpolation between amidships and stem). The smoother profile is
    # geometrically more faithful to the RC34 reference — the keel tapers
    # gradually rather than dropping abruptly at the forefoot.
    # spec 032: classic powerboat sheer — gentle dip amidships, strong rise to the
    # bow — instead of the near-flat pre-032 line. The forward sheer is lifted well
    # above sheer_height_fwd so the deck sweeps up at the stem like the RC34 reference.
    _sheer_fwd_peak = p.sheer_height_fwd * 1.22
    anchors = (
        # s,    h_top,                    h_bot,                            keel,          freeboard
        (0.00,  half_beam_max * 0.70,     half_beam_max * 0.70 * 0.60,      p.draft * 0.85, p.sheer_height_aft),
        (0.25,  half_beam_max * 0.92,     half_beam_max * 0.92 * 0.50,      p.draft * 0.97, p.sheer_height_aft * 0.96),
        (0.50,  half_beam_max,            half_beam_max * 0.40,             p.draft,        p.sheer_height_aft * 0.98),
        (0.75,  half_beam_max * 0.62,     half_beam_max * 0.62 * 0.42,      p.draft * 0.75, p.sheer_height_aft + (_sheer_fwd_peak - p.sheer_height_aft) * 0.62),
        (1.00,  0.040,                    0.040,                            p.draft * 0.22, _sheer_fwd_peak),
    )

    def _interp(s: float) -> tuple[float, float, float, float]:
        """Piecewise-linear interpolation across the 5 anchor profiles."""
        for i in range(len(anchors) - 1):
            s_lo = anchors[i][0]
            s_hi = anchors[i + 1][0]
            if s_lo <= s <= s_hi:
                t = 0.0 if s_hi == s_lo else (s - s_lo) / (s_hi - s_lo)
                lo = anchors[i][1:]
                hi = anchors[i + 1][1:]
                return tuple(  # type: ignore[return-value]
                    lo[k] + (hi[k] - lo[k]) * t for k in range(4)
                )
        # Numerical safety: s outside [0,1] uses nearest endpoint.
        return anchors[0][1:] if s < 0 else anchors[-1][1:]

    n = p.station_count
    profiles: list[_StationProfile] = []
    for i in range(n):
        # Half-hull longitudinal coordinate: i = 0 is transom (s = 0), i = n-1
        # is stem (s = 1). Evenly spaced along LOA.
        s = i / (n - 1) if n > 1 else 0.0
        x_position = s * p.loa
        is_stem = i == n - 1
        chine_z_factor = 0.6  # spec 031: default; overridden for hard-chine non-stem stations
        flare_m = 0.0  # spec 032: topside flare; set for non-stem stations below

        if is_stem and p.uses_zero_forefoot_stem:
            # Implementation drift: a true degenerate vertex causes wild
            # B-spline overshoot. THIN_STEM_HALF_WIDTH_M (5 mm) is visually
            # negligible at boat scale (vs spec 007's 80 mm) and lets the
            # AdditiveLoft converge. See StationTopology docstring.
            topology = StationTopology.PENTAGON_THIN_STEM
            half_beam_top = THIN_STEM_HALF_WIDTH_M
            half_beam_bot = THIN_STEM_HALF_WIDTH_M
            # spec 033: deeper forefoot so the bow carries volume below the
            # waterline (a fuller stem like the RC34 reference) instead of the
            # shallow 0.08 m near-zero forefoot. The keel eases from draft*0.75 at
            # s=0.75 to this depth at the stem — a smooth Ruled=True transition.
            keel_depth = 0.30
            freeboard = p.sheer_height_fwd
            vertex_count = vcount
            bilge_radius_m = 0.0
            stem_rake = p.stem_rake_angle
            name = "Stem"
        elif is_stem:
            # Legacy stem retains the spec 007 80 mm pentagon-with-forefoot.
            half_beam_top, half_beam_bot, keel_depth, freeboard = _interp(1.0)
            topology = StationTopology.PENTAGON_LEGACY
            vertex_count = vcount
            bilge_radius_m = 0.0
            stem_rake = p.stem_rake_angle
            name = "Stem"
        else:
            half_beam_top, half_beam_bot, keel_depth, freeboard = _interp(s)
            if p.uses_bilge_arc:
                topology = StationTopology.PENTAGON_WITH_ARC
                bilge_radius_m = p.bilge_radius
            else:
                topology = StationTopology.PENTAGON_LEGACY
                bilge_radius_m = 0.0
            vertex_count = vcount
            stem_rake = 0.0
            # Anchor names for indices 0, 0.25*N, 0.5*N, 0.75*N; otherwise
            # generic "StationNN" for traceability in the FreeCAD tree.
            name = "Transom" if i == 0 else f"Station{i:02d}"
            # spec 032: topside flare as a fraction of the local half-beam, stronger
            # toward the bow, capped so the pulled-in waterline turn stays outboard of
            # the chine (no section inversion / non-manifold loft).
            _flare_frac = _FLARE_FRACTION_BASE + _FLARE_FRACTION_SLOPE * s
            flare_m = min(half_beam_top * _flare_frac, (half_beam_top - half_beam_bot) * 0.7)
            # spec 031: hard-chine variant reshapes the non-stem chine vertex —
            # push it outboard toward the topside half-beam (flatter bottom,
            # sharper chine) and raise it (shallower chine). The vertex count is
            # unchanged (5), so the Ruled=True loft stays vertex-compatible.
            if hull_variant == "hard_chine":
                half_beam_bot = half_beam_bot + (half_beam_top - half_beam_bot) * _HARD_CHINE_BEAM_BLEND
                chine_z_factor = _HARD_CHINE_CHINE_Z_FACTOR

        profiles.append(
            _StationProfile(
                name=name,
                x_position=x_position,
                half_beam_at_top=half_beam_top,
                half_beam_at_bottom=half_beam_bot,
                keel_depth=keel_depth,
                freeboard=freeboard,
                is_terminal=False,
                stem_rake_angle_deg=stem_rake,
                topology=topology,
                bilge_radius_m=bilge_radius_m,
                vertex_count=vertex_count,
                chine_z_factor=chine_z_factor,
                flare_m=flare_m,
                bilge_round_frac=bilge_round,
            )
        )

    return profiles


# ---------------------------------------------------------------------------
# FreeCAD helpers (T017-T022)
# ---------------------------------------------------------------------------


def _resolve_document(document: Any) -> Any:
    """Resolve the FreeCAD document into which the hull Body is added.

    Implements FR-016 / research.md R4. See contract guarantee #3 — never
    mutates a user-supplied document's name or top-level properties.
    """
    import FreeCAD

    if document is not None:
        return document
    active = FreeCAD.activeDocument()
    if active is not None:
        return active
    return FreeCAD.newDocument()


def _resolve_body_label(name: str | None) -> str:
    """Resolve the requested Body label (FR-017 / research.md R5).

    Returns the requested name (or the default ``"Hull"``). FreeCAD applies
    its own auto-numbering when the label collides inside a document; this
    helper does not pre-disambiguate.
    """
    return name if name is not None else "Hull"


def _get_origin_plane(body: Any, plane_name: str) -> Any:
    """Find a named reference plane on the Body's auto-created Origin.

    ``plane_name`` is one of ``"XY_Plane"``, ``"XZ_Plane"``, ``"YZ_Plane"``.
    Matches the Origin feature's internal ``Name`` (stable across locales),
    not its ``Label`` (which is localized, e.g. "XY-plane"). Returns the
    FreeCAD ``App::Plane`` reference geometry. Raises ``RuntimeError`` if
    the plane cannot be located.
    """
    for feat in body.Origin.OriginFeatures:
        # FreeCAD suffixes Origin geometry names when a second Body lands in
        # the same document (`YZ_Plane` → `YZ_Plane001`). Match on the prefix
        # before the auto-numbering suffix.
        if feat.Name.rstrip("0123456789") == plane_name:
            return feat
    raise RuntimeError(f"Could not locate Origin.{plane_name} on body {body.Label!r}")


_MM_PER_M = 1000.0
"""FreeCAD's internal length unit is mm; HullParameters fields are in meters."""


def _create_datum_plane(profile: _StationProfile, body: Any) -> Any:
    """Create a PartDesign::Plane datum at the station's X coordinate.

    Per data-model §4 + research.md R3 (clarify Q1: Body-local frame). The
    datum attaches to the Body's local YZ reference plane, then offsets
    along X to ``profile.x_position * 1000`` (FreeCAD-internal mm) so the
    station sketch's plane sits parallel to YZ at the right longitudinal
    position.
    """
    import FreeCAD

    datum_name = f"HullDatum{profile.name}"
    datum = body.newObject("PartDesign::Plane", datum_name)
    yz_plane = _get_origin_plane(body, "YZ_Plane")
    datum.AttachmentSupport = [(yz_plane, "")]
    datum.MapMode = "FlatFace"
    # AttachmentOffset is in the support's LOCAL frame. For a plane attached
    # to Origin.YZ_Plane, the support's local Z axis is the global X axis
    # (the YZ plane's normal). Put the X-offset in local Z, not local X.
    #
    # Spec 007 R4 / clarify Q1: the Stem station tilts forward by
    # `stem_rake_angle` degrees around the support's local Y axis (= global Y).
    # All other stations stay parallel to YZ (identity rotation).
    if profile.name == "Stem" and profile.stem_rake_angle_deg > 0.0:
        rotation = FreeCAD.Rotation(
            FreeCAD.Vector(0, 1, 0),
            profile.stem_rake_angle_deg,
        )
    else:
        rotation = FreeCAD.Rotation()
    datum.AttachmentOffset = FreeCAD.Placement(
        FreeCAD.Vector(0.0, 0.0, profile.x_position * _MM_PER_M),
        rotation,
    )
    return datum


def _create_station_sketch(profile: _StationProfile, body: Any, datum: Any) -> Any:
    """Create a Sketcher::SketchObject for one station's half-section.

    Branches on ``profile.topology``:
        - PENTAGON_THIN_STEM: 5-vertex pentagon with THIN_STEM_HALF_WIDTH_M
          half-beam (5 mm). Implementation-equivalent to PENTAGON_LEGACY
          with thin-beam profile values; built via the same constructor.
        - PENTAGON_LEGACY: the spec 007 5-line pentagon (5 vertices, 5
          straight segments closed with Coincident constraints).
        - PENTAGON_WITH_ARC (spec 009 T021): 4 line segments + 1
          quarter-circle bilge arc replacing the bottom-to-topside diagonal.
          The arc is tangent-constrained to both adjacent line segments via
          ``Sketcher.Constraint("Tangent", ...)`` and radius-locked via
          ``Sketcher.Constraint("Radius", ...)`` so the parametric solver
          maintains tangent continuity even if the user nudges vertices in
          the FreeCAD GUI.
    """
    if profile.topology == StationTopology.PENTAGON_WITH_ARC:
        return _create_pentagon_with_arc_station_sketch(profile, body, datum)
    return _create_pentagon_legacy_station_sketch(profile, body, datum)


def _create_pentagon_legacy_station_sketch(
    profile: _StationProfile, body: Any, datum: Any
) -> Any:
    """Spec 007 5-line pentagon (preserved verbatim from v1.0.2).

    Vertices: keel-centerline (0, -keel_depth), bottom-outer
    (half_beam_at_bottom, -keel_depth * 0.6), top-outer (half_beam_at_top, 0),
    outer-sheer (half_beam_at_top, freeboard), centerline-deck (0, freeboard).
    """
    import FreeCAD
    import Part
    import Sketcher

    sketch_name = f"HullStation{profile.name}"
    sketch = body.newObject("Sketcher::SketchObject", sketch_name)
    sketch.AttachmentSupport = [(datum, "")]
    sketch.MapMode = "FlatFace"

    keel_depth_mm = profile.keel_depth * _MM_PER_M
    half_beam_top_mm = profile.half_beam_at_top * _MM_PER_M
    half_beam_bottom_mm = profile.half_beam_at_bottom * _MM_PER_M
    freeboard_mm = profile.freeboard * _MM_PER_M

    flare_mm = profile.flare_m * _MM_PER_M
    keel = FreeCAD.Vector(0.0, -keel_depth_mm, 0.0)
    chine = FreeCAD.Vector(half_beam_bottom_mm, -keel_depth_mm * profile.chine_z_factor, 0.0)
    # spec 032: flare keeps the DECK at max beam (half_beam_top) and pulls the
    # waterline turn inward by flare_m, so the topsides flare outward going up
    # without the deck exceeding the cited max beam.
    turn = FreeCAD.Vector(half_beam_top_mm - flare_mm, 0.0, 0.0)
    sheer = FreeCAD.Vector(half_beam_top_mm, freeboard_mm, 0.0)
    deck = FreeCAD.Vector(0.0, freeboard_mm, 0.0)

    frac = profile.bilge_round_frac
    if frac <= 0.0:
        # Legacy sharp chine (5-vertex).
        pts = [keel, chine, turn, sheer, deck]
    else:
        # spec 032: replace the sharp chine corner with a 3-facet rounded bilge,
        # trimming back along the keel->chine and chine->turn edges and pulling a
        # mid point toward the corner. 7-vertex section, identical topology on every
        # station (incl. the stem) so the Ruled=True loft stays manifold + watertight.
        seg_in = (chine - keel).Length
        seg_out = (turn - chine).Length
        t = frac * min(seg_in, seg_out)
        din = chine - keel
        din.normalize()
        dout = turn - chine
        dout.normalize()
        a = FreeCAD.Vector(chine.x - din.x * t, chine.y - din.y * t, 0.0)
        c = FreeCAD.Vector(chine.x + dout.x * t, chine.y + dout.y * t, 0.0)
        mid = FreeCAD.Vector((a.x + c.x) / 2.0, (a.y + c.y) / 2.0, 0.0)
        b = FreeCAD.Vector(
            mid.x + (chine.x - mid.x) * 0.55, mid.y + (chine.y - mid.y) * 0.55, 0.0
        )
        pts = [keel, a, b, c, turn, sheer, deck]

    line_ids: list[int] = []
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        seg = Part.LineSegment(pts[i], pts[j])
        line_ids.append(sketch.addGeometry(seg, False))
    for i in range(len(line_ids)):
        j = (i + 1) % len(line_ids)
        sketch.addConstraint(
            Sketcher.Constraint("Coincident", line_ids[i], 2, line_ids[j], 1)
        )
    return sketch


def _create_pentagon_with_arc_station_sketch(
    profile: _StationProfile, body: Any, datum: Any
) -> Any:
    """Pentagon cross-section with a Sketcher-filleted bilge corner.

    Builds the spec 007 5-line pentagon, then applies ``Sketcher.fillet()``
    to the chine corner (between the bottom-outer line and the topside
    diagonal). Sketcher computes a tangent-continuous arc, adjusts the
    adjacent line endpoints to meet the arc, and adds the appropriate
    Coincident + Radius constraints. The radius is capped to a per-station
    safe value: when the cross-section is too narrow to fit the requested
    radius, the radius is reduced to fit. When the cap is zero or the
    fillet would degenerate, falls back to the legacy 5-line pentagon.

    Spec 009 implementation reality (documented in closure note): the
    "always quarter-circle radius = bilge_radius" promise of FR-008 is
    relaxed to "at most bilge_radius, scaled per station to fit". Spec
    invariant ``BilgeArc.RadiusMatchesParameters`` becomes
    ``BilgeArc.RadiusBoundedByParameters``.
    """
    import FreeCAD
    import Part
    import Sketcher

    sketch_name = f"HullStation{profile.name}"
    sketch = body.newObject("Sketcher::SketchObject", sketch_name)
    sketch.AttachmentSupport = [(datum, "")]
    sketch.MapMode = "FlatFace"

    keel_depth_mm = profile.keel_depth * _MM_PER_M
    half_beam_top_mm = profile.half_beam_at_top * _MM_PER_M
    half_beam_bottom_mm = profile.half_beam_at_bottom * _MM_PER_M
    freeboard_mm = profile.freeboard * _MM_PER_M
    requested_radius_mm = profile.bilge_radius_m * _MM_PER_M

    # Compute per-station safe radius: the chord between v1 and v2 must
    # be at least twice the radius (for the quarter-circle to fit between
    # the two endpoints without crossing the centerline).
    v0 = FreeCAD.Vector(0.0, -keel_depth_mm, 0.0)
    v1 = FreeCAD.Vector(half_beam_bottom_mm, -keel_depth_mm * profile.chine_z_factor, 0.0)
    v2 = FreeCAD.Vector(half_beam_top_mm, 0.0, 0.0)
    v3 = FreeCAD.Vector(half_beam_top_mm, freeboard_mm, 0.0)
    v4 = FreeCAD.Vector(0.0, freeboard_mm, 0.0)

    chord_len_mm = math.hypot(v2.x - v1.x, v2.y - v1.y)
    safe_radius_mm = min(requested_radius_mm, chord_len_mm * 0.4)

    pts = [v0, v1, v2, v3, v4]
    line_ids: list[int] = []
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        seg = Part.LineSegment(pts[i], pts[j])
        line_ids.append(sketch.addGeometry(seg, False))
    for i in range(len(line_ids)):
        j = (i + 1) % len(line_ids)
        sketch.addConstraint(
            Sketcher.Constraint("Coincident", line_ids[i], 2, line_ids[j], 1)
        )

    # Apply a fillet at the chine corner (line_ids[1] = bottom-outer to
    # topside diagonal, line_ids[2] = topside vertical, junction at v2).
    # Wait — re-checking: the chine that gets the fillet is the corner
    # between line_ids[0] (v0→v1, bottom edge) and line_ids[1] (v1→v2,
    # bilge diagonal). The junction point is v1.
    if safe_radius_mm < 1.0:
        # Radius too small to be meaningful; fall back to the sharp chine.
        return sketch

    # FreeCAD Sketcher.fillet(geo_id_1, geo_id_2, radius) — short form,
    # auto-detects the shared corner. The chine corner is the junction
    # between line_ids[0] (v0→v1, bottom edge) and line_ids[1] (v1→v2,
    # bilge diagonal). Fillet failures fall back to the sharp chine (the
    # geometry is already a valid 5-line pentagon at this point).
    with contextlib.suppress(Exception):
        sketch.fillet(line_ids[0], line_ids[1], safe_radius_mm)

    return sketch


def _build_loft(body: Any, sketches: list[Any], *, ruled: bool) -> Any:
    """Construct a PartDesign::AdditiveLoft on the body with the given Ruled mode.

    Spec 007 R6 helper. Caller is responsible for `Document.recompute()`.
    """
    loft = body.newObject("PartDesign::AdditiveLoft", "HullLoft")
    loft.Profile = (sketches[0], [""])
    loft.Sections = [(s, [""]) for s in sketches[1:]]
    loft.Ruled = ruled
    loft.Closed = False
    return loft


def _apply_loft_and_mirror(
    body: Any, sketches: list[Any], parameters: HullParameters
) -> tuple[Any, Any]:
    """Build the PartDesign feature stack: AdditiveLoft + Mirrored.

    The loft uses ``Ruled=True`` for ALL station counts. ``Ruled=False``
    (B-spline) is permanently infeasible for the Storebro profile in
    FreeCAD 1.1.1: a spec 018 spike measured 12-141% beam overshoot across
    every station-spacing strategy (vs the ±1% bar), while ``Ruled=True`` is
    exact (0%). See ``HullParameters.uses_b_spline_loft``.

    Visual smoothness comes from station *density* (spec 018: default 31, cap
    81) under the exact ``Ruled=True`` loft, not from interpolation or the
    bilge arc (which re-defers to the sharp chine — its mesh is non-watertight;
    see ``uses_bilge_arc``). ``parameters`` is retained in the signature as a
    forward-compat hook.

    The mirror feature reflects the loft across the Body's XZ plane,
    producing the closed full-hull solid. ``Body.Tip`` is set to the mirror.

    Returns ``(loft, mirror)`` so the caller can register both features in
    the rollback list (FR-012).
    """
    _ = parameters  # forward-compat hook; unused in v1.0.3
    loft = _build_loft(body, sketches, ruled=True)
    body.Document.recompute()

    mirror = body.newObject("PartDesign::Mirrored", "HullMirror")
    mirror.Originals = [loft]
    mirror.MirrorPlane = (_get_origin_plane(body, "XZ_Plane"), [""])

    body.Tip = mirror
    return (loft, mirror)


def _detect_b_spline_overshoot(
    body: Any, parameters: HullParameters
) -> None:
    """No-op in v1.0.3 — B-spline loft is deferred to v1.1+.

    Original intent (spec 009 T015): fail fast on B-spline overshoot.
    Implementation reality: spec 009 ships with Ruled=True everywhere, so
    overshoot is impossible by construction (piecewise-linear lofts cannot
    exceed the convex hull of their station sketches). The helper is
    retained as a forward-compatibility hook for the v1.1+ B-spline work
    that re-opens ``Hull.b_spline_loft``.
    """
    _ = body, parameters  # forward-compat hook; unused in v1.0.3
    return


def _bind_parameters_to_body_properties(body: Any, parameters: HullParameters) -> None:
    """Expose hull dimensions as named FreeCAD properties on the Body.

    Implements FR-007 — the FreeCAD GUI's property panel shows these named
    fields so a user can edit a dimension and (after future expression
    bindings) trigger a parametric recompute. In v0.1.0-alpha the properties
    are read-only mirrors of the input parameters; the expression engine
    bindings that propagate edits back into the sketches are deferred to a
    PartDesign loft upgrade (see _apply_loft_and_mirror docstring).
    """
    body.addProperty("App::PropertyLength", "LOA", "Hull", "Length overall")
    body.addProperty("App::PropertyLength", "BeamMax", "Hull", "Maximum beam")
    body.addProperty("App::PropertyLength", "Draft", "Hull", "Draft at amidships")
    body.addProperty("App::PropertyLength", "Freeboard", "Hull", "Freeboard at amidships")
    body.addProperty("App::PropertyLength", "SheerHeightAft", "Hull", "Sheer height at transom")
    body.addProperty("App::PropertyLength", "SheerHeightFwd", "Hull", "Sheer height at stem")
    body.addProperty(
        "App::PropertyAngle",
        "DeadriseAmidships",
        "Hull",
        "Deadrise angle at amidships",
    )
    body.addProperty(
        "App::PropertyAngle",
        "TransomAngle",
        "Hull",
        "Transom rake from vertical",
    )
    # Spec 007 FR-007: 9th property — stem rake from vertical (forward lean
    # of the blunt bow face).
    body.addProperty(
        "App::PropertyAngle",
        "StemRakeAngle",
        "Hull",
        "Stem rake from vertical (forward lean of bow)",
    )

    # FreeCAD App::PropertyLength uses millimetres internally; multiply by
    # 1000 to keep the displayed value in meters consistent with the
    # parameter contract documented in HullParameters.
    body.LOA = parameters.loa * 1000.0
    body.BeamMax = parameters.beam_max * 1000.0
    body.Draft = parameters.draft * 1000.0
    body.Freeboard = parameters.freeboard * 1000.0
    body.SheerHeightAft = parameters.sheer_height_aft * 1000.0
    body.SheerHeightFwd = parameters.sheer_height_fwd * 1000.0
    body.DeadriseAmidships = parameters.deadrise_amidships
    body.TransomAngle = parameters.transom_angle
    body.StemRakeAngle = parameters.stem_rake_angle


# ---------------------------------------------------------------------------
# Spec 011 — hull glazing (porthole) parameters + wrapper (data-model §1, §3.1)
#
# Portholes are blind circular PartDesign::Pocket recesses cut into the hull
# topsides above the waterline, port + starboard, appended after the Mirror
# feature (so they cut the full mirrored solid and become the body Tip).
# All lengths in mm. The hull is a SOLID loft, so a recess is bounded by the
# local half-beam, not a wall thickness.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PortholeParameters:
    """Porthole recess parameters (data-model §1.1).

    A row of ``count_per_side`` blind circular recesses per side. The
    sentinel ``0.0`` on ``forward_x`` / ``aft_x`` / ``height_above_waterline``
    means "derive from the actual hull geometry in :func:`build_hull`" (so
    this dataclass needs no hull reference). All lengths in millimeters.

    Example:
        >>> p = PortholeParameters()
        >>> p.count_per_side, p.diameter
        (3, 220.0)
        >>> PortholeParameters(count_per_side=0).count_per_side
        0
    """

    count_per_side: int = 3
    diameter: float = 220.0
    recess_depth: float = 20.0
    forward_x: float = 0.0
    aft_x: float = 0.0
    height_above_waterline: float = 0.0

    def __post_init__(self) -> None:
        if self.count_per_side < 0:
            raise HullParameterError("porthole_count_per_side", self.count_per_side, ">= 0")
        for name, value in (
            ("porthole_diameter", self.diameter),
            ("porthole_recess_depth", self.recess_depth),
        ):
            if not math.isfinite(value) or value <= 0:  # spec 029: reject nan/inf
                raise HullParameterError(name, value, "> 0")
        for name, value in (
            ("porthole_forward_x", self.forward_x),
            ("porthole_aft_x", self.aft_x),
            ("porthole_height_above_waterline", self.height_above_waterline),
        ):
            # spec 029: reject nan/inf; the finite 0.0 "derive" sentinel is finite
            # so it still passes (handled by the cross-field check below).
            if not math.isfinite(value) or value < 0:
                raise HullParameterError(name, value, ">= 0")
        # 0/0 is the "derive span" sentinel; otherwise forward must precede aft.
        if self.forward_x != 0.0 and self.aft_x != 0.0 and self.forward_x >= self.aft_x:
            raise HullParameterError(
                "porthole_forward_x<>aft_x", None, "forward_x must be < aft_x"
            )


@dataclass(frozen=True)
class HullGlazingParameters:
    """Composite of the hull glazing parameter dataclasses (data-model §1.2).

    The optional ``parameters_glazing`` entry point for :func:`build_hull`.

    spec 019 adds translucent glass panes seated in the porthole recesses,
    on by default. ``glass_panes`` is the opt-out; ``glass_thickness`` is the
    pane thickness in mm.

    Example:
        >>> p = HullGlazingParameters()
        >>> p.portholes.count_per_side, p.glass_panes
        (3, True)
    """

    portholes: PortholeParameters = field(default_factory=PortholeParameters)
    glass_panes: bool = True
    glass_thickness: float = 6.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.glass_thickness) or self.glass_thickness <= 0:  # spec 029
            raise HullParameterError("hull_glass_thickness", self.glass_thickness, "> 0")


@dataclass(frozen=True)
class Porthole:
    """Wrapper describing the portholes cut into the hull (data-model §3.1).

    ``body`` is the HullBody itself (the portholes are Pocket features on it).

    Example:
        >>> # Accessed via Hull.portholes after build_hull() returns.
    """

    body: Any
    count: int
    diameter: float


# ---------------------------------------------------------------------------
# Return aggregate (data-model §2)
# ---------------------------------------------------------------------------


@dataclass
class Hull:
    """Return value of :func:`build_hull`. Wraps the FreeCAD Body and carries
    the inputs alongside it.

    Example:
        >>> # After: hull = build_hull()
        >>> # hull.parameters, hull.bbox, hull.volume are available.
    """

    body: Any
    parameters: HullParameters
    document: Any
    label: str
    build_duration_seconds: float = field(default=0.0)
    # spec 011 — glazing (appended with defaults; Hull is only constructed
    # inside build_hull, so adding fields is non-breaking for callers).
    portholes: Porthole | None = None
    parameters_glazing: HullGlazingParameters = field(default_factory=HullGlazingParameters)
    # spec 031 — hull variant bookkeeping. variant_applied is False iff a
    # hard-chine build fell back to the standard hull (FR-006/FR-010).
    hull_variant: str = "standard"
    variant_applied: bool = True

    @property
    def bbox(self) -> tuple[float, float, float]:
        """``(length, width, height)`` of the body's bounding box.

        Returns values in meters (FreeCAD reports millimeters internally;
        this property converts to meters for consistency with the parameter
        contract on :class:`HullParameters`).
        """
        bb = self.body.Shape.BoundBox
        return (bb.XLength / 1000.0, bb.YLength / 1000.0, bb.ZLength / 1000.0)

    @property
    def volume(self) -> float:
        """Volume of the body's shape, in cubic meters."""
        # FreeCAD reports volume in cubic millimeters; convert to m^3.
        return float(self.body.Shape.Volume) / 1.0e9


# ---------------------------------------------------------------------------
# Spec 011 — porthole recesses (data-model §6, research R2)
#
# Blind circular PartDesign::Pocket recesses cut into the hull topsides above
# the waterline, port + starboard, appended after the Mirror feature. The
# hull is a SOLID loft, so the manifold guard is recess_depth < local
# half-beam (the recess cannot reach the far side). A post-cut solid-count /
# validity assertion is the spec 009 non-manifold regression guard.
# ---------------------------------------------------------------------------

_WATERLINE_Z_MM = 0.0
"""Design waterline is the Z=0 datum (keel below, freeboard above)."""


def _hull_outer_y_and_freeboard_at(body: Any, x_mm: float) -> tuple[float, float]:
    """Return (sheer half-beam, freeboard) in mm at longitudinal station X.

    Sourced from the actual hull shape vertices near X (not analytical), so
    portholes seat on the real geometry. Freeboard is the max vertex Z above
    the waterline at that station; the sheer half-beam is the max |Y|.
    """
    shape = body.Shape
    near = [v for v in shape.Vertexes if abs(v.X - x_mm) < 0.05 * shape.BoundBox.XLength]
    if not near:
        near = list(shape.Vertexes)
    outer_y = max((abs(v.Y) for v in near), default=shape.BoundBox.YMax)
    freeboard = max((v.Z for v in near), default=shape.BoundBox.ZMax) - _WATERLINE_Z_MM
    return outer_y, freeboard


def _cut_portholes(
    body: Any,
    hull_params: HullParameters,
    glazing: HullGlazingParameters,
    added: list[Any],
) -> tuple[Porthole, list[Any]]:
    """Cut the porthole recesses into the hull body (FR-001, FR-007).

    Returns ``(Porthole, glass_bodies)`` — the wrapper plus the list of
    translucent glass-pane Bodies seated in the recesses (spec 019; empty when
    glazing.glass_panes is False or count is zero). Zero-count → no cuts
    (FR-011). Raises :class:`HullParameterError` for a recess that would reach
    the far side, a porthole at/below the waterline, or a diameter exceeding the
    local freeboard (data-model §6).
    """
    import FreeCAD
    import Part

    pp = glazing.portholes
    loa_mm = hull_params.loa * _MM_PER_M
    glass_bodies: list[Any] = []
    if pp.count_per_side == 0:
        return (Porthole(body=body, count=0, diameter=pp.diameter / _MM_PER_M), glass_bodies)

    # Derive the longitudinal span (sentinel 0/0 → the accommodation region,
    # 30%..70% of LOA) and the vertical centre (sentinel 0 → upper topside at
    # 0.70 * local freeboard, where the topside is widest so the recess seats
    # cleanly).
    fwd_x = pp.forward_x if pp.forward_x > 0.0 else 0.30 * loa_mm
    aft_x = pp.aft_x if pp.aft_x > 0.0 else 0.70 * loa_mm

    if pp.count_per_side == 1:
        x_stations = [(fwd_x + aft_x) / 2.0]
    else:
        step = (aft_x - fwd_x) / (pp.count_per_side - 1)
        x_stations = [fwd_x + i * step for i in range(pp.count_per_side)]

    radius = pp.diameter / 2.0
    xz_plane = _get_origin_plane(body, "XZ_Plane")
    seq = 0
    for x_mm in x_stations:
        outer_y, freeboard = _hull_outer_y_and_freeboard_at(body, x_mm)
        # Manifold + placement guards (FR-007).
        if pp.recess_depth >= outer_y:
            raise HullParameterError(
                "porthole_recess_depth<>half_beam",
                pp.recess_depth,
                f"< local half-beam ({outer_y:.0f} mm) so the recess stays blind",
            )
        if pp.diameter >= freeboard:
            raise HullParameterError(
                "porthole_diameter<>freeboard",
                pp.diameter,
                f"< local freeboard ({freeboard:.0f} mm)",
            )
        z_center = (
            pp.height_above_waterline
            if pp.height_above_waterline > 0.0
            else _WATERLINE_Z_MM + 0.70 * freeboard
        )
        if z_center <= _WATERLINE_Z_MM:
            raise HullParameterError(
                "porthole_height_above_waterline",
                z_center,
                "> waterline (a porthole below the waterline is a hole in the boat)",
            )
        for side, sign in (("Port", 1.0), ("Starboard", -1.0)):
            seq += 1
            datum = body.newObject("PartDesign::Plane", f"PortholeDatum{side}{seq}")
            added.append(datum)
            datum.AttachmentSupport = [(xz_plane, "")]
            datum.MapMode = "FlatFace"
            # XZ_Plane local frame: local X = global X, local Y = global Z,
            # local Z = global Y (normal). Place datum just outboard of the
            # sheer at this station: global (x, sign*(outer_y+2), z=0) →
            # local (x, 0, sign*(outer_y+2)).
            datum.AttachmentOffset = FreeCAD.Placement(
                FreeCAD.Vector(x_mm, 0.0, sign * (outer_y + 2.0)),
                FreeCAD.Rotation(),
            )
            sketch = body.newObject("Sketcher::SketchObject", f"PortholeSketch{side}{seq}")
            added.append(sketch)
            sketch.AttachmentSupport = [(datum, "")]
            sketch.MapMode = "FlatFace"
            # Sketch coords are LOCAL to the datum (already at global x_mm); use
            # local X = 0 — re-adding x_mm doubled the position so the porthole was
            # cut at 2*x (off the hull) and never actually appeared (spec 019 bug).
            circle = Part.Circle(
                FreeCAD.Vector(0.0, z_center, 0), FreeCAD.Vector(0, 0, 1), radius
            )
            sketch.addGeometry(circle.toShape().Curve, False)
            pocket = body.newObject("PartDesign::Pocket", f"PortholePocket{side}{seq}")
            added.append(pocket)
            pocket.Profile = (sketch, [""])
            pocket.Length = pp.recess_depth + 2.0  # +2 to bridge the datum offset
            pocket.Reversed = sign > 0.0  # cut toward the centerline
            pocket.Midplane = False

            # spec 019 — a translucent glass disc seated in the recess: a
            # separate additive Body (never a boolean on the hull), so the hull
            # solid stays manifold. Centred a touch inboard of the outer
            # surface, X-thin along the local normal (global Y).
            if glazing.glass_panes:
                inset = sign * (outer_y - pp.recess_depth * 0.5)
                g_body = body.Document.addObject(
                    "PartDesign::Body", f"Hull_PortholeGlass{side}{seq}"
                )
                added.append(g_body)
                body.Document.recompute()
                g_xz = _get_origin_plane(g_body, "XZ_Plane")
                g_datum = g_body.newObject("PartDesign::Plane", f"PortholeGlassDatum{side}{seq}")
                added.append(g_datum)
                g_datum.AttachmentSupport = [(g_xz, "")]
                g_datum.MapMode = "FlatFace"
                g_datum.AttachmentOffset = FreeCAD.Placement(
                    FreeCAD.Vector(x_mm, 0.0, inset), FreeCAD.Rotation()
                )
                g_sketch = g_body.newObject(
                    "Sketcher::SketchObject", f"PortholeGlassSketch{side}{seq}"
                )
                added.append(g_sketch)
                g_sketch.AttachmentSupport = [(g_datum, "")]
                g_sketch.MapMode = "FlatFace"
                # Datum-local coords (datum already at global x_mm); local X = 0
                # so the glass disc seats over its porthole instead of at 2*x.
                g_circle = Part.Circle(
                    FreeCAD.Vector(0.0, z_center, 0), FreeCAD.Vector(0, 0, 1), radius
                )
                g_sketch.addGeometry(g_circle.toShape().Curve, False)
                g_pad = g_body.newObject("PartDesign::Pad", f"PortholeGlassPad{side}{seq}")
                added.append(g_pad)
                g_pad.Profile = (g_sketch, [""])
                g_pad.Length = glazing.glass_thickness
                g_pad.Midplane = True
                glass_bodies.append(g_body)

    return (
        Porthole(
            body=body,
            count=pp.count_per_side * 2,
            diameter=pp.diameter / _MM_PER_M,
        ),
        glass_bodies,
    )


def _is_single_valid_solid(shape: Any) -> bool:
    """spec 031: True iff ``shape`` is a non-null, valid, single-solid B-rep.

    Used by the hard-chine manifold-or-fallback gate (FR-006) — a non-raising
    sibling of :func:`_assert_hull_manifold`.
    """
    return (
        shape is not None
        and not shape.isNull()
        and shape.isValid()
        and len(shape.Solids) == 1
    )


def _assert_hull_manifold(body: Any, parameters: HullParameters) -> None:
    """FR-008: after cuts, the hull must remain a single closed solid.

    The spec 009 non-manifold regression guard. Blind recesses should never
    trip this; a trip means a genuine bug, so fail loudly (rollback).
    """
    shape = body.Shape
    solids = shape.Solids
    if len(solids) != 1 or not shape.isValid():
        raise HullConstructionError(
            f"hull is non-manifold after glazing cuts "
            f"(solids={len(solids)}, valid={shape.isValid()})",
            parameters=parameters,
        )


# ---------------------------------------------------------------------------
# Public builder (FR-001 + contracts/python-api.md)
# ---------------------------------------------------------------------------


def build_hull(
    parameters: HullParameters | None = None,
    *,
    parameters_glazing: HullGlazingParameters | None = None,
    hull_variant: Literal["standard", "hard_chine"] = "standard",
    document: Any = None,
    name: str = "Hull",
    apply_render_attributes: bool = True,
) -> Hull:
    """Build a parametric Storebro hull Body in a FreeCAD document.

    Args:
        parameters: Hull dimensional parameters. ``None`` → use
            :class:`HullParameters` defaults (the canonical Storebro Royal
            Cruiser 34, 1972 model, within ±1% reference fidelity).
        document: Target FreeCAD document. ``None`` → use the active
            document if one exists, else create a new one and activate it.
            A caller-supplied document is never renamed or mutated beyond
            the Body addition (FR-016).
        hull_variant: Cross-section variant (spec 031). ``"standard"`` (default)
            is the round-ish soft-chine hull, byte-identical to pre-031.
            ``"hard_chine"`` reshapes each station's chine vertex outboard and up
            for a pronounced hard chine; it falls back to the standard hull (with
            ``Hull.variant_applied = False``) if the reshaped loft is non-manifold.
        name: Body ``Label``. Defaults to ``"Hull"``. FreeCAD's standard
            auto-numbering applies on label collision (``Hull``,
            ``Hull001``, ``Hull002``).

    Returns:
        :class:`Hull` — wraps the FreeCAD Body, the input parameters,
        the target document, the resolved label, and the build duration.

    Raises:
        HullParameterError: If ``parameters`` (or its defaults) fails
            validation. Raised BEFORE any FreeCAD call.
        HullConstructionError: If the FreeCAD runtime version is outside
            the supported range, or if FreeCAD fails to construct the hull
            despite valid parameters.

    Example:
        >>> from storebro import build_hull, HullParameters
        >>> hull = build_hull()  # defaults: Storebro Royal Cruiser 34 (1972)
        >>> abs(hull.bbox[0] - 10.35) < 0.1035  # within ±1% of LOA = 10.35 m  # doctest: +SKIP
        True
        >>> custom = build_hull(HullParameters(loa=12.0, beam_max=3.8))  # doctest: +SKIP
        >>> custom.bbox[0] > hull.bbox[0]  # doctest: +SKIP
        True
        >>> chined = build_hull(hull_variant="hard_chine")  # doctest: +SKIP
        >>> chined.hull_variant  # doctest: +SKIP
        'hard_chine'
    """
    # spec 031 — hull variant guard (before ANY FreeCAD call, so it is
    # unit-testable without a FreeCAD runtime and fails fast).
    if hull_variant not in ("standard", "hard_chine"):
        raise HullParameterError(
            "hull_variant",
            None,
            "one of {'standard', 'hard_chine'}",
        )

    # Lazy first-call version check (FR-013 / research.md R6).
    from storebro._freecad_check import ensure_supported_freecad

    ensure_supported_freecad()

    # Validate parameters (FR-004). __post_init__ already validated, but
    # callers can subclass HullParameters and bypass __post_init__; defend
    # against that by re-validating on entry.
    resolved_params = parameters if parameters is not None else HullParameters()
    _validate_hull_parameters(resolved_params)

    # spec 011 — resolve glazing (portholes on by default).
    glazing = parameters_glazing if parameters_glazing is not None else HullGlazingParameters()

    # Resolve document (FR-016).
    target_doc = _resolve_document(document)
    body_label = _resolve_body_label(name)

    started = time.perf_counter()
    added: list[Any] = []
    variant_applied = True
    try:
        body = target_doc.addObject("PartDesign::Body", "HullBody")
        added.append(body)
        body.Label = body_label

        # Recompute once now so the auto-created Origin's reference planes
        # are populated and accessible via body.Origin.OriginFeatures before
        # we attach datums/sketches to them.
        target_doc.recompute()

        _bind_parameters_to_body_properties(body, resolved_params)

        def _build_stations(variant: str) -> list[Any]:
            """Build the datums + station sketches + loft + mirror for ``variant``.

            Returns every object it created so the spec 031 manifold-or-fallback
            gate can discard them if the hard-chine loft is non-manifold.
            """
            created: list[Any] = []
            sks: list[Any] = []
            for profile in _compute_stations(resolved_params, variant):
                datum = _create_datum_plane(profile, body)
                added.append(datum)
                created.append(datum)
                sk = _create_station_sketch(profile, body, datum)
                added.append(sk)
                created.append(sk)
                sks.append(sk)
            lft, mir = _apply_loft_and_mirror(body, sks, resolved_params)
            added.extend([lft, mir])
            created.extend([lft, mir])
            target_doc.recompute()
            return created

        # spec 031 — build the requested variant, with a manifold-or-fallback gate
        # (FR-006): if the hard-chine loft is not a single valid solid, discard it
        # and rebuild the standard hull, recording variant_applied = False.
        variant_objs = _build_stations(hull_variant)
        if hull_variant == "hard_chine" and not _is_single_valid_solid(body.Shape):
            for obj in reversed(variant_objs):
                added[:] = [a for a in added if getattr(a, "Name", None) != obj.Name]
                with contextlib.suppress(BaseException):
                    target_doc.removeObject(obj.Name)
            with contextlib.suppress(BaseException):
                body.Tip = None
            _build_stations("standard")
            variant_applied = False

        # spec 009 T016: fail fast if the B-spline loft overshoots the
        # explicit hull height envelope. No-op when the loft is Ruled=True.
        _detect_b_spline_overshoot(body, resolved_params)

        # spec 011 — cut porthole recesses after the mirror, then assert the
        # hull is still a single closed solid (FR-008 non-manifold guard).
        portholes, porthole_glass = _cut_portholes(body, resolved_params, glazing, added)
        target_doc.recompute()
        _assert_hull_manifold(body, resolved_params)
    except HullParameterError:
        # spec 011: porthole cross-geometry validation (recess vs half-beam,
        # above-waterline, diameter vs freeboard) runs inside the try because
        # it needs the built hull; let it propagate as a parameter error
        # rather than being re-wrapped as a construction failure.
        for obj in reversed(added):
            with contextlib.suppress(BaseException):
                target_doc.removeObject(obj.Name)
        raise
    except HullConstructionError:
        for obj in reversed(added):
            with contextlib.suppress(BaseException):
                target_doc.removeObject(obj.Name)
        raise
    except BaseException as underlying:
        for obj in reversed(added):
            with contextlib.suppress(BaseException):
                target_doc.removeObject(obj.Name)
        raise HullConstructionError(
            "FreeCAD failed to construct hull with parameters "
            f"{resolved_params!r} — {type(underlying).__name__}: {underlying}",
            parameters=resolved_params,
            underlying=underlying,
        ) from underlying

    # spec 015 — cosmetic render attributes (gelcoat-white hull). On by default;
    # geometry is already committed, so this is outside the rollback try-block.
    from storebro.render import apply_render_attributes as _apply_render_attributes

    _apply_render_attributes([body, *porthole_glass], enabled=apply_render_attributes)

    duration = time.perf_counter() - started
    return Hull(
        body=body,
        parameters=resolved_params,
        document=target_doc,
        label=body.Label,
        build_duration_seconds=duration,
        portholes=portholes,
        parameters_glazing=glazing,
        hull_variant=hull_variant,
        variant_applied=variant_applied,
    )
