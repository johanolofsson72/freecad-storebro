"""Unit tests for spec 014 ShaftParameters validation (FR-002, FR-004, T012)."""

from __future__ import annotations

import pytest

from storebro.propulsion import PropulsionParameterError, ShaftParameters


def test_defaults_construct() -> None:
    p = ShaftParameters()
    assert p.diameter_mm == 45.0
    assert p.angle_deg == 10.0
    assert p.exit_x_mm == 1800.0


@pytest.mark.parametrize("value", [0.0, -1.0])
def test_non_positive_diameter_raises(value: float) -> None:
    with pytest.raises(PropulsionParameterError) as exc:
        ShaftParameters(diameter_mm=value)
    assert exc.value.parameter_name == "shaft.diameter_mm"


@pytest.mark.parametrize("value", [0.0, 30.0])
def test_angle_bounds_inclusive(value: float) -> None:
    assert ShaftParameters(angle_deg=value).angle_deg == value


@pytest.mark.parametrize("value", [-0.1, 30.1, 45.0])
def test_angle_out_of_range_raises(value: float) -> None:
    with pytest.raises(PropulsionParameterError) as exc:
        ShaftParameters(angle_deg=value)
    assert exc.value.parameter_name == "shaft.angle_deg"


def test_negative_exit_raises() -> None:
    with pytest.raises(PropulsionParameterError) as exc:
        ShaftParameters(exit_x_mm=-1.0)
    assert exc.value.parameter_name == "shaft.exit_x_mm"
