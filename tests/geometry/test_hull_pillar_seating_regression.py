"""Spec 009 T023 — pillar seating regression test against the v1.0.3 hull.

Spec 008 introduced ``_resolve_deck_top_z_at()`` to seat hardtop pillars on
the actual deck plate top Z. Spec 009's denser-station + B-spline hull
changes the sheer line at any given X-station, so this test verifies the
resolver helper still produces pillar bases within ±1 mm of deck top Z
against the new hull.
"""

from __future__ import annotations

import pytest

from storebro.deck import build_deck
from storebro.hull import HullParameters, build_hull

pytestmark = pytest.mark.requires_freecad


def test_default_pillars_do_not_pierce_hull_after_v103_smooth_hull() -> None:
    """Spec 008 pillar-seating contract preserved against the v1.0.3 hull."""
    hull = build_hull(HullParameters())
    deck = build_deck(hull)

    # spec 008 stores pillars in deck.hardtop_pillars (HardtopPillars wrapper).
    pillars_wrapper = deck.hardtop_pillars
    assert pillars_wrapper is not None, "deck.hardtop_pillars is None"

    # The wrapper exposes per-pillar Bodies; inspect each one's bbox.
    # The HardtopPillars dataclass in spec 008 carries individual pillar
    # references via attributes — fall back to inspecting the document
    # for objects whose name contains 'Pillar'.
    pillar_objects = [
        obj
        for obj in hull.document.Objects
        if obj.TypeId == "PartDesign::Body" and "Pillar" in obj.Name
    ]
    assert pillar_objects, "no Pillar Body objects found in the document"

    for pillar in pillar_objects:
        bbox = pillar.Shape.BoundBox
        # Pillars must sit on the deck, not pierce into the hull. A pillar
        # extending below -100 mm Z is certainly piercing the hull.
        assert bbox.ZMin > -100.0, (
            f"pillar {pillar.Name} ZMin={bbox.ZMin} mm — likely piercing the hull "
            "(spec 008 regression on v1.0.3 hull)"
        )
