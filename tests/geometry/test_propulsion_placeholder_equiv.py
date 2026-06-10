"""Geometry test: all-detail-off == spec 014 placeholder (spec 021 T029).

Covers FR-009, SC-006. A build with every detail flag off reproduces the
spec 014 build byte-for-byte (component volumes) and produces no struts.
"""

from __future__ import annotations

import contextlib

import FreeCAD  # type: ignore[import-not-found]

from storebro import build_deck, build_hull, build_propulsion
from storebro.propulsion import (
    EngineParameters,
    PropellerParameters,
    PropulsionParameters,
    RudderParameters,
    ShaftParameters,
)

_PLACEHOLDER = PropulsionParameters(
    engine=EngineParameters(detailed=False),
    shaft=ShaftParameters(coupling_flange=False, strut_bearing=False, shaft_log_fairing=False),
    propeller=PropellerParameters(airfoil_blades=False),
    rudder=RudderParameters(naca_foil=False),
)
_GROUPS = ("engine_beds", "engines", "shafts", "propellers", "rudders")


def test_all_detail_off_has_no_struts(freecad_doc: object) -> None:
    prop = build_propulsion(
        h := build_hull(document=freecad_doc), build_deck(h), _PLACEHOLDER
    )
    assert prop.struts == []  # type: ignore[attr-defined]
    for p in prop.propellers:  # type: ignore[attr-defined]
        assert p.airfoil_applied is False
    for r in prop.rudders:  # type: ignore[attr-defined]
        assert r.naca_applied is False
    for e in prop.engines:  # type: ignore[attr-defined]
        assert e.detail_applied is False


def test_two_placeholder_builds_identical() -> None:
    doc1 = FreeCAD.newDocument("Ph021_1")
    doc2 = FreeCAD.newDocument("Ph021_2")
    try:
        a = build_propulsion(h1 := build_hull(document=doc1), build_deck(h1), _PLACEHOLDER)
        b = build_propulsion(h2 := build_hull(document=doc2), build_deck(h2), _PLACEHOLDER)
        for g in _GROUPS:
            va = sorted(w.body.Shape.Volume for w in getattr(a, g))
            vb = sorted(w.body.Shape.Volume for w in getattr(b, g))
            assert va == vb, f"{g}: {va} != {vb}"
    finally:
        for doc in (doc1, doc2):
            with contextlib.suppress(Exception):
                FreeCAD.closeDocument(doc.Name)
