"""Geometry test: detailed diesel engine block (spec 021 US2, T015).

Covers FR-005, SC-005, FR-007, FR-009, FR-010 + spec.allium
DetailedEnginesStaySingleSolid / SeatedAndContained.
"""

from __future__ import annotations

from storebro import build_deck, build_hull, build_propulsion
from storebro.propulsion import EngineParameters, PropulsionParameters


def _engine(doc: object, **engine_kw: object) -> object:
    hull = build_hull(document=doc)
    deck = build_deck(hull)
    params = PropulsionParameters(engine=EngineParameters(**engine_kw))  # type: ignore[arg-type]
    return build_propulsion(hull, deck, params).engines[0]  # type: ignore[attr-defined]


def test_default_engine_is_detailed_and_manifold(freecad_doc: object) -> None:
    e = _engine(freecad_doc)
    shape = e.body.Shape
    assert len(shape.Solids) == 1 and shape.isValid()  # fused into one solid
    assert e.detail_applied is True
    assert e.within_hull_envelope is True
    assert e.pierces_hull_shell is False


def test_detailed_engine_more_articulated_than_box(
    freecad_doc: object, freecad_doc2: object
) -> None:
    detailed = _engine(freecad_doc)
    plain = _engine(freecad_doc2, detailed=False)
    bb_d = detailed.body.Shape.BoundBox
    bb_p = plain.body.Shape.BoundBox
    # Sump drops the bottom, head raises the top → the detailed body is taller.
    assert bb_d.ZLength > bb_p.ZLength
    # More faces (sump + head + stubs) than the plain six-face box.
    assert len(detailed.body.Shape.Faces) > len(plain.body.Shape.Faces)


def test_engine_detail_off_reproduces_box(freecad_doc: object) -> None:
    e = _engine(freecad_doc, detailed=False)
    assert e.detail_applied is False
    assert len(e.body.Shape.Faces) == 6  # plain rectangular box


def test_zero_stubs_still_manifold(freecad_doc: object) -> None:
    e = _engine(freecad_doc, manifold_stub_count=0)
    assert len(e.body.Shape.Solids) == 1 and e.body.Shape.isValid()
    assert e.detail_applied is True
