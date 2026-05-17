"""Unit tests for ExportInputError + ExportWriteError (T012).

Covers FR-007 + SC-006 (≥5 invalid-input cases). Pure Python.
"""

from __future__ import annotations

from pathlib import Path

from storebro import ExportInputError, ExportWriteError


class TestExportInputError:
    def test_subclasses_value_error(self) -> None:
        assert issubclass(ExportInputError, ValueError)

    def test_attributes_set_by_init(self) -> None:
        err = ExportInputError("target_path", "parent directory does not exist", "/no/such/dir")
        assert err.field == "target_path"
        assert err.reason == "parent directory does not exist"
        assert err.offending_value == "/no/such/dir"

    def test_message_cites_field_reason_and_value(self) -> None:
        err = ExportInputError("body", "shape is null", repr(None))
        msg = str(err)
        assert "body" in msg
        assert "shape is null" in msg
        assert "None" in msg

    def test_message_without_offending_value(self) -> None:
        err = ExportInputError("document", "must not be None")
        msg = str(err)
        assert "document" in msg
        assert "must not be None" in msg
        # No "(got: ...)" suffix when offending_value is None.
        assert "got:" not in msg

    def test_attribute_offending_value_none_when_omitted(self) -> None:
        err = ExportInputError("foo", "bar")
        assert err.offending_value is None


class TestExportWriteError:
    def test_subclasses_runtime_error(self) -> None:
        assert issubclass(ExportWriteError, RuntimeError)

    def test_attributes_for_filesystem_failure(self) -> None:
        underlying = OSError("disk full")
        err = ExportWriteError(
            "failed to write /tmp/x.step",
            target_path=Path("/tmp/x.step"),
            underlying=underlying,
            format="step",
        )
        assert err.target_path == Path("/tmp/x.step")
        assert "disk full" in err.underlying_message
        assert err.format == "step"
        assert err.detected_version is None
        assert err.supported_range is None

    def test_attributes_for_version_check_failure(self) -> None:
        err = ExportWriteError(
            "unsupported FreeCAD",
            detected_version=(0, 20),
            supported_range=">=1.1,<2.0",
        )
        assert err.detected_version == (0, 20)
        assert err.supported_range == ">=1.1,<2.0"
        assert err.target_path is None
        assert err.format is None

    def test_message_prefixed(self) -> None:
        err = ExportWriteError("boom")
        assert "ExportWriteError" in str(err)
        assert "boom" in str(err)
