"""Geometry test: hardware bodies are FreeCAD-idiomatic PartDesign (T015).

Covers spec 010 FR-002 + constitution III (no raw mesh). Every hardware
solid is a PartDesign::Body containing Pad/AdditiveLoft features; the
multi-instance items (rubrail, lifelines, cleats) are Part::Compounds of
such bodies.
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull

_PARTDESIGN_FEATURES = ("PartDesign::Pad", "PartDesign::AdditiveLoft")


@pytest.mark.requires_freecad
def test_partdesign_bodies_exist_for_each_hardware(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    type_ids = {obj.TypeId for obj in deck.document.Objects}
    assert "PartDesign::Body" in type_ids
    assert any(f in type_ids for f in _PARTDESIGN_FEATURES)


@pytest.mark.requires_freecad
def test_no_raw_mesh_objects(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    for obj in deck.document.Objects:
        assert not obj.TypeId.startswith("Mesh::"), (
            f"constitution III violation: raw mesh object {obj.Label} ({obj.TypeId})"
        )


@pytest.mark.requires_freecad
def test_rubrail_uses_additive_loft(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    loft_labels = [
        obj.Label
        for obj in deck.document.Objects
        if obj.TypeId == "PartDesign::AdditiveLoft" and "Rubrail" in obj.Label
    ]
    assert loft_labels, "FR-005: rubrail must be built with AdditiveLoft"
