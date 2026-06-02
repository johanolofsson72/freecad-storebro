"""Spec 009 T007 — unit tests for HullParameters.station_count validation."""

from __future__ import annotations

import pytest

from storebro.hull import (
    DEFAULT_STATION_COUNT,
    STATION_COUNT_MAX,
    STATION_COUNT_MIN,
    HullParameterError,
    HullParameters,
)


def test_default_station_count_is_thirty_one() -> None:
    # spec 018: default densified 9 -> 31 for a smooth-reading Ruled=True hull.
    assert HullParameters().station_count == DEFAULT_STATION_COUNT == 31


def test_station_count_at_b_spline_threshold_is_accepted() -> None:
    HullParameters(station_count=8)


def test_station_count_at_minimum_is_accepted() -> None:
    HullParameters(station_count=STATION_COUNT_MIN)


def test_station_count_at_maximum_is_accepted() -> None:
    HullParameters(station_count=STATION_COUNT_MAX)


def test_station_count_below_minimum_raises() -> None:
    with pytest.raises(HullParameterError) as exc_info:
        HullParameters(station_count=STATION_COUNT_MIN - 1)
    err = exc_info.value
    assert err.parameter_name == "station_count"
    assert "3" in err.valid_range and "81" in err.valid_range


def test_station_count_above_maximum_raises() -> None:
    with pytest.raises(HullParameterError) as exc_info:
        HullParameters(station_count=STATION_COUNT_MAX + 1)
    err = exc_info.value
    assert err.parameter_name == "station_count"


def test_station_count_zero_raises() -> None:
    with pytest.raises(HullParameterError):
        HullParameters(station_count=0)


def test_station_count_negative_raises() -> None:
    with pytest.raises(HullParameterError):
        HullParameters(station_count=-5)


def test_station_count_remains_frozen() -> None:
    p = HullParameters(station_count=11)
    with pytest.raises(AttributeError):  # frozen dataclass raises FrozenInstanceError (subclass)
        p.station_count = 12  # type: ignore[misc]
