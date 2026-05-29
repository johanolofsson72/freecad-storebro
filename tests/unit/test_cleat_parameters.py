"""Unit tests for spec 010 CleatParameters validation (FR-003, FR-009)."""

from __future__ import annotations

import pytest

from storebro.deck import CleatParameters, DeckParameterError


def test_defaults_construct() -> None:
    p = CleatParameters()
    assert p.count_per_station == 1
    assert p.station_count == 2
    assert p.length == 200.0
    assert p.height == 80.0


def test_default_total_is_four() -> None:
    """Per-side semantics: total = count_per_station * station_count * 2."""
    p = CleatParameters()
    assert p.count_per_station * p.station_count * 2 == 4


def test_negative_count_per_station_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        CleatParameters(count_per_station=-1)
    assert exc.value.parameter_name == "cleat_count_per_station"


def test_negative_station_count_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        CleatParameters(station_count=-1)
    assert exc.value.parameter_name == "cleat_station_count"


def test_zero_counts_allowed() -> None:
    """Zero cleats is a valid no-op (FR-016)."""
    p = CleatParameters(count_per_station=0, station_count=0)
    assert p.count_per_station == 0
    assert p.station_count == 0


@pytest.mark.parametrize(
    ("field", "name"),
    [("length", "cleat_length"), ("height", "cleat_height")],
)
@pytest.mark.parametrize("value", [0.0, -1.0])
def test_non_positive_dimension_raises(field: str, name: str, value: float) -> None:
    with pytest.raises(DeckParameterError) as exc:
        CleatParameters(**{field: value})
    assert exc.value.parameter_name == name
