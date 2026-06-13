"""Unit tests for DeckParameters dataclass (T014).

Covers FR-002, FR-008, FR-015, SC-007 (additional invalid-input cases).
"""

from __future__ import annotations

import dataclasses

import pytest

from storebro import DeckParameterError, DeckParameters


class TestDefaults:
    def test_defaults_match_reference_constant(self) -> None:
        p = DeckParameters()
        ref = DeckParameters.REFERENCE_STOREBRO_DECK_RC34_1972
        assert p.cabin_trunk_length == ref["cabin_trunk_length"]
        assert p.hardtop_length == ref["hardtop_length"]
        assert p.railing_height == ref["railing_height"]
        assert p.cabin_trunk_corner_radius == ref["cabin_trunk_corner_radius"]
        assert p.hardtop_pillar_diameter == ref["hardtop_pillar_diameter"]
        assert p.deck_plate_thickness == ref["deck_plate_thickness"]

    def test_default_cabin_trunk_length(self) -> None:
        assert DeckParameters().cabin_trunk_length == 5.20  # spec 033: RC34 greenhouse cabin

    def test_default_railing_height(self) -> None:
        assert DeckParameters().railing_height == 0.65


class TestPerFieldRejections:
    @pytest.mark.parametrize(
        "kwargs,expected_field",
        [
            ({"deck_plate_thickness": 0.0}, "deck_plate_thickness"),
            ({"cabin_trunk_length": -1.0}, "cabin_trunk_length"),
            ({"cabin_trunk_width": 0.0}, "cabin_trunk_width"),
            ({"cabin_trunk_height": -0.1}, "cabin_trunk_height"),
            ({"hardtop_length": 0.0}, "hardtop_length"),
            ({"hardtop_pillar_diameter": 0.0}, "hardtop_pillar_diameter"),
            ({"railing_height": 0.0}, "railing_height"),
            ({"deck_side_walkway": -0.05}, "deck_side_walkway"),
        ],
    )
    def test_non_positive_lengths_rejected(
        self, kwargs: dict[str, float], expected_field: str
    ) -> None:
        with pytest.raises(DeckParameterError) as exc_info:
            DeckParameters(**kwargs)
        assert exc_info.value.parameter_name == expected_field

    @pytest.mark.parametrize(
        "kwargs,expected_field",
        [
            ({"cabin_trunk_fwd_offset": -0.1}, "cabin_trunk_fwd_offset"),
            ({"cabin_trunk_corner_radius": -0.001}, "cabin_trunk_corner_radius"),
            ({"hardtop_height": -0.01}, "hardtop_height"),
            ({"hardtop_overhang_fwd": -0.1}, "hardtop_overhang_fwd"),
            ({"hardtop_overhang_aft": -0.1}, "hardtop_overhang_aft"),
        ],
    )
    def test_negative_non_negatives_rejected(
        self, kwargs: dict[str, float], expected_field: str
    ) -> None:
        with pytest.raises(DeckParameterError) as exc_info:
            DeckParameters(**kwargs)
        assert exc_info.value.parameter_name == expected_field

    @pytest.mark.parametrize("rake", [-1.0, 60.01, 90.0])
    def test_windshield_rake_out_of_range_rejected(self, rake: float) -> None:
        with pytest.raises(DeckParameterError) as exc_info:
            DeckParameters(windshield_rake=rake)
        assert exc_info.value.parameter_name == "windshield_rake"

    def test_hardtop_overhang_collapse_rejected(self) -> None:
        with pytest.raises(DeckParameterError) as exc_info:
            DeckParameters(
                hardtop_length=1.0,
                hardtop_overhang_fwd=0.5,
                hardtop_overhang_aft=0.6,
            )
        assert "hardtop" in exc_info.value.parameter_name
        assert exc_info.value.parameter_value is None


class TestFrozenness:
    def test_field_assignment_raises_frozen_instance_error(self) -> None:
        p = DeckParameters()
        with pytest.raises(dataclasses.FrozenInstanceError):
            p.cabin_trunk_length = 5.0  # type: ignore[misc]

    def test_hashable(self) -> None:
        assert hash(DeckParameters()) == hash(DeckParameters())

    def test_value_equal(self) -> None:
        assert DeckParameters() == DeckParameters()

    def test_different_values_not_equal(self) -> None:
        assert DeckParameters() != DeckParameters(cabin_trunk_length=5.0)
