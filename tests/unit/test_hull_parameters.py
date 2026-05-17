"""Unit tests for HullParameters dataclass (T015).

Covers FR-002, FR-004, FR-008, FR-009 (symmetric, no asymmetric params),
FR-012 (geometric impossibility), SC-007 (≥5 invalid-input cases).
"""

from __future__ import annotations

import dataclasses

import pytest

from storebro import HullParameterError, HullParameters


class TestDefaults:
    def test_defaults_match_reference_constant(self) -> None:
        p = HullParameters()
        ref = HullParameters.REFERENCE_STOREBRO_ROYAL_CRUISER_34_1972
        assert p.loa == ref["loa"]
        assert p.beam_max == ref["beam_max"]
        assert p.draft == ref["draft"]
        assert p.freeboard == ref["freeboard"]
        assert p.deadrise_amidships == ref["deadrise_amidships"]
        assert p.sheer_height_aft == ref["sheer_height_aft"]
        assert p.sheer_height_fwd == ref["sheer_height_fwd"]
        assert p.transom_angle == ref["transom_angle"]

    def test_citation_grade_loa_is_10_35(self) -> None:
        # Royal Cruiser 34, 1972 model — domain-expert citation
        assert HullParameters().loa == 10.35

    def test_citation_grade_beam_is_3_20(self) -> None:
        assert HullParameters().beam_max == 3.20

    def test_aspect_ratio_property(self) -> None:
        p = HullParameters()
        assert abs(p.aspect_ratio - (10.35 / 3.20)) < 1e-9

    def test_is_planing_hull_property(self) -> None:
        p = HullParameters()
        assert p.is_planing_hull is True  # aspect ratio ~3.23

    def test_is_displacement_hull_when_low_aspect(self) -> None:
        p = HullParameters(loa=8.0, beam_max=3.20)
        assert p.is_planing_hull is False


class TestPerFieldRejections:
    @pytest.mark.parametrize(
        "kwargs,expected_field",
        [
            ({"loa": 0.0}, "loa"),
            ({"loa": -1.0}, "loa"),
            ({"beam_max": 0.0}, "beam_max"),
            ({"beam_max": -0.1}, "beam_max"),
            ({"draft": 0.0}, "draft"),
            ({"draft": -1.0}, "draft"),
            ({"freeboard": 0.0}, "freeboard"),
            ({"freeboard": -0.5}, "freeboard"),
            ({"sheer_height_aft": 0.0}, "sheer_height_aft"),
            ({"sheer_height_fwd": -0.1}, "sheer_height_fwd"),
        ],
    )
    def test_non_positive_lengths_rejected(
        self, kwargs: dict[str, float], expected_field: str
    ) -> None:
        with pytest.raises(HullParameterError) as exc_info:
            HullParameters(**kwargs)
        assert exc_info.value.parameter_name == expected_field

    @pytest.mark.parametrize("deadrise", [-1.0, -0.01, 30.01, 90.0])
    def test_deadrise_out_of_range_rejected(self, deadrise: float) -> None:
        with pytest.raises(HullParameterError) as exc_info:
            HullParameters(deadrise_amidships=deadrise)
        assert exc_info.value.parameter_name == "deadrise_amidships"

    @pytest.mark.parametrize("angle", [-1.0, 45.01, 90.0])
    def test_transom_angle_out_of_range_rejected(self, angle: float) -> None:
        with pytest.raises(HullParameterError) as exc_info:
            HullParameters(transom_angle=angle)
        assert exc_info.value.parameter_name == "transom_angle"


class TestCrossFieldRejections:
    def test_loa_le_beam_max_rejected(self) -> None:
        with pytest.raises(HullParameterError) as exc_info:
            HullParameters(loa=3.0, beam_max=4.0)
        assert exc_info.value.parameter_name == "loa<>beam_max"

    def test_loa_equal_to_beam_max_rejected(self) -> None:
        with pytest.raises(HullParameterError) as exc_info:
            HullParameters(loa=4.0, beam_max=4.0)
        assert exc_info.value.parameter_name == "loa<>beam_max"

    def test_inverted_sheer_rejected(self) -> None:
        with pytest.raises(HullParameterError) as exc_info:
            HullParameters(sheer_height_aft=1.5, sheer_height_fwd=1.0)
        assert exc_info.value.parameter_name == "sheer_height_fwd<>sheer_height_aft"

    def test_equal_sheer_heights_accepted(self) -> None:
        # Boundary case: fwd == aft is OK per FR-012
        p = HullParameters(sheer_height_aft=1.0, sheer_height_fwd=1.0)
        assert p.sheer_height_aft == p.sheer_height_fwd

    def test_deadrise_at_zero_is_valid(self) -> None:
        p = HullParameters(deadrise_amidships=0.0)
        assert p.deadrise_amidships == 0.0

    def test_deadrise_at_max_is_valid(self) -> None:
        p = HullParameters(deadrise_amidships=30.0)
        assert p.deadrise_amidships == 30.0


class TestFrozenness:
    def test_field_assignment_raises_frozen_instance_error(self) -> None:
        p = HullParameters()
        with pytest.raises(dataclasses.FrozenInstanceError):
            p.loa = 12.0  # type: ignore[misc]

    def test_hashable(self) -> None:
        p1 = HullParameters()
        p2 = HullParameters()
        assert hash(p1) == hash(p2)

    def test_value_equal(self) -> None:
        p1 = HullParameters()
        p2 = HullParameters()
        assert p1 == p2

    def test_different_values_not_equal(self) -> None:
        p1 = HullParameters()
        p2 = HullParameters(loa=12.0)
        assert p1 != p2


class TestCustomParameters:
    def test_custom_loa_accepted(self) -> None:
        p = HullParameters(loa=12.0)
        assert p.loa == 12.0

    def test_all_custom_parameters_accepted(self) -> None:
        p = HullParameters(
            loa=11.5,
            beam_max=3.5,
            draft=1.1,
            freeboard=1.0,
            deadrise_amidships=18.0,
            sheer_height_aft=0.9,
            sheer_height_fwd=1.4,
            transom_angle=10.0,
        )
        assert p.loa == 11.5
