"""Geometry test: single-screw produces exactly one of each component (T020, US1).

Covers spec 014 FR-001, FR-006, SC-002.
"""

from __future__ import annotations

from storebro import build_deck, build_hull, build_propulsion
from storebro.propulsion import PropulsionParameters


def test_single_screw_one_of_each(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    params = PropulsionParameters(engine_count=1, engine_offset_y_mm=0.0)
    prop = build_propulsion(hull, deck, parameters=params)

    assert len(prop.engine_beds) == 1
    assert len(prop.engines) == 1
    assert len(prop.shafts) == 1
    assert len(prop.propellers) == 1
    assert len(prop.rudders) == 1  # rudder_count resolves to engine_count
    assert prop.hull_modified is False


def test_single_screw_centreline(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    prop = build_propulsion(
        hull, deck, parameters=PropulsionParameters(engine_count=1, engine_offset_y_mm=0.0)
    )
    # The single shaft sits on the centreline (Y bbox centre ~ 0).
    centre = prop.shafts[0].body.Shape.BoundBox.Center
    assert abs(centre.y) < 5.0


def test_hull_only_no_deck(freecad_doc: object) -> None:
    """deck omitted: engine ceiling falls back to the hull sheer; build succeeds."""
    hull = build_hull(document=freecad_doc)
    prop = build_propulsion(
        hull, parameters=PropulsionParameters(engine_count=1, engine_offset_y_mm=0.0)
    )
    assert len(prop.engines) == 1
    assert prop.engines[0].within_hull_envelope is True
