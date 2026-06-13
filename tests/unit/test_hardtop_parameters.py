"""Unit tests for spec 008 HardtopParameters validation (FR-009..013, FR-026)."""

from __future__ import annotations

import pytest

from storebro.deck import DeckParameterError, HardtopParameters


def test_defaults_construct_without_error() -> None:
    p = HardtopParameters()
    assert p.length == 3700.0
    assert p.forward_width == 2200.0
    assert p.aft_width == 2000.0
    assert p.thickness == 60.0
    assert p.height_above_deck == 1520.0  # spec 033: continuous coupe roofline
    assert p.leading_edge_curl_depth == 80.0
    assert p.leading_edge_curl_length == 250.0


def test_aft_taper_invariant_holds_on_defaults() -> None:
    p = HardtopParameters()
    assert p.aft_width <= p.forward_width


@pytest.mark.parametrize(
    "field,value,expected_param_name",
    [
        ("length", 0.0, "hardtop_length"),
        ("length", -10.0, "hardtop_length"),
        ("forward_width", 0.0, "hardtop_forward_width"),
        ("aft_width", 0.0, "hardtop_aft_width"),
        ("thickness", 0.0, "hardtop_thickness"),
        ("height_above_deck", 0.0, "hardtop_height_above_deck"),
    ],
)
def test_non_positive_dimensions_raise(
    field: str, value: float, expected_param_name: str
) -> None:
    with pytest.raises(DeckParameterError) as exc:
        HardtopParameters(**{field: value})
    assert exc.value.parameter_name == expected_param_name


@pytest.mark.parametrize(
    "field,value,expected_param_name",
    [
        ("leading_edge_curl_depth", -1.0, "hardtop_leading_edge_curl_depth"),
        ("leading_edge_curl_length", -1.0, "hardtop_leading_edge_curl_length"),
    ],
)
def test_negative_curl_dimensions_raise(
    field: str, value: float, expected_param_name: str
) -> None:
    with pytest.raises(DeckParameterError) as exc:
        HardtopParameters(**{field: value})
    assert exc.value.parameter_name == expected_param_name


def test_zero_curl_dimensions_are_allowed() -> None:
    p = HardtopParameters(leading_edge_curl_depth=0.0, leading_edge_curl_length=0.0)
    assert p.leading_edge_curl_depth == 0.0
    assert p.leading_edge_curl_length == 0.0


def test_aft_wider_than_forward_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        HardtopParameters(forward_width=2000.0, aft_width=2500.0)
    assert exc.value.parameter_name == "hardtop_aft_width<>forward_width"


def test_aft_equal_to_forward_is_allowed() -> None:
    p = HardtopParameters(forward_width=2100.0, aft_width=2100.0)
    assert p.forward_width == p.aft_width


def test_curl_length_exceeding_length_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        HardtopParameters(length=300.0, leading_edge_curl_length=500.0)
    assert exc.value.parameter_name == "hardtop_curl_length<>length"


def test_curl_depth_exceeding_height_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        HardtopParameters(height_above_deck=100.0, leading_edge_curl_depth=200.0)
    assert exc.value.parameter_name == "hardtop_curl_depth<>height"


def test_dataclass_is_frozen() -> None:
    p = HardtopParameters()
    with pytest.raises(Exception):  # noqa: B017
        p.length = 9999.0  # type: ignore[misc]
