"""Unit tests for spec 014 EngineParameters validation (FR-002, T012)."""

from __future__ import annotations

import pytest

from storebro.propulsion import EngineParameters, PropulsionParameterError


def test_defaults_construct() -> None:
    p = EngineParameters()
    assert p.length_mm == 1100.0
    assert p.width_mm == 600.0
    assert p.height_mm == 700.0
    assert p.station_x_mm == 3500.0


@pytest.mark.parametrize("field", ["length_mm", "width_mm", "height_mm"])
@pytest.mark.parametrize("value", [0.0, -10.0])
def test_non_positive_dimension_raises(field: str, value: float) -> None:
    with pytest.raises(PropulsionParameterError) as exc:
        EngineParameters(**{field: value})
    assert exc.value.parameter_name == f"engine.{field}"


def test_zero_station_allowed() -> None:
    assert EngineParameters(station_x_mm=0.0).station_x_mm == 0.0


def test_negative_station_raises() -> None:
    with pytest.raises(PropulsionParameterError) as exc:
        EngineParameters(station_x_mm=-1.0)
    assert exc.value.parameter_name == "engine.station_x_mm"
