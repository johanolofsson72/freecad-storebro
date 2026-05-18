"""Spec 008 FR-001/005/009/014/019/029 — superstructure bodies are PartDesign Bodies.

After the spec 008 refresh, every superstructure sub-body MUST be a
``PartDesign::Body`` with named feature children (sketches + AdditiveLoft /
Pad / Mirrored). The legacy v1.0.1 ``Part::Feature`` + raw ``Part.makeXxx``
implementations are retired. The deck plate is intentionally not part of
this contract — it lives in spec 003 scope and remains a Part::Feature.
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull


@pytest.mark.requires_freecad
def test_cabin_trunk_is_partdesign_body(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    assert deck.cabin_trunk.body.TypeId == "PartDesign::Body", (
        f"FR-001: cabin trunk must be PartDesign::Body, got {deck.cabin_trunk.body.TypeId}"
    )
    assert deck.cabin_trunk.body.Shape.Volume > 0


@pytest.mark.requires_freecad
def test_windshield_is_partdesign_body(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    assert deck.windshield.body.TypeId == "PartDesign::Body", (
        f"FR-005: windshield must be PartDesign::Body, got {deck.windshield.body.TypeId}"
    )
    assert deck.windshield.body.Shape.Volume > 0


@pytest.mark.requires_freecad
def test_hardtop_is_partdesign_body(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    assert deck.hardtop.body.TypeId == "PartDesign::Body", (
        f"FR-009: hardtop must be PartDesign::Body, got {deck.hardtop.body.TypeId}"
    )
    assert deck.hardtop.body.Shape.Volume > 0


@pytest.mark.requires_freecad
def test_every_pillar_is_partdesign_body(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    pillar_bodies = [
        obj
        for obj in deck.document.Objects
        if obj.Label.startswith("Deck_Pillar_")
    ]
    assert len(pillar_bodies) >= 2, "FR-014: at least one pillar body must exist on default params"
    for body in pillar_bodies:
        assert body.TypeId == "PartDesign::Body", (
            f"FR-014: pillar {body.Label} must be PartDesign::Body, got {body.TypeId}"
        )
        assert body.Shape.Volume > 0, f"FR-014: pillar {body.Label} has zero volume"


@pytest.mark.requires_freecad
def test_each_railing_side_is_partdesign_body(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    side_bodies = [
        obj
        for obj in deck.document.Objects
        if obj.Label.startswith("Deck_Railings_") and obj.Label != "Deck_Railings"
    ]
    assert len(side_bodies) == 2, (
        f"FR-019: expected exactly 2 railing side bodies (port + starboard), found {len(side_bodies)}"
    )
    for body in side_bodies:
        assert body.TypeId == "PartDesign::Body", (
            f"FR-019: railing side {body.Label} must be PartDesign::Body, got {body.TypeId}"
        )
        assert body.Shape.Volume > 0


@pytest.mark.requires_freecad
def test_no_raw_part_feature_for_named_superstructure_bodies(freecad_doc: object) -> None:
    """No body whose label starts with Deck_CabinTrunk, Deck_Windshield, Deck_Hardtop,
    Deck_Pillar_*, or Deck_Railings_* may be a raw Part::Feature (FR-029).

    The exception are the legacy compound wrappers (`Deck_HardtopPillars`,
    `Deck_Railings`) which intentionally remain Part::Feature compounds for
    backward compatibility — the underlying per-pillar / per-side bodies are
    the PartDesign Bodies under test.
    """
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    forbidden_prefixes = (
        "Deck_CabinTrunk",
        "Deck_Windshield",
        "Deck_Hardtop",  # NB: includes "Deck_Hardtop" but not "Deck_HardtopPillars"
        "Deck_Pillar_",
        "Deck_Railings_",  # port + starboard side bodies
    )
    excluded_labels = {"Deck_HardtopPillars", "Deck_Railings"}
    for obj in deck.document.Objects:
        if obj.Label in excluded_labels:
            continue
        if obj.Label == "Deck_Hardtop" or any(
            obj.Label.startswith(p) and obj.Label != "Deck_HardtopPillars"
            for p in forbidden_prefixes
        ):
            assert obj.TypeId == "PartDesign::Body", (
                f"FR-029: {obj.Label} is {obj.TypeId} but must be PartDesign::Body"
            )


@pytest.mark.requires_freecad
def test_each_partdesign_body_has_loft_or_pad_tip(freecad_doc: object) -> None:
    """FR-001/005/009/014/019: each superstructure Body should have a non-empty
    feature stack — at minimum a Tip that is one of AdditiveLoft, Pad, or
    AdditivePipe."""
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    bodies = [
        deck.cabin_trunk.body,
        deck.windshield.body,
        deck.hardtop.body,
    ]
    for body in bodies:
        assert body.Tip is not None, f"{body.Label}: no Tip feature"
        tip_type = body.Tip.TypeId
        assert any(
            keyword in tip_type
            for keyword in ("AdditiveLoft", "AdditivePipe", "Pad", "Mirrored")
        ), f"{body.Label}: Tip is {tip_type}, not a recognized PartDesign feature"
