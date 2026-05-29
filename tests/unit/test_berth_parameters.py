"""Unit tests for spec 012 BerthParameters validation (FR-003)."""

from __future__ import annotations

import pytest

from storebro.interior import BerthParameters, InteriorParameterError


def test_defaults_construct() -> None:
    p = BerthParameters()
    assert p.base_height == 350.0
    assert p.cushion_thickness == 100.0
    assert p.cushion_count == 1
    assert p.wall_inset == 50.0


@pytest.mark.parametrize(
    ("field", "name"),
    [("base_height", "berth_base_height"), ("cushion_thickness", "berth_cushion_thickness")],
)
@pytest.mark.parametrize("value", [0.0, -1.0])
def test_non_positive_dimension_raises(field: str, name: str, value: float) -> None:
    with pytest.raises(InteriorParameterError) as exc:
        BerthParameters(**{field: value})
    assert exc.value.field == name


def test_negative_cushion_count_raises() -> None:
    with pytest.raises(InteriorParameterError) as exc:
        BerthParameters(cushion_count=-1)
    assert exc.value.field == "berth_cushion_count"


def test_zero_cushion_count_allowed() -> None:
    assert BerthParameters(cushion_count=0).cushion_count == 0


def test_negative_inset_raises() -> None:
    with pytest.raises(InteriorParameterError) as exc:
        BerthParameters(wall_inset=-1.0)
    assert exc.value.field == "berth_wall_inset"
