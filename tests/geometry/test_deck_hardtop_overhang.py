"""Spec 008 FR-013 — hardtop overhang ≥ 50 mm beyond pillar attachment points.

The hardtop's forward and aft edges must extend at least 50 mm beyond
the pillars' longitudinal attachment X values (spec.allium
``HardtopOverhangsRespectMinimum`` invariant). Asserted on default
parameters; the 50 mm minimum is the spec FR-013 contract.
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull
from storebro.deck import DeckSuperstructureParameters

OVERHANG_MIN_MM = 50.0


@pytest.mark.requires_freecad
def test_hardtop_extends_beyond_pillars_at_both_ends(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull, parameters_superstructure=DeckSuperstructureParameters())
    pillar_xs = [
        (o.Shape.BoundBox.XMin + o.Shape.BoundBox.XMax) / 2.0
        for o in deck.document.Objects
        if o.Label.startswith("Deck_Pillar_")
    ]
    assert pillar_xs, "no pillars found — overhang test requires pillars"
    fwd_pillar_x = min(pillar_xs)
    aft_pillar_x = max(pillar_xs)
    hardtop_bb = deck.hardtop.body.Shape.BoundBox
    fwd_overhang = fwd_pillar_x - hardtop_bb.XMin
    aft_overhang = hardtop_bb.XMax - aft_pillar_x
    assert fwd_overhang >= OVERHANG_MIN_MM, (
        f"FR-013: forward hardtop overhang is {fwd_overhang:.1f} mm "
        f"(< {OVERHANG_MIN_MM} mm minimum)"
    )
    assert aft_overhang >= OVERHANG_MIN_MM, (
        f"FR-013: aft hardtop overhang is {aft_overhang:.1f} mm "
        f"(< {OVERHANG_MIN_MM} mm minimum)"
    )
