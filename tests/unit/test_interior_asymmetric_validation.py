"""Unit test (no FreeCAD): spec 025 asymmetric placement validation (T006).

Covers FR-006 (y!=0 accepted) and FR-007 (transverse half-beam bound).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from storebro import InteriorParameterError
from storebro.interior import (
    CompartmentSpec,
    Dimensions3D,
    Position3D,
    _parse_compartment_entry,
    _validate_compartment_in_envelope,
)


def _stub_hull(beam_max=3.20):
    return SimpleNamespace(
        parameters=SimpleNamespace(
            loa=10.35, beam_max=beam_max, draft=0.95, sheer_height_fwd=1.30
        )
    )


def _spec(y=0.0, width=1.0):
    return CompartmentSpec(
        name="C",
        compartment_type="head",
        position=Position3D(0.5, y, 0.5),
        dimensions=Dimensions3D(1.0, width, 1.0),
    )


def test_parser_accepts_non_zero_y() -> None:
    # spec 025 — the v1.0 centreline reject is gone.
    entry = {
        "name": "PortHead",
        "type": "head",
        "position": {"x": 0.5, "y": 0.6, "z": 0.5},
        "dimensions": {"length": 1.0, "width": 1.0, "height": 1.4},
    }
    spec = _parse_compartment_entry(entry, "src", set())
    assert spec.position.y == 0.6


def test_centreline_still_valid() -> None:
    _validate_compartment_in_envelope(_spec(y=0.0, width=1.0), _stub_hull(), "test")


def test_offcentre_within_half_beam_accepted() -> None:
    # beam_max 3.20 -> half 1.60; 0.5 + 1.0/2 = 1.0 <= 1.60
    _validate_compartment_in_envelope(_spec(y=0.5, width=1.0), _stub_hull(), "test")


def test_offcentre_past_half_beam_rejected() -> None:
    # 1.0 + 1.4/2 = 1.70 > 1.60
    with pytest.raises(InteriorParameterError) as exc:
        _validate_compartment_in_envelope(_spec(y=1.0, width=1.4), _stub_hull(), "test")
    assert exc.value.field == "position.y"


def test_negative_y_uses_absolute_value() -> None:
    # |-1.0| + 1.4/2 = 1.70 > 1.60 → rejected (symmetric bound)
    with pytest.raises(InteriorParameterError) as exc:
        _validate_compartment_in_envelope(_spec(y=-1.0, width=1.4), _stub_hull(), "test")
    assert exc.value.field == "position.y"
