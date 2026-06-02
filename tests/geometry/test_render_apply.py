"""Geometry tests: render attributes applied + persisted (spec 015 T010).

Covers FR-001, FR-005, FR-010, FR-014 and contract invariants 1-2, 7-8 against a
real built model. Requires FreeCAD (auto-marked requires_freecad).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import FreeCAD  # type: ignore[import-not-found]

from storebro import (
    PALETTE,
    apply_render_attributes,
    build_deck,
    build_hull,
    build_interior,
    build_propulsion,
    export_fcstd,
    role_for_label,
)


def _quantized(color: tuple[float, ...]) -> tuple[int, ...]:
    """FreeCAD stores colour as 8-bit per channel; compare on that grid."""
    return tuple(round(c * 255) for c in color)


def test_hull_body_carries_gelcoat_color(freecad_doc: Any) -> None:
    hull = build_hull(document=freecad_doc)
    assert "RenderColor" in hull.body.PropertiesList
    assert _quantized(hull.body.RenderColor) == _quantized(PALETTE["hull"].color)
    assert hull.body.RenderMaterialName == "gelcoat_white"


def test_every_deck_body_is_coloured(freecad_doc: Any) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    bodies = [
        deck.deck_plate.body,
        deck.cabin_trunk.body,
        deck.windshield.body,
        deck.hardtop.body,
        deck.hardtop_pillars.body,
        deck.railings.body,
        deck.rubrail.body,
        deck.bow_pulpit.body,
        deck.lifelines.body,
        deck.anchor_locker.body,
        deck.cleats.body,
    ]
    for body in bodies:
        assert "RenderColor" in body.PropertiesList, body.Label
        expected = PALETTE[role_for_label(body.Label)]
        assert _quantized(body.RenderColor) == _quantized(expected.color), body.Label
        assert body.RenderMaterialName == expected.material, body.Label


def test_rubrail_is_teak_and_railings_metal(freecad_doc: Any) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    assert deck.rubrail.body.RenderMaterialName == "teak"
    assert deck.railings.body.RenderMaterialName == "chrome"


def test_windshield_glass_is_translucent(freecad_doc: Any) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    glass = deck.windshield.glass_pane
    assert glass is not None
    assert glass.body.RenderColor[3] < 1.0
    assert glass.body.RenderMaterialName == "glass"
    # The material transparency derives from alpha.
    assert glass.body.RenderMaterial.Transparency > 0.0


def test_interior_compartments_are_teak(freecad_doc: Any) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout="Alternativ3")
    assert interior.compartments
    for comp in interior.compartments:
        assert comp.body.RenderMaterialName == "teak", comp.body.Label


def test_propulsion_bodies_coloured_by_role(freecad_doc: Any) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    prop = build_propulsion(hull, deck)
    for engine in prop.engines:
        assert engine.body.RenderMaterialName == "engine_enamel"
    for shaft in prop.shafts:
        assert shaft.body.RenderMaterialName == "steel"
    for propeller in prop.propellers:
        assert propeller.body.RenderMaterialName == "bronze"
    for rudder in prop.rudders:
        assert rudder.body.RenderMaterialName == "bronze"


def test_unmatched_label_gets_default(freecad_doc: Any) -> None:
    obj = freecad_doc.addObject("Part::Feature", "TotallyUnknownThing")
    applied = apply_render_attributes([obj], enabled=True)
    assert applied == 1
    assert _quantized(obj.RenderColor) == _quantized(PALETTE["DEFAULT"].color)
    assert obj.RenderMaterialName == "default"


def test_attributes_survive_save_reload(freecad_doc: Any, tmp_path: Path) -> None:
    hull = build_hull(document=freecad_doc)
    expected = _quantized(hull.body.RenderColor)
    out = tmp_path / "persist.FCStd"
    export_fcstd(hull.document, str(out))
    reopened = FreeCAD.openDocument(str(out))
    try:
        body = next(o for o in reopened.Objects if o.Label == hull.body.Label)
        assert "RenderColor" in body.PropertiesList
        # Persisted colour round-trips through 8-bit quantisation; the rounding
        # direction at a .5 boundary is a FreeCAD detail, so allow ±1 per channel.
        reloaded = _quantized(body.RenderColor)
        assert all(abs(a - b) <= 1 for a, b in zip(reloaded, expected, strict=True))
        assert body.RenderMaterialName == "gelcoat_white"
    finally:
        FreeCAD.closeDocument(reopened.Name)
