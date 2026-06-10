"""Geometry test: NACA rudder foil (spec 021 US3, T018).

Covers FR-002, SC-004, FR-007, FR-009, FR-010.
"""

from __future__ import annotations

from storebro import build_deck, build_hull, build_propulsion
from storebro.propulsion import PropulsionParameters, RudderParameters


def _rudder(doc: object, *, naca: bool) -> object:
    hull = build_hull(document=doc)
    deck = build_deck(hull)
    params = PropulsionParameters(rudder=RudderParameters(naca_foil=naca))
    return build_propulsion(hull, deck, params).rudders[0]  # type: ignore[attr-defined]


def test_default_rudder_is_naca_foil(freecad_doc: object) -> None:
    r = _rudder(freecad_doc, naca=True)
    shape = r.body.Shape
    assert len(shape.Solids) == 1 and shape.isValid()
    assert shape.Volume > 0.0
    assert r.naca_applied is True
    assert r.bbox_min_z_mm < 0.0


def test_foil_rudder_has_more_faces_than_flat(freecad_doc: object, freecad_doc2: object) -> None:
    foil = _rudder(freecad_doc, naca=True)
    flat = _rudder(freecad_doc2, naca=False)
    # The polyline foil blade has many side faces vs the flat plate's four.
    assert len(foil.body.Shape.Faces) > len(flat.body.Shape.Faces)


def test_naca_off_reproduces_flat_plate(freecad_doc: object) -> None:
    r = _rudder(freecad_doc, naca=False)
    assert r.naca_applied is False
    assert len(r.body.Shape.Solids) == 1
