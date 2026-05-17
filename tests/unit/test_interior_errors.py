"""Unit tests for InteriorParameterError + InteriorConstructionError (T019)."""

from __future__ import annotations

from storebro import InteriorConstructionError, InteriorParameterError


class TestInteriorParameterError:
    def test_subclasses_value_error(self) -> None:
        assert issubclass(InteriorParameterError, ValueError)

    def test_message_with_all_fields(self) -> None:
        err = InteriorParameterError(
            "Alternativ3", "Salon", "dimensions.length", "must be > 0"
        )
        msg = str(err)
        assert "Alternativ3" in msg
        assert "Salon" in msg
        assert "dimensions.length" in msg
        assert "must be > 0" in msg

    def test_message_with_compartment_only(self) -> None:
        err = InteriorParameterError("file.yaml", "Salon", None, "is broken")
        assert err.compartment_name == "Salon"
        assert err.field is None
        assert "Salon" in str(err)

    def test_message_top_level(self) -> None:
        err = InteriorParameterError("file.yaml", None, None, "top-level error")
        assert err.compartment_name is None
        assert err.field is None
        assert "top-level error" in str(err)

    def test_attributes_set(self) -> None:
        err = InteriorParameterError("src", "Cabin", "position.y", "non-zero")
        assert err.source == "src"
        assert err.compartment_name == "Cabin"
        assert err.field == "position.y"
        assert err.reason == "non-zero"


class TestInteriorConstructionError:
    def test_subclasses_runtime_error(self) -> None:
        assert issubclass(InteriorConstructionError, RuntimeError)

    def test_message_prefixed(self) -> None:
        err = InteriorConstructionError("boom")
        assert "InteriorConstructionError" in str(err)
        assert "boom" in str(err)

    def test_version_check_attributes(self) -> None:
        err = InteriorConstructionError(
            "unsupported",
            detected_version=(0, 20),
            supported_range=">=1.1,<2.0",
        )
        assert err.detected_version == (0, 20)
        assert err.supported_range == ">=1.1,<2.0"
        assert err.layout_name is None

    def test_construction_failure_attributes(self) -> None:
        underlying = RuntimeError("forced")
        err = InteriorConstructionError(
            "FreeCAD failed",
            layout_name="Alternativ3",
            underlying=underlying,
        )
        assert err.layout_name == "Alternativ3"
        assert err.underlying is underlying
