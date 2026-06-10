"""Unit test (no FreeCAD): spec 025 compartment types + new-type params (T005).

Covers FR-002, FR-003, FR-004, FR-011 (type set + furnish-by-type gate).
"""

from __future__ import annotations

import pytest

from storebro import EngineRoomParameters, InteriorParameterError, WetLockerParameters
from storebro.interior import (
    _COMPARTMENT_TYPES,
    _FURNISHABLE_TYPES,
    _parse_compartment_entry,
)

_NEW_TYPES = ("aft_cabin", "dinette", "engine_room", "wet_locker", "salon_galley")


def test_new_types_in_compartment_set() -> None:
    for t in _NEW_TYPES:
        assert t in _COMPARTMENT_TYPES


def test_every_type_is_furnishable() -> None:
    # spec 025 — furnishing is type-driven; every type furnishes.
    assert _FURNISHABLE_TYPES == _COMPARTMENT_TYPES
    for t in _NEW_TYPES:
        assert t in _FURNISHABLE_TYPES


def _entry(ctype: str, y: float = 0.0) -> dict:
    return {
        "name": "C",
        "type": ctype,
        "position": {"x": 0.5, "y": y, "z": 0.5},
        "dimensions": {"length": 1.5, "width": 1.5, "height": 1.4},
    }


@pytest.mark.parametrize("ctype", _NEW_TYPES)
def test_parser_accepts_new_types(ctype: str) -> None:
    spec = _parse_compartment_entry(_entry(ctype), "src", set())
    assert spec.compartment_type == ctype


def test_parser_rejects_unknown_type() -> None:
    with pytest.raises(InteriorParameterError) as exc:
        _parse_compartment_entry(_entry("submarine_bay"), "src", set())
    assert exc.value.field == "type"


def test_engine_room_params_defaults_and_validation() -> None:
    p = EngineRoomParameters()
    assert p.block_height > 0 and p.raised_top_height > 0
    with pytest.raises(InteriorParameterError):
        EngineRoomParameters(block_height=-1.0)
    with pytest.raises(InteriorParameterError):
        EngineRoomParameters(raised_top_height=0.0)


def test_wet_locker_params_defaults_and_validation() -> None:
    p = WetLockerParameters()
    assert p.shelf_count == 2 and p.locker_height > 0
    with pytest.raises(InteriorParameterError):
        WetLockerParameters(locker_height=0.0)
    with pytest.raises(InteriorParameterError):
        WetLockerParameters(shelf_count=-1)
    WetLockerParameters(shelf_count=0)  # zero shelves is valid
