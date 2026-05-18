"""Unit tests for spec 008 WindshieldParameters validation (FR-005..008, FR-026)."""

from __future__ import annotations

import pytest

from storebro.deck import DeckParameterError, WindshieldParameters


def test_defaults_construct_without_error() -> None:
    p = WindshieldParameters()
    assert p.base_z == 0.0
    assert p.top_z == 750.0
    assert p.rake_angle_base == 35.0
    assert p.rake_angle_top == 38.0
    assert p.base_width == 2050.0
    assert p.top_width == 1800.0
    assert p.thickness == 25.0


def test_top_narrowing_invariant_holds_on_defaults() -> None:
    p = WindshieldParameters()
    assert p.top_width <= p.base_width


@pytest.mark.parametrize(
    "field,value,expected_param_name",
    [
        ("base_width", 0.0, "windshield_base_width"),
        ("base_width", -10.0, "windshield_base_width"),
        ("top_width", 0.0, "windshield_top_width"),
        ("thickness", 0.0, "windshield_thickness"),
    ],
)
def test_non_positive_dimensions_raise(
    field: str, value: float, expected_param_name: str
) -> None:
    with pytest.raises(DeckParameterError) as exc:
        WindshieldParameters(**{field: value})
    assert exc.value.parameter_name == expected_param_name


def test_top_z_equal_to_base_z_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        WindshieldParameters(base_z=500.0, top_z=500.0)
    assert exc.value.parameter_name == "windshield_top_z<>base_z"


def test_top_z_less_than_base_z_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        WindshieldParameters(base_z=500.0, top_z=400.0)
    assert exc.value.parameter_name == "windshield_top_z<>base_z"


def test_top_width_greater_than_base_width_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        WindshieldParameters(base_width=1800.0, top_width=2000.0)
    assert exc.value.parameter_name == "windshield_top_width<>base_width"


def test_top_width_equal_to_base_width_is_allowed() -> None:
    p = WindshieldParameters(base_width=2000.0, top_width=2000.0)
    assert p.top_width == p.base_width


@pytest.mark.parametrize("angle", [-11.0, 61.0])
def test_rake_angle_base_out_of_range_raises(angle: float) -> None:
    with pytest.raises(DeckParameterError) as exc:
        WindshieldParameters(rake_angle_base=angle)
    assert exc.value.parameter_name == "windshield_rake_angle_base"


@pytest.mark.parametrize("angle", [-11.0, 61.0])
def test_rake_angle_top_out_of_range_raises(angle: float) -> None:
    # Pick a base angle so the rake_delta * top_z calc doesn't trip the
    # curvature-radius check first.
    with pytest.raises(DeckParameterError) as exc:
        WindshieldParameters(rake_angle_base=0.0, rake_angle_top=angle)
    assert exc.value.parameter_name == "windshield_rake_angle_top"


def test_sub_minimum_curvature_radius_raises() -> None:
    # Tiny height + large rake delta = tight curve = self-intersection.
    with pytest.raises(DeckParameterError) as exc:
        WindshieldParameters(
            base_z=0.0,
            top_z=100.0,  # only 100 mm tall
            rake_angle_base=0.0,
            rake_angle_top=50.0,  # 50° rake delta
        )
    assert exc.value.parameter_name == "windshield_curvature_radius"


def test_equal_rakes_pass_curvature_check_regardless_of_height() -> None:
    # rake_delta = 0 → no curvature constraint.
    p = WindshieldParameters(
        base_z=0.0,
        top_z=50.0,
        rake_angle_base=20.0,
        rake_angle_top=20.0,
    )
    assert p.top_z > p.base_z


def test_dataclass_is_frozen() -> None:
    p = WindshieldParameters()
    with pytest.raises(Exception):  # noqa: B017
        p.top_z = 999.0  # type: ignore[misc]
