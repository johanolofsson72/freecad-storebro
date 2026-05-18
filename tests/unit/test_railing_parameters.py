"""Unit tests for spec 008 RailingParameters validation (FR-019..022, FR-026)."""

from __future__ import annotations

import pytest

from storebro.deck import DeckParameterError, RailingParameters


def test_defaults_construct_without_error() -> None:
    p = RailingParameters()
    assert p.post_count_per_side == 6
    assert p.post_diameter == 25.0
    assert p.top_rail_diameter == 30.0
    assert p.height_above_deck == 720.0
    assert p.forward_x == 0.0
    assert p.aft_x == 9800.0
    assert p.inboard_offset_from_sheer == 60.0


def test_zero_post_count_is_allowed() -> None:
    """A railing with no posts (top rail only) is still mathematically valid."""
    p = RailingParameters(post_count_per_side=0)
    assert p.post_count_per_side == 0


def test_negative_post_count_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        RailingParameters(post_count_per_side=-1)
    assert exc.value.parameter_name == "railing_post_count_per_side"


@pytest.mark.parametrize(
    "field,value,expected_param_name",
    [
        ("post_diameter", 0.0, "railing_post_diameter"),
        ("post_diameter", -10.0, "railing_post_diameter"),
        ("top_rail_diameter", 0.0, "railing_top_rail_diameter"),
        ("height_above_deck", 0.0, "railing_height_above_deck"),
    ],
)
def test_non_positive_dimensions_raise(
    field: str, value: float, expected_param_name: str
) -> None:
    with pytest.raises(DeckParameterError) as exc:
        RailingParameters(**{field: value})
    assert exc.value.parameter_name == expected_param_name


def test_forward_x_equal_to_aft_x_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        RailingParameters(forward_x=5000.0, aft_x=5000.0)
    assert exc.value.parameter_name == "railing_forward_x<>aft_x"


def test_forward_x_greater_than_aft_x_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        RailingParameters(forward_x=9000.0, aft_x=5000.0)
    assert exc.value.parameter_name == "railing_forward_x<>aft_x"


def test_negative_inboard_offset_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        RailingParameters(inboard_offset_from_sheer=-5.0)
    assert exc.value.parameter_name == "railing_inboard_offset_from_sheer"


def test_zero_inboard_offset_is_allowed() -> None:
    p = RailingParameters(inboard_offset_from_sheer=0.0)
    assert p.inboard_offset_from_sheer == 0.0


def test_dataclass_is_frozen() -> None:
    p = RailingParameters()
    with pytest.raises(Exception):  # noqa: B017
        p.height_above_deck = 999.0  # type: ignore[misc]
