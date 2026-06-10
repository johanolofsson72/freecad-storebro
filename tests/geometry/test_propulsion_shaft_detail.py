"""Geometry test: shaft coupling flange + fairing (fused) + strut (separate body).

Spec 021 US4 + US5 (T022, T024). Covers FR-003, FR-004, FR-006, FR-007, FR-009,
FR-013, SC-007 + spec.allium CouplingAndFairingFusedIntoShaft / HullNeverBooleaned.
"""

from __future__ import annotations

from storebro import build_deck, build_hull, build_propulsion
from storebro.propulsion import PropulsionParameters, ShaftParameters


def _build(doc: object, shaft: ShaftParameters) -> object:
    hull = build_hull(document=doc)
    deck = build_deck(hull)
    return build_propulsion(hull, deck, PropulsionParameters(shaft=shaft))


def test_coupling_and_fairing_fused_into_shaft(freecad_doc: object) -> None:
    prop = _build(freecad_doc, ShaftParameters())
    for s in prop.shafts:  # type: ignore[attr-defined]
        assert s.has_coupling_flange is True
        assert s.has_shaft_log_fairing is True
        shape = s.body.Shape
        assert len(shape.Solids) == 1 and shape.isValid()  # still one solid


def test_strut_is_separate_valid_body_reaching_up(freecad_doc: object) -> None:
    prop = _build(freecad_doc, ShaftParameters())
    assert prop.struts, "expected at least one strut body"  # type: ignore[attr-defined]
    for st in prop.struts:  # type: ignore[attr-defined]
        shape = st.body.Shape
        assert st.body.TypeId == "PartDesign::Body"  # FR-013, separate body
        assert len(shape.Solids) == 1 and shape.isValid()
        assert st.top_z_mm > st.bottom_z_mm  # arm reaches up toward the hull


def test_detail_off_reproduces_spec014_shaft_and_no_struts(freecad_doc: object) -> None:
    prop = _build(
        freecad_doc,
        ShaftParameters(coupling_flange=False, strut_bearing=False, shaft_log_fairing=False),
    )
    for s in prop.shafts:  # type: ignore[attr-defined]
        assert s.has_coupling_flange is False
        assert s.has_shaft_log_fairing is False
        assert len(s.body.Shape.Solids) == 1
    assert prop.struts == []  # type: ignore[attr-defined]


def test_hull_never_booleaned(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    vol_before = hull.body.Shape.Volume
    deck = build_deck(hull)
    prop = build_propulsion(hull, deck)
    assert prop.hull_modified is False  # type: ignore[attr-defined]
    assert hull.body.Shape.Volume == vol_before  # SC-007 — additive fairing only
