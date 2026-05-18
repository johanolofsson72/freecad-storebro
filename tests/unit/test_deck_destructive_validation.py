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
    CabinTrunkParameters,
    DeckParameterError,
    DeckSuperstructureParameters,
    HardtopParameters,
    PillarParameters,
    RailingParameters,
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
