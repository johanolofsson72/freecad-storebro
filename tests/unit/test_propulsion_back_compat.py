"""Unit test: spec 014 adds public API additively (T037, FR-013)."""

from __future__ import annotations

import inspect

import storebro


def test_pre_1_1_0_names_still_exported() -> None:
    pre_existing = [
        "build_hull",
        "build_deck",
        "build_interior",
        "Hull",
        "Deck",
        "Interior",
        "export_fcstd",
        "export_step",
        "export_stl",
        "export_brep",
        "main",
    ]
    for name in pre_existing:
        assert name in storebro.__all__, f"{name} dropped from public API"
        assert hasattr(storebro, name)


def test_new_propulsion_names_exported() -> None:
    new_names = [
        "build_propulsion",
        "Propulsion",
        "PropulsionParameters",
        "EngineBedParameters",
        "EngineParameters",
        "ShaftParameters",
        "PropellerParameters",
        "RudderParameters",
        "EngineBed",
        "EngineBlock",
        "Shaft",
        "Propeller",
        "Rudder",
        "PropulsionParameterError",
        "PropulsionConstructionError",
        # spec 021 (propulsion-fidelity): the strut/P-bracket support body.
        "Strut",
    ]
    for name in new_names:
        assert name in storebro.__all__, f"{name} missing from public API"
        assert hasattr(storebro, name)


def test_existing_build_signatures_unchanged() -> None:
    hull_sig = inspect.signature(storebro.build_hull)
    assert next(iter(hull_sig.parameters)) == "parameters"
    deck_sig = inspect.signature(storebro.build_deck)
    assert next(iter(deck_sig.parameters)) == "hull"
