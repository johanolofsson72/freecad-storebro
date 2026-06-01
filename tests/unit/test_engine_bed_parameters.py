"""Unit tests for spec 014 EngineBedParameters validation (FR-002, T012)."""

from __future__ import annotations

import pytest

from storebro.propulsion import EngineBedParameters, PropulsionParameterError


def test_defaults_construct() -> None:
    p = EngineBedParameters()
    assert p.length_mm == 1400.0
    assert p.width_mm == 120.0
    assert p.height_mm == 200.0


@pytest.mark.parametrize("field", ["length_mm", "width_mm", "height_mm"])
@pytest.mark.parametrize("value", [0.0, -1.0])
def test_non_positive_dimension_raises(field: str, value: float) -> None:
    with pytest.raises(PropulsionParameterError) as exc:
        EngineBedParameters(**{field: value})
    assert exc.value.parameter_name == f"engine_bed.{field}"


@pytest.mark.parametrize("field", ["length_mm", "width_mm", "height_mm"])
def test_non_finite_dimension_raises(field: str) -> None:
    with pytest.raises(PropulsionParameterError):
        EngineBedParameters(**{field: float("inf")})
