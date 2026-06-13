"""Unit tests for spec 008 CabinTrunkParameters validation (FR-001..004, FR-026)."""

from __future__ import annotations

import pytest

from storebro.deck import CabinTrunkParameters, DeckParameterError


def test_defaults_construct_without_error() -> None:
    p = CabinTrunkParameters()
    assert p.length == 4600.0
    assert p.forward_width == 1900.0
    assert p.aft_width == 2150.0
    assert p.height == 1100.0
    assert p.forward_rake_angle == 20.0  # spec 033: raked windshield
    assert p.aft_rake_angle == 2.0
    assert p.wall_inset == 350.0


def test_tapered_silhouette_invariant_holds_on_defaults() -> None:
    p = CabinTrunkParameters()
    assert p.forward_width <= p.aft_width


@pytest.mark.parametrize(
    "field,value,expected_param_name",
    [
        ("length", 0.0, "cabin_trunk_length"),
        ("length", -100.0, "cabin_trunk_length"),
        ("forward_width", 0.0, "cabin_trunk_forward_width"),
        ("aft_width", -10.0, "cabin_trunk_aft_width"),
        ("height", 0.0, "cabin_trunk_height"),
    ],
)
def test_non_positive_dimensions_raise(field: str, value: float, expected_param_name: str) -> None:
    kwargs = {field: value}
    with pytest.raises(DeckParameterError) as exc:
        CabinTrunkParameters(**kwargs)
    assert exc.value.parameter_name == expected_param_name
    assert exc.value.parameter_value == value


def test_negative_wall_inset_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        CabinTrunkParameters(wall_inset=-1.0)
    assert exc.value.parameter_name == "cabin_trunk_wall_inset"


def test_zero_wall_inset_is_allowed() -> None:
    p = CabinTrunkParameters(wall_inset=0.0)
    assert p.wall_inset == 0.0


def test_forward_width_greater_than_aft_width_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        CabinTrunkParameters(forward_width=2500.0, aft_width=2000.0)
    assert exc.value.parameter_name == "cabin_trunk_forward_width<>aft_width"


def test_forward_width_equal_to_aft_width_is_allowed() -> None:
    p = CabinTrunkParameters(forward_width=2100.0, aft_width=2100.0)
    assert p.forward_width == p.aft_width


@pytest.mark.parametrize("angle", [-1.0, 46.0, 90.0])
def test_forward_rake_angle_out_of_range_raises(angle: float) -> None:
    with pytest.raises(DeckParameterError) as exc:
        CabinTrunkParameters(forward_rake_angle=angle)
    assert exc.value.parameter_name == "cabin_trunk_forward_rake_angle"


@pytest.mark.parametrize("angle", [0.0, 22.5, 45.0])
def test_forward_rake_angle_in_range_is_allowed(angle: float) -> None:
    p = CabinTrunkParameters(forward_rake_angle=angle)
    assert p.forward_rake_angle == angle


@pytest.mark.parametrize("angle", [-16.0, 31.0])
def test_aft_rake_angle_out_of_range_raises(angle: float) -> None:
    with pytest.raises(DeckParameterError) as exc:
        CabinTrunkParameters(aft_rake_angle=angle)
    assert exc.value.parameter_name == "cabin_trunk_aft_rake_angle"


@pytest.mark.parametrize("angle", [-15.0, 0.0, 15.0, 30.0])
def test_aft_rake_angle_in_range_is_allowed(angle: float) -> None:
    p = CabinTrunkParameters(aft_rake_angle=angle)
    assert p.aft_rake_angle == angle


def test_dataclass_is_frozen() -> None:
    p = CabinTrunkParameters()
    with pytest.raises(Exception):  # noqa: B017 — dataclasses raises FrozenInstanceError, narrow not portable
        p.length = 5000.0  # type: ignore[misc]
