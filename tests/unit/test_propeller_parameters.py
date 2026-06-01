"""Unit tests for spec 014 PropellerParameters validation (FR-002, FR-004, T012)."""

from __future__ import annotations

import pytest

from storebro.propulsion import PropellerParameters, PropulsionParameterError


def test_defaults_construct() -> None:
    p = PropellerParameters()
    assert p.diameter_mm == 450.0
    assert p.hub_diameter_mm == 90.0
    assert p.blade_count == 3


@pytest.mark.parametrize("value", [0.0, -1.0])
def test_non_positive_diameter_raises(value: float) -> None:
    with pytest.raises(PropulsionParameterError):
        PropellerParameters(diameter_mm=value)


def test_hub_not_smaller_than_disc_raises() -> None:
    with pytest.raises(PropulsionParameterError) as exc:
        PropellerParameters(diameter_mm=100.0, hub_diameter_mm=100.0)
    assert exc.value.parameter_name == "propeller.hub_diameter_mm"


@pytest.mark.parametrize("value", [2, 6])
def test_blade_count_bounds_inclusive(value: int) -> None:
    assert PropellerParameters(blade_count=value).blade_count == value


@pytest.mark.parametrize("value", [1, 7, 0])
def test_blade_count_out_of_range_raises(value: int) -> None:
    with pytest.raises(PropulsionParameterError) as exc:
        PropellerParameters(blade_count=value)
    assert exc.value.parameter_name == "propeller.blade_count"
