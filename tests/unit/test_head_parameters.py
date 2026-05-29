"""Unit tests for spec 012 HeadParameters validation (FR-003)."""

from __future__ import annotations

import pytest

from storebro.interior import HeadParameters, InteriorParameterError


def test_defaults_construct() -> None:
    p = HeadParameters()
    assert p.toilet_height == 400.0
    assert p.sink_height == 800.0


@pytest.mark.parametrize(
    ("field", "name"),
    [("toilet_height", "head_toilet_height"), ("sink_height", "head_sink_height")],
)
@pytest.mark.parametrize("value", [0.0, -1.0])
def test_non_positive_dimension_raises(field: str, name: str, value: float) -> None:
    with pytest.raises(InteriorParameterError) as exc:
        HeadParameters(**{field: value})
    assert exc.value.field == name
