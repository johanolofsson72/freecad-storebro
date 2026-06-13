"""Unit tests for spec 030 windshield crown parameter validation (FR-001, FR-006..008).

No FreeCAD required — these exercise WindshieldParameters validation only. Geometry
assertions (crown shape, manifold, frame margin, reproducibility) live in the
requires_freecad suite (tests/geometry/test_windshield_crown_geom.py)."""

from __future__ import annotations

import math

import pytest

from storebro.deck import DeckParameterError, WindshieldParameters


def test_default_crown_height_is_60() -> None:
    # FR-001/FR-006: ships crowned by default.
    assert WindshieldParameters().crown_height == 60.0


def test_off_sentinel_zero_is_accepted() -> None:
    # FR-006: 0.0 is the OFF sentinel (flat top, byte-identical to pre-030).
    assert WindshieldParameters(crown_height=0.0).crown_height == 0.0


def test_valid_mid_value_is_accepted() -> None:
    p = WindshieldParameters(crown_height=120.0)
    assert p.crown_height == 120.0


def test_negative_crown_height_raises() -> None:
    # FR-008: negative crown ("frown") is not a supported shape.
    with pytest.raises(DeckParameterError) as exc:
        WindshieldParameters(crown_height=-1.0)
    assert exc.value.parameter_name == "windshield_crown_height"


def test_crown_height_at_half_top_width_raises() -> None:
    # FR-007: strict upper bound — exactly top_width/2 is rejected (degenerate arch).
    half = WindshieldParameters().top_width / 2.0  # 900.0
    with pytest.raises(DeckParameterError) as exc:
        WindshieldParameters(crown_height=half)
    assert exc.value.parameter_name == "windshield_crown_height"


def test_crown_height_above_half_top_width_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        WindshieldParameters(crown_height=1000.0)
    assert exc.value.parameter_name == "windshield_crown_height"


def test_crown_height_just_below_half_top_width_is_accepted() -> None:
    # Boundary: top_width/2 - epsilon is valid.
    p = WindshieldParameters(crown_height=899.0)
    assert p.crown_height == 899.0


def test_crown_bound_tracks_top_width() -> None:
    # FR-007: the bound is top_width/2, not a fixed constant — a narrower top
    # tightens it. With top_width=1000 the limit is 500.
    WindshieldParameters(base_width=2050.0, top_width=1000.0, crown_height=499.0)
    with pytest.raises(DeckParameterError) as exc:
        WindshieldParameters(base_width=2050.0, top_width=1000.0, crown_height=500.0)
    assert exc.value.parameter_name == "windshield_crown_height"


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_non_finite_crown_height_raises(bad: float) -> None:
    # FR-008: NaN/±inf rejected by the spec 029 _reject_nonfinite_floats guard,
    # which names the raw field "crown_height".
    with pytest.raises(DeckParameterError) as exc:
        WindshieldParameters(crown_height=bad)
    assert exc.value.parameter_name == "crown_height"


def test_crown_height_does_not_disturb_other_fields() -> None:
    p = WindshieldParameters(crown_height=40.0)
    assert p.base_width == 2050.0
    assert p.top_width == 1800.0
    assert p.thickness == 25.0
    assert p.rake_angle_base == 35.0
