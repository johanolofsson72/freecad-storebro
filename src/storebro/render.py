"""Spec 015 — cosmetic render attributes (colours + materials).

Assigns deterministic, role-keyed colours and named materials to the bodies the
library produces, so a built ``.FCStd`` reads as a real Storebro: gelcoat-white
hull, teak-brown trim, chromed hardware, translucent glass, bronze propeller,
dark engine.

Design (constitution II + III):

* The palette and role resolution are **pure Python** — this module imports no
  FreeCAD at module scope, so :data:`PALETTE` and :func:`role_for_label` are
  unit-testable on any host. ``import FreeCAD`` is not needed at all; the
  applier only touches the objects it is handed.
* Each object carries its appearance as **custom App data properties** in a
  ``"Render"`` group — ``App::PropertyColor`` ``RenderColor`` (RGBA),
  ``App::PropertyMaterial`` ``RenderMaterial`` (diffuse colour + transparency),
  and ``App::PropertyString`` ``RenderMaterialName`` (the human material name).
  These persist headless in ``Document.xml`` (verified on FreeCAD 1.1.1; the
  GUI's view-provider colours live in ``GuiDocument.xml`` which a headless build
  cannot emit). RGBA round-trips through deterministic 8-bit-per-channel
  quantisation, so identical inputs yield byte-identical output (FR-004).
* When (and only when) a live ``ViewObject`` is present (a GUI session), the
  applier also mirrors the colour + transparency to it so the GUI renders
  (FR-006). Headless, ``ViewObject`` is ``None`` and that branch is skipped.

Geometry is never touched: ``.Shape`` is left untouched on every object
(FR-011).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

__all__ = [
    "PALETTE",
    "RenderAttribute",
    "apply_render_attributes",
    "role_for_label",
]

# RGBA, each channel in [0, 1].
RGBA = tuple[float, float, float, float]

_RENDER_GROUP = "Render"


@dataclass(frozen=True)
class RenderAttribute:
    """The cosmetic appearance of one body role: an RGBA colour + material name.

    Carries no geometric meaning. ``color`` alpha < 1.0 marks translucency.

    Example:
        >>> RenderAttribute((0.93, 0.93, 0.88, 1.0), "gelcoat_white").material
        'gelcoat_white'
    """

    color: RGBA
    material: str

    def __post_init__(self) -> None:
        if len(self.color) != 4:
            raise ValueError(f"color must be a 4-tuple RGBA, got {self.color!r}")
        for channel in self.color:
            if not 0.0 <= channel <= 1.0:
                raise ValueError(f"color channel out of range [0, 1]: {channel!r}")
        if not self.material:
            raise ValueError("material name must be a non-empty string")


# ---------------------------------------------------------------------------
# Palette — the single source of truth (FR-002, FR-003). role -> attribute.
# RGBA values tuned to the docs/references/ Storebro appearance; exact hex is
# an implementation detail, the role intent is the spec.
# ---------------------------------------------------------------------------

PALETTE: dict[str, RenderAttribute] = {
    "hull": RenderAttribute((0.93, 0.93, 0.88, 1.0), "gelcoat_white"),
    "superstructure": RenderAttribute((0.95, 0.95, 0.93, 1.0), "gelcoat_white"),
    "frame": RenderAttribute((0.25, 0.25, 0.28, 1.0), "frame_alloy"),
    "glass": RenderAttribute((0.60, 0.72, 0.80, 0.35), "glass"),
    "trim": RenderAttribute((0.55, 0.32, 0.16, 1.0), "teak"),
    "metal": RenderAttribute((0.78, 0.80, 0.83, 1.0), "chrome"),
    "bulkhead": RenderAttribute((0.88, 0.86, 0.80, 1.0), "paint_white"),
    "engine": RenderAttribute((0.20, 0.27, 0.24, 1.0), "engine_enamel"),
    "steel": RenderAttribute((0.62, 0.64, 0.67, 1.0), "steel"),
    "bronze": RenderAttribute((0.72, 0.52, 0.26, 1.0), "bronze"),
    "DEFAULT": RenderAttribute((0.70, 0.70, 0.70, 1.0), "default"),
}

# Ordered, most-specific-first: the first prefix that matches a body's Label
# wins, so "Deck_WindshieldGlass" resolves to glass before "Deck_Windshield"
# resolves to frame, and "Deck_Rubrail" is trim, not metal. FreeCAD label
# auto-numbering (e.g. twin "Propulsion_Engine001") is handled by startswith.
# NB: interior bulkheads are nested inside compartment compounds, not top-level
# objects, so the "bulkhead" role is reached only by a hypothetical "Bulkhead*"
# top-level label; compartment compounds resolve to trim (teak joinery).
_ROLE_RULES: tuple[tuple[str, str], ...] = (
    ("Deck_WindshieldGlass", "glass"),
    ("Deck_CabinWindowGlass", "glass"),
    ("Deck_DeckhouseWindowGlass", "glass"),
    ("Hull_PortholeGlass", "glass"),
    ("Deck_Windshield", "frame"),
    ("Deck_Rubrail", "trim"),
    ("Deck_Railings", "metal"),
    ("Deck_BowPulpit", "metal"),
    ("Deck_Cleat", "metal"),
    ("Deck_Lifelines", "metal"),
    ("Deck_HardtopPillars", "metal"),
    ("Deck_Pillar", "metal"),
    ("Deck_DeckPlate", "superstructure"),
    ("Deck_CabinTrunk", "superstructure"),
    ("Deck_Deckhouse", "superstructure"),
    ("Deck_Hardtop", "superstructure"),
    ("Deck_AnchorLocker", "superstructure"),
    ("HullBody", "hull"),
    ("Bulkhead", "bulkhead"),
    ("Interior_", "trim"),
    ("Propulsion_EngineBed", "engine"),
    ("Propulsion_Engine", "engine"),
    ("Propulsion_Shaft", "steel"),
    ("Propulsion_Propeller", "bronze"),
    ("Propulsion_Rudder", "bronze"),
)


def role_for_label(label: str) -> str:
    """Resolve a body identifier (``Name`` or ``Label``) to a palette role key.

    Always returns a key present in :data:`PALETTE`; unmatched identifiers map
    to ``"DEFAULT"`` (FR-010). Pure function — no FreeCAD dependency.

    Example:
        >>> role_for_label("Deck_WindshieldGlass")
        'glass'
        >>> role_for_label("Deck_Windshield")
        'frame'
        >>> role_for_label("Propulsion_Propeller")
        'bronze'
        >>> role_for_label("something_unmapped")
        'DEFAULT'
    """
    for prefix, role in _ROLE_RULES:
        if label.startswith(prefix):
            return role
    return "DEFAULT"


def _role_for_object(obj: Any) -> str:
    """Resolve an object's role from its FreeCAD ``Name`` first, then ``Label``.

    The construction-time ``Name`` (e.g. ``HullBody``, ``Deck_CabinTrunk``,
    ``Propulsion_Engine``) is the canonical role string — it survives even when
    the user-facing ``Label`` is renamed (``build_hull(name=...)`` leaves the
    ``Name`` as ``HullBody`` but the ``Label`` becomes ``"Hull"``). The first
    identifier that resolves to a non-DEFAULT role wins.
    """
    for key in (getattr(obj, "Name", "") or "", getattr(obj, "Label", "") or ""):
        role = role_for_label(key)
        if role != "DEFAULT":
            return role
    return "DEFAULT"


# ---------------------------------------------------------------------------
# Applier (FR-001, FR-005, FR-006, FR-011)
# ---------------------------------------------------------------------------


def _ensure_property(obj: Any, prop_type: str, name: str, doc: str) -> None:
    """Add a custom data property in the Render group if it is not present."""
    if name not in obj.PropertiesList:
        obj.addProperty(prop_type, name, _RENDER_GROUP, doc)


def _apply_to_object(obj: Any, attr: RenderAttribute) -> None:
    """Persist colour + material as data properties; bridge the ViewObject."""
    _ensure_property(obj, "App::PropertyColor", "RenderColor", "Cosmetic render colour (RGBA)")
    obj.RenderColor = attr.color

    _ensure_property(obj, "App::PropertyMaterial", "RenderMaterial", "Render material")
    material = obj.RenderMaterial
    material.DiffuseColor = attr.color
    material.Transparency = 1.0 - attr.color[3]
    obj.RenderMaterial = material

    _ensure_property(obj, "App::PropertyString", "RenderMaterialName", "Render material name")
    obj.RenderMaterialName = attr.material

    # Best-effort GUI bridge (FR-006): None in console mode → skipped.
    view = getattr(obj, "ViewObject", None)
    if view is not None:
        try:
            view.ShapeColor = attr.color[:3]
            view.Transparency = round((1.0 - attr.color[3]) * 100)
        except Exception:
            # A quirky view provider must never break the geometry build.
            pass


def apply_render_attributes(objects: Iterable[Any], *, enabled: bool = True) -> int:
    """Assign role-keyed colour + material to each given FreeCAD object.

    Args:
        objects: iterable of top-level shape-bearing FreeCAD objects (the
            bodies in a ``build_*`` aggregate). ``None`` entries are skipped.
        enabled: when ``False`` this is a no-op (returns 0) and objects keep
            FreeCAD's default appearance (FR-009).

    Returns:
        The number of objects to which attributes were applied.

    Never mutates ``.Shape`` (FR-011). Idempotent — re-applying the same palette
    yields identical stored values.

    Example:
        >>> # apply_render_attributes([hull.body, deck.deck_plate.body])
        >>> apply_render_attributes([], enabled=False)
        0
    """
    if not enabled:
        return 0
    count = 0
    for obj in objects:
        if obj is None:
            continue
        attr = PALETTE[_role_for_object(obj)]
        _apply_to_object(obj, attr)
        count += 1
    return count
