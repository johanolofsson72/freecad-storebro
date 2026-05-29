"""Unit tests for spec 011 PortholeParameters validation (FR-005)."""

from __future__ import annotations

import pytest

from storebro.hull import HullParameterError, PortholeParameters


def test_defaults_construct() -> None:
    p = PortholeParameters()
    assert p.count_per_side == 3
    assert p.diameter == 220.0
    assert p.recess_depth == 20.0
    assert p.forward_x == 0.0
    assert p.aft_x == 0.0
    assert p.height_above_waterline == 0.0


def test_negative_count_raises() -> None:
    with pytest.raises(HullParameterError) as exc:
        PortholeParameters(count_per_side=-1)
    assert exc.value.parameter_name == "porthole_count_per_side"


def test_zero_count_allowed() -> None:
    assert PortholeParameters(count_per_side=0).count_per_side == 0


@pytest.mark.parametrize(
    ("field", "name"),
    [("diameter", "porthole_diameter"), ("recess_depth", "porthole_recess_depth")],
)
@pytest.mark.parametrize("value", [0.0, -1.0])
def test_non_positive_dimension_raises(field: str, name: str, value: float) -> None:
    with pytest.raises(HullParameterError) as exc:
        PortholeParameters(**{field: value})
    assert exc.value.parameter_name == name


def test_negative_station_raises() -> None:
    with pytest.raises(HullParameterError) as exc:
        PortholeParameters(forward_x=-1.0)
    assert exc.value.parameter_name == "porthole_forward_x"


def test_forward_after_aft_raises_when_both_set() -> None:
    with pytest.raises(HullParameterError) as exc:
        PortholeParameters(forward_x=5000.0, aft_x=1000.0)
    assert exc.value.parameter_name == "porthole_forward_x<>aft_x"


def test_sentinel_zero_span_allowed() -> None:
    """0/0 means 'derive from geometry' — must not trip the ordering check."""
    p = PortholeParameters(forward_x=0.0, aft_x=0.0)
    assert p.forward_x == 0.0 and p.aft_x == 0.0


def test_is_value_error_subclass() -> None:
    with pytest.raises(ValueError):
        PortholeParameters(diameter=-1.0)
