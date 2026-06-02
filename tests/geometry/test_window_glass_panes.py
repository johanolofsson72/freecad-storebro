"""Geometry test: spec 019 translucent glass panes (FR-001..FR-007).

Requires FreeCAD. Panes are additive bodies discoverable in the document by
Name; the host hull/trunk/deckhouse solids stay single manifold solids.
"""

from __future__ import annotations

from storebro import build_deck, build_hull
from storebro.deck import DeckGlazingParameters, DeckhouseParameters, DsWindowParameters
from storebro.hull import HullGlazingParameters, HullParameters
from storebro.render import role_for_label


def _bodies(doc: object, prefix: str) -> list:
    # Only the pane Bodies themselves — not their child Datum/Sketch/Pad
    # features (which share the body's Name prefix).
    return [
        o
        for o in doc.Objects  # type: ignore[attr-defined]
        if o.Name.startswith(prefix) and o.isDerivedFrom("PartDesign::Body")
    ]


def test_portholes_get_glass_discs(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    panes = _bodies(freecad_doc, "Hull_PortholeGlass")
    assert len(panes) == hull.portholes.count  # one disc per porthole
    for g in panes:
        assert len(g.Shape.Solids) == 1 and g.Shape.isValid()
    # Host hull untouched.
    assert len(hull.body.Shape.Solids) == 1 and hull.body.Shape.isValid()


def test_portholes_glass_off(freecad_doc: object) -> None:
    hull = build_hull(
        document=freecad_doc,
        parameters_glazing=HullGlazingParameters(glass_panes=False),
    )
    assert _bodies(freecad_doc, "Hull_PortholeGlass") == []
    assert len(hull.body.Shape.Solids) == 1  # host unchanged


def test_cabin_windows_get_glass(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    panes = _bodies(freecad_doc, "Deck_CabinWindowGlass")
    assert deck.cabin_windows is not None
    assert len(panes) == deck.cabin_windows.count
    for g in panes:
        assert len(g.Shape.Solids) == 1 and g.Shape.isValid()
    assert deck.cabin_trunk is not None
    assert len(deck.cabin_trunk.body.Shape.Solids) == 1


def test_deckhouse_windows_get_glass(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull, superstructure_variant="ds")
    panes = _bodies(freecad_doc, "Deck_DeckhouseWindowGlass")
    assert deck.deckhouse is not None
    assert len(panes) == deck.deckhouse.window_count
    for g in panes:
        assert len(g.Shape.Solids) == 1 and g.Shape.isValid()
    assert len(deck.deckhouse.body.Shape.Solids) == 1  # host unchanged


def test_panes_resolve_to_glass_role() -> None:
    # Pure (no FreeCAD): the new glass body names map to the translucent role.
    assert role_for_label("Hull_PortholeGlassPort1") == "glass"
    assert role_for_label("Deck_CabinWindowGlassPort1") == "glass"
    assert role_for_label("Deck_DeckhouseWindowGlassPort1") == "glass"
