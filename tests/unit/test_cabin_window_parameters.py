"""Unit tests for spec 011 CabinWindowParameters validation (FR-005)."""

from __future__ import annotations

import pytest

from storebro.deck import CabinWindowParameters, DeckParameterError


def test_defaults_construct() -> None:
    p = CabinWindowParameters()
    assert p.count_per_side == 3  # spec 033: greenhouse window band
    assert p.length == 900.0
    assert p.height == 450.0  # spec 033
    assert p.corner_radius == 80.0
    assert p.recess_depth == 15.0
    assert p.sill_height == 0.0


def test_negative_count_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        CabinWindowParameters(count_per_side=-1)
    assert exc.value.parameter_name == "cabin_window_count_per_side"


def test_zero_count_allowed() -> None:
    assert CabinWindowParameters(count_per_side=0).count_per_side == 0


@pytest.mark.parametrize(
    ("field", "name"),
    [
        ("length", "cabin_window_length"),
        ("height", "cabin_window_height"),
        ("recess_depth", "cabin_window_recess_depth"),
    ],
)
@pytest.mark.parametrize("value", [0.0, -1.0])
def test_non_positive_dimension_raises(field: str, name: str, value: float) -> None:
    with pytest.raises(DeckParameterError) as exc:
        CabinWindowParameters(**{field: value})
    assert exc.value.parameter_name == name


def test_negative_corner_radius_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        CabinWindowParameters(corner_radius=-1.0)
    assert exc.value.parameter_name == "cabin_window_corner_radius"


def test_corner_radius_too_large_for_height_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        CabinWindowParameters(corner_radius=200.0, height=350.0)  # 2*200 > 350
    assert exc.value.parameter_name == "cabin_window_corner_radius"


def test_corner_radius_too_large_for_length_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        CabinWindowParameters(corner_radius=400.0, length=700.0, height=900.0)  # 2*400 > 700
    assert exc.value.parameter_name == "cabin_window_corner_radius"


def test_negative_sill_height_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        CabinWindowParameters(sill_height=-1.0)
    assert exc.value.parameter_name == "cabin_window_sill_height"
