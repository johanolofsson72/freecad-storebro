"""Geometry test: rubrail follows the sampled sheer (T013).

Covers spec 010 FR-004, FR-005, SC-002 + spec.allium RubrailsFollowSheer.
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull
from storebro.deck import _resolve_deck_top_z_at, _sheer_samples_mm

SHEER_TOLERANCE_MM = 1.0


@pytest.mark.requires_freecad
def test_rubrail_spans_majority_of_loa(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    bb = deck.rubrail.body.Shape.BoundBox
    deck_bb = deck.deck_plate.body.Shape.BoundBox
    span = bb.XMax - bb.XMin
    deck_span = deck_bb.XMax - deck_bb.XMin
    assert span >= 0.80 * deck_span, (
        f"FR-005: rubrail spans {span:.0f} mm of {deck_span:.0f} mm deck (< 80%)"
    )


@pytest.mark.requires_freecad
def test_rubrail_top_tracks_sheer_z_at_each_station(freecad_doc: object) -> None:
    """SC-002: rubrail centerline Z at each sampled station is on the sheer."""
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    rp = deck.parameters_hardware.rubrail
    half_h = rp.height  # mm; allow one full height of slack (centerline vs. top)

    # Collect per-side rubrail bodies via the compound's child shapes.
    rubrail_shape = deck.rubrail.body.Shape
    for x_mm, _y, _z in _sheer_samples_mm(hull):
        if not (rp.forward_x <= x_mm <= rp.aft_x):
            continue
        expected_z = _resolve_deck_top_z_at(deck.deck_plate, x_mm)
        # Vertices of the rubrail near this X station.
        near = [v for v in rubrail_shape.Vertexes if abs(v.X - x_mm) < 200.0]
        if not near:
            continue
        zs = [v.Z for v in near]
        # The rubrail strip straddles the sheer Z within ±height.
        assert min(zs) <= expected_z + half_h
        assert max(zs) >= expected_z - half_h


@pytest.mark.requires_freecad
def test_rubrail_present_on_both_sides(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    bb = deck.rubrail.body.Shape.BoundBox
    assert bb.YMax > 0.0 and bb.YMin < 0.0, "rubrail must exist port and starboard"
