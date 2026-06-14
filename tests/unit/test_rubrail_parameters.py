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


# --- spec 022: moulded profile + chrome insert -----------------------------


def test_spec022_defaults() -> None:
    p = RubrailParameters()
    assert p.rounded_profile is False  # chamfer is the reproducible default
    assert p.outboard_fillet == 12.0
    assert p.chamfer_width == 12.0
    assert p.chrome_insert is True
    assert p.insert_height == 30.0
    assert p.insert_thickness == 12.0


@pytest.mark.parametrize("field", ["outboard_fillet", "chamfer_width"])
@pytest.mark.parametrize("value", [0.0, -1.0, 1000.0])
def test_fillet_chamfer_out_of_range_raises(field: str, value: float) -> None:
    # Valid range is (0, min(height, thickness)/2] = (0, 20] at defaults.
    with pytest.raises(DeckParameterError) as exc:
        RubrailParameters(**{field: value})
    assert exc.value.parameter_name == f"rubrail_{field}"


@pytest.mark.parametrize("value", [0.0, -1.0, 60.0, 61.0])
def test_insert_height_out_of_range_raises(value: float) -> None:
    with pytest.raises(DeckParameterError) as exc:
        RubrailParameters(insert_height=value)
    assert exc.value.parameter_name == "rubrail_insert_height"


@pytest.mark.parametrize("value", [0.0, -1.0, 41.0])
def test_insert_thickness_out_of_range_raises(value: float) -> None:
    with pytest.raises(DeckParameterError) as exc:
        RubrailParameters(insert_thickness=value)
    assert exc.value.parameter_name == "rubrail_insert_thickness"


def test_chrome_insert_can_be_disabled() -> None:
    assert RubrailParameters(chrome_insert=False).chrome_insert is False


def test_rounded_profile_opt_in() -> None:
    assert RubrailParameters(rounded_profile=True).rounded_profile is True
