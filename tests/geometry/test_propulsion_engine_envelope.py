"""Geometry test: engine sits inside the hull envelope, no pierce (T023, US1).

Covers spec 014 FR-005, SC-004 + spec.allium SeatedAndContained.
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull, build_propulsion
from storebro.propulsion import (
    EngineParameters,
    PropulsionParameterError,
    PropulsionParameters,
    _hull_half_beam_at,
)


def test_engine_within_envelope_flags(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    prop = build_propulsion(hull, deck)
    for engine in prop.engines:
        assert engine.rests_on_bed is True
        assert engine.within_hull_envelope is True
        assert engine.pierces_hull_shell is False


def test_engine_bbox_inboard_of_half_beam(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    prop = build_propulsion(hull, deck)
    station = prop.parameters.engine.station_x_mm
    half_beam = _hull_half_beam_at(hull, station)
    for engine in prop.engines:
        bb = engine.body.Shape.BoundBox
        assert max(abs(bb.YMin), abs(bb.YMax)) <= half_beam + 1.0


def test_engine_offset_past_topside_rejected(freecad_doc: object) -> None:
    """An engine pushed outboard past the sampled half-beam is rejected."""
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    huge = PropulsionParameters(
        engine_count=2,
        engine_offset_y_mm=5000.0,
        engine=EngineParameters(),
    )
    with pytest.raises(PropulsionParameterError) as exc:
        build_propulsion(hull, deck, parameters=huge)
    assert exc.value.parameter_name == "engine_offset_y_mm"
