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
import math
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    pass

__all__ = [
    "Hull",
    "HullConstructionError",
    "HullParameterError",
    "HullParameters",
    "build_hull",
]


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
        if value <= 0:
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


# ---------------------------------------------------------------------------
# Internal station profile (data-model §5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _StationProfile:
    """One of the five hull cross-sections used by the lofted-stations
    construction strategy (research.md R2 + spec 007 R3/R4)."""

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


def _compute_stations(p: HullParameters) -> list[_StationProfile]:
    """Compute the five station profiles per research.md R2.

    Profiles, transom to stem:
        - transom    at x = 0
        - aft        at x = 0.25 · LOA
        - amidships  at x = 0.50 · LOA  (governs beam_max + deadrise)
        - fwd        at x = 0.75 · LOA
        - stem       at x = LOA          (collapses to centerline vertex)
    """
    half_beam_max = p.beam_max / 2.0

    # Half-beam tapers from beam_max at amidships toward stem and transom.
    # Transom is typically ~70% of max beam, bow stations narrow further.
    # Stem: finite blunt face (40mm half-width = 80mm full width) per spec
    # 007 FR-003 — a real RC34's stem strip is ~80-100mm wide, not a knife edge.
    half_beam_transom = half_beam_max * 0.70
    half_beam_aft = half_beam_max * 0.92
    half_beam_amidships = half_beam_max
    half_beam_fwd = half_beam_max * 0.55
    half_beam_stem = 0.040  # 40mm half-width (= 80mm stem face)

    # Deadrise at amidships drives how deep the keel sits below the waterline.
    # The other stations interpolate; the actual keel-depth profile is a
    # smooth curve, approximated here by station-wise depth.
    deadrise_rad = math.radians(p.deadrise_amidships)
    keel_depth_amidships = p.draft
    # Stations away from amidships have shallower keel depth (V flattens
    # toward both ends).
    keel_depth_transom = p.draft * 0.75
    keel_depth_aft = p.draft * 0.95
    keel_depth_fwd = p.draft * 0.55
    # spec 007: small forefoot below the bow (was 0 in v1.0.0). Keeps the
    # Stem station topologically a 5-vertex pentagon matching the other
    # stations — required for PartDesign::AdditiveLoft Ruled=True to map
    # vertices 1:1 without twisting (~4cm forefoot ≈ 0.4% of LOA, barely
    # visible at boat scale but loft-stable).
    keel_depth_stem = 0.08
    _ = deadrise_rad  # reserved for future deadrise-driven sketches

    return [
        _StationProfile(
            name="Transom",
            x_position=0.0,
            half_beam_at_top=half_beam_transom,
            half_beam_at_bottom=half_beam_transom * 0.60,
            keel_depth=keel_depth_transom,
            freeboard=p.sheer_height_aft,
            is_terminal=False,
        ),
        _StationProfile(
            name="Aft",
            x_position=0.25 * p.loa,
            half_beam_at_top=half_beam_aft,
            half_beam_at_bottom=half_beam_aft * 0.50,
            keel_depth=keel_depth_aft,
            freeboard=p.sheer_height_aft + (p.sheer_height_fwd - p.sheer_height_aft) * 0.25,
            is_terminal=False,
        ),
        _StationProfile(
            name="Amidships",
            x_position=0.50 * p.loa,
            half_beam_at_top=half_beam_amidships,
            half_beam_at_bottom=half_beam_amidships * 0.40,
            keel_depth=keel_depth_amidships,
            freeboard=p.freeboard,
            is_terminal=False,
        ),
        _StationProfile(
            name="Fwd",
            x_position=0.75 * p.loa,
            half_beam_at_top=half_beam_fwd,
            half_beam_at_bottom=half_beam_fwd * 0.30,
            keel_depth=keel_depth_fwd,
            freeboard=p.sheer_height_aft + (p.sheer_height_fwd - p.sheer_height_aft) * 0.75,
            is_terminal=False,
        ),
        _StationProfile(
            name="Stem",
            x_position=p.loa,
            half_beam_at_top=half_beam_stem,
            half_beam_at_bottom=half_beam_stem,  # constant — stem face is a rectangle
            keel_depth=keel_depth_stem,
            freeboard=p.sheer_height_fwd,
            is_terminal=False,  # spec 007: stem is now finite, not a vertex
            stem_rake_angle_deg=p.stem_rake_angle,
        ),
    ]


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

    Per data-model §5 + §6 (spec 006) + §5/§6 (spec 007). The sketch attaches
    to ``datum`` (a PartDesign::Plane). Sketch local x-axis maps to the Body's
    Y-axis (transverse beam); local y-axis maps to the Body's Z-axis (vertical).

    Every station — including Stem — is a closed 5-line-segment pentagon
    with vertices: keel-centerline (0, -keel_depth), bottom-outer
    (half_beam_at_bottom, -keel_depth * 0.6), top-outer (half_beam_at_top, 0),
    outer-sheer (half_beam_at_top, freeboard), centerline-deck (0, freeboard).

    Stem's blunt 80mm face (FR-003) is achieved via half_beam_at_top =
    half_beam_at_bottom = 0.040 m; the small ``keel_depth_stem`` forefoot
    (~80mm, set in :func:`_compute_stations`) keeps the pentagon
    topologically 5-vertex so PartDesign::AdditiveLoft can map vertices
    1:1 across all stations without twisting. The quarter-circle bilge
    arc transition is deferred to v1.1+.
    """
    import FreeCAD
    import Part
    import Sketcher

    sketch_name = f"HullStation{profile.name}"
    sketch = body.newObject("Sketcher::SketchObject", sketch_name)
    sketch.AttachmentSupport = [(datum, "")]
    sketch.MapMode = "FlatFace"

    # Scale meters → mm (FreeCAD's internal unit).
    keel_depth_mm = profile.keel_depth * _MM_PER_M
    half_beam_top_mm = profile.half_beam_at_top * _MM_PER_M
    half_beam_bottom_mm = profile.half_beam_at_bottom * _MM_PER_M
    freeboard_mm = profile.freeboard * _MM_PER_M

    pts = [
        FreeCAD.Vector(0.0, -keel_depth_mm, 0.0),
        FreeCAD.Vector(half_beam_bottom_mm, -keel_depth_mm * 0.6, 0.0),
        FreeCAD.Vector(half_beam_top_mm, 0.0, 0.0),
        FreeCAD.Vector(half_beam_top_mm, freeboard_mm, 0.0),
        FreeCAD.Vector(0.0, freeboard_mm, 0.0),
    ]

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


def _apply_loft_and_mirror(body: Any, sketches: list[Any]) -> tuple[Any, Any]:
    """Build the PartDesign feature stack: AdditiveLoft + Mirrored.

    Spec 007 R6: builds the AdditiveLoft with ``Ruled=True`` (piecewise-
    linear surfaces between station pairs). The smooth B-spline alternative
    (``Ruled=False``) is deferred to v1.1+ — with only 5 stations, the
    B-spline interpolation overshoots between the wide amidships and the
    narrow stem, producing surfaces that bulge well beyond the profile
    vertices. A future denser station set (≥8 stations) will constrain
    the B-spline; see spec.allium ``deferred Hull.b_spline_loft``.

    The mirror feature reflects the loft across the Body's XZ plane,
    producing the closed full-hull solid. ``Body.Tip`` is set to the mirror.

    Returns ``(loft, mirror)`` so the caller can register both features in
    the rollback list (FR-012).
    """
    loft = _build_loft(body, sketches, ruled=True)
    body.Document.recompute()

    mirror = body.newObject("PartDesign::Mirrored", "HullMirror")
    mirror.Originals = [loft]
    mirror.MirrorPlane = (_get_origin_plane(body, "XZ_Plane"), [""])

    body.Tip = mirror
    return (loft, mirror)


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
# Public builder (FR-001 + contracts/python-api.md)
# ---------------------------------------------------------------------------


def build_hull(
    parameters: HullParameters | None = None,
    *,
    document: Any = None,
    name: str = "Hull",
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
    """
    # Lazy first-call version check (FR-013 / research.md R6).
    from storebro._freecad_check import ensure_supported_freecad

    ensure_supported_freecad()

    # Validate parameters (FR-004). __post_init__ already validated, but
    # callers can subclass HullParameters and bypass __post_init__; defend
    # against that by re-validating on entry.
    resolved_params = parameters if parameters is not None else HullParameters()
    _validate_hull_parameters(resolved_params)

    # Resolve document (FR-016).
    target_doc = _resolve_document(document)
    body_label = _resolve_body_label(name)

    started = time.perf_counter()
    added: list[Any] = []
    try:
        body = target_doc.addObject("PartDesign::Body", "HullBody")
        added.append(body)
        body.Label = body_label

        # Recompute once now so the auto-created Origin's reference planes
        # are populated and accessible via body.Origin.OriginFeatures before
        # we attach datums/sketches to them.
        target_doc.recompute()

        _bind_parameters_to_body_properties(body, resolved_params)

        sketches: list[Any] = []
        for profile in _compute_stations(resolved_params):
            datum = _create_datum_plane(profile, body)
            added.append(datum)
            sketch = _create_station_sketch(profile, body, datum)
            added.append(sketch)
            sketches.append(sketch)

        loft, mirror = _apply_loft_and_mirror(body, sketches)
        added.extend([loft, mirror])

        target_doc.recompute()
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

    duration = time.perf_counter() - started
    return Hull(
        body=body,
        parameters=resolved_params,
        document=target_doc,
        label=body.Label,
        build_duration_seconds=duration,
    )
