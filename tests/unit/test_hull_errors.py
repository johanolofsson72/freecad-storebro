"""Unit tests for HullParameterError and HullConstructionError (T014).

Covers FR-004, FR-015, SC-007 (≥5 invalid-input cases).
"""

from __future__ import annotations

import pytest

from storebro import HullConstructionError, HullParameterError, HullParameters


class TestHullParameterError:
    def test_subclasses_value_error(self) -> None:
        assert issubclass(HullParameterError, ValueError)

    def test_attributes_set_by_init(self) -> None:
        err = HullParameterError("loa", -5.0, "> 0")
        assert err.parameter_name == "loa"
        assert err.parameter_value == -5.0
        assert err.valid_range == "> 0"

    def test_message_cites_field_value_and_range(self) -> None:
        err = HullParameterError("draft", 0.0, "> 0")
        msg = str(err)
        assert "draft" in msg
        assert "0.0" in msg or "0" in msg
        assert "> 0" in msg

    def test_cross_field_message_when_value_is_none(self) -> None:
        err = HullParameterError("loa<>beam_max", None, "loa must exceed beam_max")
        msg = str(err)
        assert "loa<>beam_max" in msg
        assert "loa must exceed beam_max" in msg

    def test_invalid_loa_raised_with_correct_payload(self) -> None:
        with pytest.raises(HullParameterError) as exc_info:
            HullParameters(loa=-1.0)
        assert exc_info.value.parameter_name == "loa"
        assert exc_info.value.parameter_value == -1.0
        assert exc_info.value.valid_range == "> 0"

    def test_invalid_beam_raised(self) -> None:
        with pytest.raises(HullParameterError) as exc_info:
            HullParameters(beam_max=0.0)
        assert exc_info.value.parameter_name == "beam_max"

    def test_invalid_draft_raised(self) -> None:
        with pytest.raises(HullParameterError) as exc_info:
            HullParameters(draft=-0.1)
        assert exc_info.value.parameter_name == "draft"

    def test_invalid_freeboard_raised(self) -> None:
        with pytest.raises(HullParameterError) as exc_info:
            HullParameters(freeboard=0.0)
        assert exc_info.value.parameter_name == "freeboard"

    def test_invalid_deadrise_above_max(self) -> None:
        with pytest.raises(HullParameterError) as exc_info:
            HullParameters(deadrise_amidships=31.0)
        assert exc_info.value.parameter_name == "deadrise_amidships"
        assert "30" in exc_info.value.valid_range

    def test_invalid_deadrise_below_min(self) -> None:
        with pytest.raises(HullParameterError) as exc_info:
            HullParameters(deadrise_amidships=-0.1)
        assert exc_info.value.parameter_name == "deadrise_amidships"

    def test_invalid_transom_angle_above_max(self) -> None:
        with pytest.raises(HullParameterError) as exc_info:
            HullParameters(transom_angle=46.0)
        assert exc_info.value.parameter_name == "transom_angle"

    def test_invalid_loa_le_beam_cross_field(self) -> None:
        with pytest.raises(HullParameterError) as exc_info:
            HullParameters(loa=3.0, beam_max=5.0)
        assert exc_info.value.parameter_name == "loa<>beam_max"
        assert exc_info.value.parameter_value is None

    def test_invalid_inverted_sheer_cross_field(self) -> None:
        with pytest.raises(HullParameterError) as exc_info:
            HullParameters(sheer_height_aft=1.5, sheer_height_fwd=1.0)
        assert exc_info.value.parameter_name == "sheer_height_fwd<>sheer_height_aft"


class TestHullConstructionError:
    def test_subclasses_runtime_error(self) -> None:
        assert issubclass(HullConstructionError, RuntimeError)

    def test_message_prefixed(self) -> None:
        err = HullConstructionError("boom")
        assert "HullConstructionError" in str(err)
        assert "boom" in str(err)

    def test_version_check_attributes(self) -> None:
        err = HullConstructionError(
            "unsupported FreeCAD version: 0.20",
            detected_version=(0, 20),
            supported_range=">=1.1,<2.0",
        )
        assert err.detected_version == (0, 20)
        assert err.supported_range == ">=1.1,<2.0"
        assert err.parameters is None
        assert err.underlying is None

    def test_construction_failure_attributes(self) -> None:
        params = HullParameters()
        underlying = RuntimeError("loft self-intersected")
        err = HullConstructionError(
            "FreeCAD failed", parameters=params, underlying=underlying
        )
        assert err.parameters is params
        assert err.underlying is underlying
        assert err.detected_version is None
        assert err.supported_range is None
