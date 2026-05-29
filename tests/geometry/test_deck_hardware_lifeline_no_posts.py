"""Geometry test: lifelines degrade gracefully without railing posts (T026).

Covers spec 010 FR-017 + spec.allium SkipLifelinesWithoutPosts /
LifelinesRequirePosts.
"""

from __future__ import annotations

import pytest

from storebro import (
    DeckSuperstructureParameters,
    RailingParameters,
    build_deck,
    build_hull,
)


@pytest.mark.requires_freecad
def test_lifelines_skipped_when_no_railing_posts(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    # Railing with zero posts → lifelines have nothing to attach to.
    sp = DeckSuperstructureParameters(railings=RailingParameters(post_count_per_side=0))
    deck = build_deck(hull, parameters_superstructure=sp)
    assert deck.lifelines.line_count == 0
    # The compound exists but is empty (no exception raised).
    assert deck.lifelines.body is not None
    assert deck.lifelines.body.Shape.Solids == [] or deck.lifelines.body.Shape.Volume == 0.0


@pytest.mark.requires_freecad
def test_lifelines_present_with_default_posts(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    # Default railing has 6 posts/side → 1 line/side → 2 lifeline bodies.
    assert deck.lifelines.line_count == 2
    assert deck.lifelines.body.Shape.Volume > 0.0
