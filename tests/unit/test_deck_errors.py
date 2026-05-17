"""Unit tests for DeckParameterError + DeckConstructionError (T013).

Covers FR-015 + SC-007 (≥5 invalid-input cases contributing to the 7+ total).
"""

from __future__ import annotations

import pytest

from storebro import (
    DeckConstructionError,
    DeckParameterError,
    DeckParameters,
)


class TestDeckParameterError:
    def test_subclasses_value_error(self) -> None:
        assert issubclass(DeckParameterError, ValueError)

    def test_attributes_set(self) -> None:
        err = DeckParameterError("railing_height", -0.5, "> 0")
        assert err.parameter_name == "railing_height"
        assert err.parameter_value == -0.5
        assert err.valid_range == "> 0"

    def test_cross_field_message_when_value_is_none(self) -> None:
        err = DeckParameterError(
            "hardtop_overhang_fwd+aft<>hardtop_length",
            None,
            "fwd + aft must be < length",
        )
        msg = str(err)
        assert "hardtop_overhang_fwd+aft<>hardtop_length" in msg
        assert "fwd + aft must be < length" in msg

    def test_invalid_railing_height_via_dataclass(self) -> None:
        with pytest.raises(DeckParameterError) as exc_info:
            DeckParameters(railing_height=-0.1)
        assert exc_info.value.parameter_name == "railing_height"

    def test_invalid_deck_plate_thickness(self) -> None:
        with pytest.raises(DeckParameterError) as exc_info:
            DeckParameters(deck_plate_thickness=0.0)
        assert exc_info.value.parameter_name == "deck_plate_thickness"

    def test_invalid_cabin_trunk_length(self) -> None:
        with pytest.raises(DeckParameterError) as exc_info:
            DeckParameters(cabin_trunk_length=0.0)
        assert exc_info.value.parameter_name == "cabin_trunk_length"

    def test_invalid_windshield_rake_above_max(self) -> None:
        with pytest.raises(DeckParameterError) as exc_info:
            DeckParameters(windshield_rake=61.0)
        assert exc_info.value.parameter_name == "windshield_rake"

    def test_invalid_windshield_rake_below_min(self) -> None:
        with pytest.raises(DeckParameterError) as exc_info:
            DeckParameters(windshield_rake=-1.0)
        assert exc_info.value.parameter_name == "windshield_rake"

    def test_invalid_hardtop_overhang_too_large(self) -> None:
        with pytest.raises(DeckParameterError) as exc_info:
            DeckParameters(
                hardtop_length=2.0,
                hardtop_overhang_fwd=1.0,
                hardtop_overhang_aft=1.0,  # fwd + aft >= length
            )
        assert "hardtop" in exc_info.value.parameter_name

    def test_invalid_negative_corner_radius(self) -> None:
        with pytest.raises(DeckParameterError) as exc_info:
            DeckParameters(cabin_trunk_corner_radius=-0.01)
        assert exc_info.value.parameter_name == "cabin_trunk_corner_radius"


class TestDeckConstructionError:
    def test_subclasses_runtime_error(self) -> None:
        assert issubclass(DeckConstructionError, RuntimeError)

    def test_version_check_attributes(self) -> None:
        err = DeckConstructionError(
            "unsupported FreeCAD version",
            detected_version=(0, 20),
            supported_range=">=1.1,<2.0",
        )
        assert err.detected_version == (0, 20)
        assert err.supported_range == ">=1.1,<2.0"
        assert err.parameters is None
        assert err.hull is None
        assert err.underlying is None

    def test_construction_failure_attributes(self) -> None:
        params = DeckParameters()
        underlying = RuntimeError("sketch failed")
        err = DeckConstructionError(
            "FreeCAD failed",
            parameters=params,
            hull=None,  # would be a Hull in real usage
            underlying=underlying,
        )
        assert err.parameters is params
        assert err.underlying is underlying
        assert err.detected_version is None

    def test_message_prefixed(self) -> None:
        err = DeckConstructionError("boom")
        assert "DeckConstructionError" in str(err)
        assert "boom" in str(err)
