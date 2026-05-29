"""Spec 008 FR-032 — destructive parameter-validation tests.

Covers the 8 edge cases listed in spec.md → Edge Cases:

1. Zero pillars (valid construction path) — covered in geometry test_deck_pillar_zero_fallback
2. Pillar / cabin trunk footprint conflict
3. Oversized hardtop overhang (forward_width > deck width — note: deck width validation lives in build_deck, not the dataclass)
4. Sub-minimum windshield curvature
5. Railing height >= hardtop height (collision)
6. Negative / zero principal dimensions
7. Old-hull-parameter compatibility (covered in test_deck_back_compat)
8. Cross-platform reproducibility (covered in geometry test_deck_determinism)

This file consolidates the destructive negative-path tests at unit-test
level. Geometry-level destructive paths (e.g., zero-pillar build,
reproducibility) live alongside the corresponding positive-path tests
in tests/geometry/.
"""

from __future__ import annotations

import pytest

from storebro.deck import (
    AnchorLockerParameters,
    BowPulpitParameters,
    CabinTrunkParameters,
    CleatParameters,
    DeckParameterError,
    DeckSuperstructureParameters,
    HardtopParameters,
    LifelineParameters,
    PillarParameters,
    RailingParameters,
    RubrailParameters,
    WindshieldParameters,
)

# ---------------------------------------------------------------------------
# Edge case 2: Pillar / cabin trunk footprint conflict
# ---------------------------------------------------------------------------


def test_pillar_inside_cabin_trunk_footprint_raises() -> None:
    """spec.md FR-026 + edge case: cabin_trunk.length=4600, pillar.forward_x=4000 → conflict."""
    with pytest.raises(DeckParameterError) as exc:
        DeckSuperstructureParameters(
            cabin_trunk=CabinTrunkParameters(length=4600.0),
            pillars=PillarParameters(forward_x=4000.0, aft_x=5500.0),
        )
    assert exc.value.parameter_name == "pillar_forward_x<>cabin_trunk_length"


# ---------------------------------------------------------------------------
# Edge case 4: Sub-minimum windshield curvature radius
# ---------------------------------------------------------------------------


def test_tight_windshield_curve_raises() -> None:
    """Chord 80 mm with 60° rake delta → radius below 200 mm threshold."""
    with pytest.raises(DeckParameterError) as exc:
        WindshieldParameters(
            base_z=0.0,
            top_z=80.0,
            rake_angle_base=0.0,
            rake_angle_top=60.0,
        )
    assert exc.value.parameter_name == "windshield_curvature_radius"


# ---------------------------------------------------------------------------
# Edge case 5: Railing height >= hardtop height (railing penetrates hardtop)
# ---------------------------------------------------------------------------


def test_railing_taller_than_hardtop_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        DeckSuperstructureParameters(
            hardtop=HardtopParameters(height_above_deck=2000.0),
            railings=RailingParameters(height_above_deck=2500.0),
        )
    assert exc.value.parameter_name == "railing_height<>hardtop_height"


def test_railing_equal_to_hardtop_raises() -> None:
    """Equal heights still cause a collision; must reject."""
    with pytest.raises(DeckParameterError) as exc:
        DeckSuperstructureParameters(
            hardtop=HardtopParameters(height_above_deck=2000.0),
            railings=RailingParameters(height_above_deck=2000.0),
        )
    assert exc.value.parameter_name == "railing_height<>hardtop_height"


# ---------------------------------------------------------------------------
# Edge case 6: Negative / zero principal dimensions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "dataclass,kwargs,expected_param_name",
    [
        (CabinTrunkParameters, {"length": -1.0}, "cabin_trunk_length"),
        (CabinTrunkParameters, {"length": 0.0}, "cabin_trunk_length"),
        (WindshieldParameters, {"thickness": 0.0}, "windshield_thickness"),
        (HardtopParameters, {"thickness": 0.0}, "hardtop_thickness"),
        (PillarParameters, {"diameter": 0.0}, "pillar_diameter"),
        (PillarParameters, {"diameter": -10.0}, "pillar_diameter"),
        (RailingParameters, {"post_diameter": 0.0}, "railing_post_diameter"),
        (RailingParameters, {"height_above_deck": 0.0}, "railing_height_above_deck"),
    ],
)
def test_negative_or_zero_principal_dimensions_raise(
    dataclass: type, kwargs: dict[str, float], expected_param_name: str
) -> None:
    with pytest.raises(DeckParameterError) as exc:
        dataclass(**kwargs)
    assert exc.value.parameter_name == expected_param_name


# ---------------------------------------------------------------------------
# Edge case bonus: Hardtop curl exceeds bounds
# ---------------------------------------------------------------------------


def test_curl_length_greater_than_hardtop_length_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        HardtopParameters(length=500.0, leading_edge_curl_length=600.0)
    assert exc.value.parameter_name == "hardtop_curl_length<>length"


def test_curl_depth_greater_than_height_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        HardtopParameters(height_above_deck=100.0, leading_edge_curl_depth=200.0)
    assert exc.value.parameter_name == "hardtop_curl_depth<>height"


# ---------------------------------------------------------------------------
# Edge case bonus: Range violations on rake angles
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("angle", [46.0, -1.0])
def test_cabin_trunk_forward_rake_out_of_range_raises(angle: float) -> None:
    with pytest.raises(DeckParameterError) as exc:
        CabinTrunkParameters(forward_rake_angle=angle)
    assert exc.value.parameter_name == "cabin_trunk_forward_rake_angle"


# ---------------------------------------------------------------------------
# Edge case bonus: Invariant violations on ordering
# ---------------------------------------------------------------------------


def test_pillar_forward_x_greater_than_aft_x_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        PillarParameters(forward_x=8000.0, aft_x=5000.0)
    assert exc.value.parameter_name == "pillar_forward_x<>aft_x"


def test_railing_forward_x_greater_than_aft_x_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        RailingParameters(forward_x=9000.0, aft_x=5000.0)
    assert exc.value.parameter_name == "railing_forward_x<>aft_x"


# ---------------------------------------------------------------------------
# Spec 010 — deck-hardware destructive parameter validation (T031).
#
# Dataclass-level negative paths across the 6 attack categories. Cross-deck
# collision paths (anchor locker vs cabin trunk, rubrail vs deck extent) need
# the built deck plate and live in the geometry tier
# (tests/geometry/test_deck_hardware_anchor_locker_placement.py).
# ---------------------------------------------------------------------------


# Category 1: invalid input (negative, zero). NOTE: like every other deck
# dataclass in this module (spec 003/008), the `value <= 0` guards do NOT
# reject non-finite NaN/inf — that hardening would be a module-wide change
# applied uniformly to all 11 dataclasses, tracked as
# `DeckParameters.reject_non_finite` rather than bolted onto spec 010's five.
@pytest.mark.parametrize("value", [-1.0, 0.0])
def test_rubrail_invalid_height_raises(value: float) -> None:
    with pytest.raises(DeckParameterError):
        RubrailParameters(height=value)


@pytest.mark.parametrize("value", [-5.0, 0.0])
def test_cleat_invalid_length_raises(value: float) -> None:
    with pytest.raises(DeckParameterError):
        CleatParameters(length=value)


# Category 4: boundary values.
def test_lifeline_height_fraction_lower_boundary_zero_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        LifelineParameters(height_fraction=0.0)
    assert exc.value.parameter_name == "lifeline_height_fraction"


def test_lifeline_height_fraction_upper_boundary_one_ok() -> None:
    assert LifelineParameters(height_fraction=1.0).height_fraction == 1.0


def test_lifeline_height_fraction_just_above_one_raises() -> None:
    with pytest.raises(DeckParameterError):
        LifelineParameters(height_fraction=1.0000001)


def test_rubrail_equal_forward_aft_boundary_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        RubrailParameters(forward_x=2000.0, aft_x=2000.0)
    assert exc.value.parameter_name == "rubrail_forward_x<>aft_x"


# Category: extreme magnitude (very large still valid → no raise).
def test_extreme_but_valid_rubrail_constructs() -> None:
    p = RubrailParameters(height=1e6, thickness=1e6, forward_x=0.0, aft_x=1e9)
    assert p.aft_x == 1e9


# Zero-count no-op paths (FR-016) must NOT raise.
def test_zero_count_hardware_does_not_raise() -> None:
    CleatParameters(count_per_station=0, station_count=0)
    LifelineParameters(line_count=0)
    BowPulpitParameters(stanchion_count=0)


# Negative counts DO raise.
@pytest.mark.parametrize(
    ("ctor", "kwargs", "name"),
    [
        (CleatParameters, {"count_per_station": -1}, "cleat_count_per_station"),
        (CleatParameters, {"station_count": -1}, "cleat_station_count"),
        (LifelineParameters, {"line_count": -1}, "lifeline_line_count"),
        (BowPulpitParameters, {"stanchion_count": -1}, "bow_pulpit_stanchion_count"),
        (AnchorLockerParameters, {"center_x": -1.0}, "anchor_locker_center_x"),
    ],
)
def test_negative_counts_and_positions_raise(
    ctor: type, kwargs: dict[str, float], name: str
) -> None:
    with pytest.raises(DeckParameterError) as exc:
        ctor(**kwargs)
    assert exc.value.parameter_name == name
