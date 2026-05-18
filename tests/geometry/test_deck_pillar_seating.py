"""Spec 008 FR-016/017/018/022 — pillar seating, symmetry, and railing port/starboard.

The headline correctness invariant of spec 008: every hardtop pillar's
lower endpoint Z must equal the deck plate top Z at that pillar's
longitudinal station within 1 mm. This is the explicit fix for the
v1.0.1 regression where pillars dropped through the hull into the cabin
cavity.

Also covers FR-017 (vertical centerline — pillar's Pad direction must be
strictly Z-axis) and FR-018/022 (symmetric port/starboard counts).
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull
from storebro.deck import _resolve_deck_top_z_at

SEATING_TOLERANCE_MM = 1.0


@pytest.mark.requires_freecad
def test_every_pillar_lower_endpoint_matches_deck_top_z(freecad_doc: object) -> None:
    """FR-016 + spec.allium NoPillarPiercesDeckPlate invariant."""
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    pillar_bodies = [
        obj
        for obj in deck.document.Objects
        if obj.Label.startswith("Deck_Pillar_")
    ]
    assert pillar_bodies, "FR-016: at least one pillar required on default parameters"
    for pillar in pillar_bodies:
        pillar_bb = pillar.Shape.BoundBox
        x_center = (pillar_bb.XMin + pillar_bb.XMax) / 2.0
        expected_top_z = _resolve_deck_top_z_at(deck.deck_plate, x_center)
        delta = pillar_bb.ZMin - expected_top_z
        assert abs(delta) <= SEATING_TOLERANCE_MM, (
            f"FR-016: pillar {pillar.Label} ZMin={pillar_bb.ZMin:.2f} mm but deck-top "
            f"at X={x_center:.1f} is {expected_top_z:.2f} mm (delta={delta:+.2f} mm "
            f"exceeds ±{SEATING_TOLERANCE_MM} mm tolerance)"
        )


@pytest.mark.requires_freecad
def test_no_pillar_geometry_below_deck_plate_top(freecad_doc: object) -> None:
    """FR-016 + spec.allium PillarsNeverPierceDeckPlate global invariant.

    Stronger than the per-pillar seating: NO vertex of any pillar may sit
    below the deck plate top at the pillar's longitudinal station — within
    the seating tolerance.
    """
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    pillar_bodies = [
        obj
        for obj in deck.document.Objects
        if obj.Label.startswith("Deck_Pillar_")
    ]
    for pillar in pillar_bodies:
        x_center = (pillar.Shape.BoundBox.XMin + pillar.Shape.BoundBox.XMax) / 2.0
        expected_top_z = _resolve_deck_top_z_at(deck.deck_plate, x_center)
        for v in pillar.Shape.Vertexes:
            assert expected_top_z - SEATING_TOLERANCE_MM <= v.Z, (
                f"FR-016: pillar {pillar.Label} vertex at "
                f"({v.X:.1f}, {v.Y:.1f}, {v.Z:.1f}) sits below deck top "
                f"{expected_top_z:.1f} at X={x_center:.1f}"
            )


@pytest.mark.requires_freecad
def test_pillar_pad_is_strictly_vertical(freecad_doc: object) -> None:
    """FR-017 — pillar centerline is parallel to global Z.

    The Pad feature inside each pillar Body has its direction along the
    sketch plane normal. Sketches are placed on XY-parallel datums whose
    normal is the global Z-axis, so the Pad direction is global Z by
    construction. Verify this by checking the BoundBox has nearly-zero
    spread in X and Y compared to its Z spread (pillar diameter is small;
    pillar height is large).
    """
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    pillar_bodies = [
        obj
        for obj in deck.document.Objects
        if obj.Label.startswith("Deck_Pillar_")
    ]
    for pillar in pillar_bodies:
        bb = pillar.Shape.BoundBox
        x_spread = bb.XMax - bb.XMin
        y_spread = bb.YMax - bb.YMin
        z_spread = bb.ZMax - bb.ZMin
        # Pillar diameter default is 35 mm; height is ~2 m. A vertical pillar
        # has x_spread ≈ y_spread ≈ diameter ≪ z_spread.
        assert z_spread > 5 * max(x_spread, y_spread), (
            f"FR-017: pillar {pillar.Label} is not strictly vertical — "
            f"X spread {x_spread:.1f}, Y spread {y_spread:.1f}, Z spread {z_spread:.1f}"
        )
        # Pad feature exists and Reversed=False.
        if pillar.Tip is not None and "Pad" in pillar.Tip.TypeId:
            assert pillar.Tip.Reversed is False, (
                f"FR-017: {pillar.Label} Pad.Reversed must be False (extrude in +Z)"
            )


@pytest.mark.requires_freecad
def test_pillar_count_matches_parameters(freecad_doc: object) -> None:
    """FR-015/018 — pillar count = count_per_side * 2, evenly split port/starboard."""
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    sp = deck.parameters.to_superstructure_parameters()
    port_count = len(
        [o for o in deck.document.Objects if o.Label.startswith("Deck_Pillar_Port_")]
    )
    starboard_count = len(
        [o for o in deck.document.Objects if o.Label.startswith("Deck_Pillar_Starboard_")]
    )
    expected = sp.pillars.count_per_side
    assert port_count == expected, (
        f"FR-018: expected {expected} port pillars, got {port_count}"
    )
    assert starboard_count == expected, (
        f"FR-018: expected {expected} starboard pillars, got {starboard_count}"
    )


@pytest.mark.requires_freecad
def test_pillars_symmetric_port_starboard_at_same_x(freecad_doc: object) -> None:
    """FR-018 — for each port pillar at X there is a matching starboard pillar at X."""
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    port_xs = sorted(
        round((o.Shape.BoundBox.XMin + o.Shape.BoundBox.XMax) / 2.0, 1)
        for o in deck.document.Objects
        if o.Label.startswith("Deck_Pillar_Port_")
    )
    stbd_xs = sorted(
        round((o.Shape.BoundBox.XMin + o.Shape.BoundBox.XMax) / 2.0, 1)
        for o in deck.document.Objects
        if o.Label.startswith("Deck_Pillar_Starboard_")
    )
    assert port_xs == stbd_xs, (
        f"FR-018: pillar X stations differ between sides — port={port_xs}, "
        f"starboard={stbd_xs}"
    )


@pytest.mark.requires_freecad
def test_exactly_one_port_and_one_starboard_railing(freecad_doc: object) -> None:
    """FR-022 — railings are symmetric port + starboard, exactly one of each."""
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    side_bodies = [
        o
        for o in deck.document.Objects
        if o.Label.startswith("Deck_Railings_") and o.Label != "Deck_Railings"
    ]
    port = [o for o in side_bodies if "Port" in o.Label]
    starboard = [o for o in side_bodies if "Starboard" in o.Label]
    assert len(port) == 1, f"FR-022: expected 1 port railing body, got {len(port)}"
    assert len(starboard) == 1, (
        f"FR-022: expected 1 starboard railing body, got {len(starboard)}"
    )
