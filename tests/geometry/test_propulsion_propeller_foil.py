"""Geometry test: airfoil propeller blades (spec 021 US1, T011).

Covers FR-001, SC-003, FR-007, FR-009, FR-010, FR-013 + spec.allium
FoilWhenApplied / DetailedPropellersAreFoilOrFellBack.
"""

from __future__ import annotations

from storebro import build_deck, build_hull, build_propulsion
from storebro.propulsion import PropellerParameters, PropulsionParameters


def _prop(doc: object, *, airfoil: bool) -> object:
    hull = build_hull(document=doc)
    deck = build_deck(hull)
    params = PropulsionParameters(propeller=PropellerParameters(airfoil_blades=airfoil))
    return build_propulsion(hull, deck, params)


def test_default_propeller_is_foil_and_twisted(freecad_doc: object) -> None:
    prop = _prop(freecad_doc, airfoil=True)
    assert prop.propellers, "expected at least one propeller"  # type: ignore[attr-defined]
    for p in prop.propellers:  # type: ignore[attr-defined]
        shape = p.body.Shape
        assert len(shape.Solids) == 1 and shape.isValid()
        assert shape.Volume > 0.0
        assert p.body.TypeId == "PartDesign::Body"  # FR-013
        assert p.airfoil_applied is True
        assert p.root_to_tip_twist_deg != 0.0  # SC-003 non-zero twist
        assert p.blade_count == p.parameters.blade_count


def test_foil_blade_has_more_faces_than_flat(freecad_doc2: object, freecad_doc: object) -> None:
    foil = _prop(freecad_doc, airfoil=True)
    flat = _prop(freecad_doc2, airfoil=False)
    foil_faces = len(foil.propellers[0].body.Shape.Faces)  # type: ignore[attr-defined]
    flat_faces = len(flat.propellers[0].body.Shape.Faces)  # type: ignore[attr-defined]
    # A lofted polyline foil blade has many side faces; the spec 014 flat blade
    # is a simple rectangular pad with few — the foil is unambiguously richer.
    assert foil_faces > flat_faces


def test_airfoil_off_reproduces_spec014_flat_blade(freecad_doc: object) -> None:
    prop = _prop(freecad_doc, airfoil=False)
    for p in prop.propellers:  # type: ignore[attr-defined]
        assert p.airfoil_applied is False
        assert p.root_to_tip_twist_deg == 0.0
        assert len(p.body.Shape.Solids) == 1


def test_propeller_below_waterline(freecad_doc: object) -> None:
    prop = _prop(freecad_doc, airfoil=True)
    for p in prop.propellers:  # type: ignore[attr-defined]
        assert p.bbox_min_z_mm < 0.0
