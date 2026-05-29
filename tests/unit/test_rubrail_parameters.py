"""Unit tests for spec 010 RubrailParameters validation (FR-003, FR-005)."""

from __future__ import annotations

import pytest

from storebro.deck import DeckParameterError, RubrailParameters


def test_defaults_construct() -> None:
    p = RubrailParameters()
    assert p.height == 60.0
    assert p.thickness == 40.0
    assert p.forward_x == 300.0
    assert p.aft_x == 10000.0


@pytest.mark.parametrize("value", [0.0, -5.0])
def test_non_positive_height_raises(value: float) -> None:
    with pytest.raises(DeckParameterError) as exc:
        RubrailParameters(height=value)
    assert exc.value.parameter_name == "rubrail_height"


@pytest.mark.parametrize("value", [0.0, -1.0])
def test_non_positive_thickness_raises(value: float) -> None:
    with pytest.raises(DeckParameterError) as exc:
        RubrailParameters(thickness=value)
    assert exc.value.parameter_name == "rubrail_thickness"


def test_negative_forward_x_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        RubrailParameters(forward_x=-1.0)
    assert exc.value.parameter_name == "rubrail_forward_x"


def test_forward_not_before_aft_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        RubrailParameters(forward_x=5000.0, aft_x=1000.0)
    assert exc.value.parameter_name == "rubrail_forward_x<>aft_x"


def test_equal_forward_aft_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        RubrailParameters(forward_x=1000.0, aft_x=1000.0)
    assert exc.value.parameter_name == "rubrail_forward_x<>aft_x"


def test_is_value_error_subclass() -> None:
    with pytest.raises(ValueError):
        RubrailParameters(height=-1.0)
