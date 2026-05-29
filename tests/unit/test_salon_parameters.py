"""Unit tests for spec 012 SalonParameters validation (FR-003)."""

from __future__ import annotations

import pytest

from storebro.interior import InteriorParameterError, SalonParameters


def test_defaults_construct() -> None:
    p = SalonParameters()
    assert p.seat_height == 400.0
    assert p.table_height == 650.0


@pytest.mark.parametrize(
    ("field", "name"),
    [("seat_height", "salon_seat_height"), ("table_height", "salon_table_height")],
)
@pytest.mark.parametrize("value", [0.0, -1.0])
def test_non_positive_dimension_raises(field: str, name: str, value: float) -> None:
    with pytest.raises(InteriorParameterError) as exc:
        SalonParameters(**{field: value})
    assert exc.value.field == name
