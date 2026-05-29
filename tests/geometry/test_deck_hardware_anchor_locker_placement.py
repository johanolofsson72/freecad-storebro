"""Geometry test: anchor locker placement + rejection paths (T020, T021).

Covers spec 010 FR-008, FR-018 + spec.allium ForwardAndInFootprint.
Coordinate convention: bow = XMax, stern = XMin; the foredeck is the high-X
region forward of the cabin trunk's XMax edge.
"""

from __future__ import annotations

import pytest

from storebro import (
    AnchorLockerParameters,
    DeckHardwareParameters,
    build_deck,
    build_hull,
)
from storebro.deck import DeckParameterError


@pytest.mark.requires_freecad
def test_anchor_locker_forward_of_cabin_trunk(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    locker_bb = deck.anchor_locker.body.Shape.BoundBox
    cabin_bb = deck.cabin_trunk.body.Shape.BoundBox
    # Locker's stern edge (XMin) is forward of the cabin's bow edge (XMax).
    assert locker_bb.XMin >= cabin_bb.XMax - 1.0


@pytest.mark.requires_freecad
def test_anchor_locker_within_deck_footprint(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    locker_bb = deck.anchor_locker.body.Shape.BoundBox
    deck_bb = deck.deck_plate.body.Shape.BoundBox
    assert locker_bb.XMax <= deck_bb.XMax + 1.0
    assert locker_bb.XMin >= deck_bb.XMin - 1.0


@pytest.mark.requires_freecad
def test_anchor_locker_overlapping_cabin_trunk_rejected(freecad_doc: object) -> None:
    """FR-018: a locker placed over the cabin trunk is rejected (rollback)."""
    hull = build_hull(document=freecad_doc)
    # center_x deep inside the cabin trunk footprint (cabin ~ X[350, 4950]).
    hw = DeckHardwareParameters(anchor_locker=AnchorLockerParameters(center_x=2000.0))
    objects_before = [obj.Name for obj in freecad_doc.Objects]
    with pytest.raises(DeckParameterError) as exc:
        build_deck(hull, parameters_hardware=hw)
    assert exc.value.parameter_name == "anchor_locker_center_x<>cabin_trunk"
    # Rollback leaves no orphans.
    assert [obj.Name for obj in freecad_doc.Objects] == objects_before


@pytest.mark.requires_freecad
def test_anchor_locker_past_deck_bow_edge_rejected(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    # center_x past the stem so the bow edge exceeds the deck.
    hw = DeckHardwareParameters(anchor_locker=AnchorLockerParameters(center_x=20000.0))
    with pytest.raises(DeckParameterError) as exc:
        build_deck(hull, parameters_hardware=hw)
    assert exc.value.parameter_name == "anchor_locker_center_x<>deck_forward_edge"
