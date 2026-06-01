"""Unit tests for spec 014 RudderParameters validation (FR-002, T012)."""

from __future__ import annotations

import pytest

from storebro.propulsion import PropulsionParameterError, RudderParameters


def test_defaults_construct() -> None:
    p = RudderParameters()
    assert p.chord_mm == 300.0
    assert p.span_mm == 500.0
    assert p.thickness_mm == 40.0
    assert p.stock_diameter_mm == 50.0


@pytest.mark.parametrize(
    "field", ["chord_mm", "span_mm", "thickness_mm", "stock_diameter_mm"]
)
@pytest.mark.parametrize("value", [0.0, -1.0])
def test_non_positive_dimension_raises(field: str, value: float) -> None:
    with pytest.raises(PropulsionParameterError) as exc:
        RudderParameters(**{field: value})
    assert exc.value.parameter_name == f"rudder.{field}"
