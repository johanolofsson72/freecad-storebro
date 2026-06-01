"""Geometry test: default (twin) build produces all five components (T027, US2).

Covers spec 014 FR-001, FR-006, SC-001, SC-002.
"""

from __future__ import annotations

from storebro import build_deck, build_hull, build_propulsion

EXPECTED_LABEL_PREFIXES = (
    "Propulsion_EngineBed",
    "Propulsion_Engine",
    "Propulsion_Shaft",
    "Propulsion_Propeller",
    "Propulsion_Rudder",
)


def test_default_twin_two_of_each_running_gear(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    prop = build_propulsion(hull, deck)  # twin default

    assert len(prop.engine_beds) == 2
    assert len(prop.engines) == 2
    assert len(prop.shafts) == 2
    assert len(prop.propellers) == 2
    assert len(prop.rudders) == prop.parameters.rudder_count == 2


def test_default_adds_all_component_bodies_to_document(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    build_propulsion(hull, deck)
    labels = [obj.Label for obj in hull.document.Objects]
    for prefix in EXPECTED_LABEL_PREFIXES:
        assert any(label.startswith(prefix) for label in labels), (
            f"SC-001: no document object with prefix {prefix!r}"
        )
