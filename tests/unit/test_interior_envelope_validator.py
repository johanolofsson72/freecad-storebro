"""Unit tests for envelope validation (T021).

Covers FR-010 unit-level.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from storebro import InteriorParameterError
from storebro.interior import (
    CompartmentSpec,
    Dimensions3D,
    Position3D,
    _validate_compartment_in_envelope,
)


def _stub_hull(loa=10.35, beam_max=3.20, draft=0.95, sheer_height_fwd=1.30):
    return SimpleNamespace(
        parameters=SimpleNamespace(
            loa=loa,
            beam_max=beam_max,
            draft=draft,
            sheer_height_fwd=sheer_height_fwd,
        )
    )


def _spec(name="C", x=0.5, y=0.0, z=0.5, length=1.0, width=1.0, height=1.0):
    return CompartmentSpec(
        name=name,
        compartment_type="forward_cabin",
        position=Position3D(x, y, z),
        dimensions=Dimensions3D(length, width, height),
    )


def test_in_envelope_accepted() -> None:
    _validate_compartment_in_envelope(_spec(), _stub_hull(), "test")


def test_negative_x_rejected() -> None:
    with pytest.raises(InteriorParameterError) as exc:
        _validate_compartment_in_envelope(_spec(x=-1.0), _stub_hull(), "test")
    assert exc.value.field == "position.x"


def test_extends_past_stem_rejected() -> None:
    with pytest.raises(InteriorParameterError) as exc:
        _validate_compartment_in_envelope(
            _spec(x=9.0, length=2.0), _stub_hull(), "test"
        )
    assert exc.value.field == "dimensions.length"


def test_too_wide_rejected() -> None:
    with pytest.raises(InteriorParameterError) as exc:
        _validate_compartment_in_envelope(
            _spec(width=4.0), _stub_hull(), "test"
        )
    assert exc.value.field == "dimensions.width"


def test_below_keel_rejected() -> None:
    with pytest.raises(InteriorParameterError) as exc:
        _validate_compartment_in_envelope(
            _spec(z=-2.0), _stub_hull(), "test"
        )
    assert exc.value.field == "position.z"


def test_above_cabin_top_rejected() -> None:
    with pytest.raises(InteriorParameterError) as exc:
        _validate_compartment_in_envelope(
            _spec(z=1.0, height=5.0), _stub_hull(), "test"
        )
    assert exc.value.field == "dimensions.height"
