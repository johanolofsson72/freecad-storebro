"""Unit tests for path/extension/overwrite validation (T013).

Covers FR-006 + FR-009 + SC-006 (≥5 invalid-input cases).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storebro import ExportInputError
from storebro.export import _resolve_target_path, _resolve_tessellation_tolerance


def test_resolve_target_path_rejects_missing_parent(tmp_path: Path) -> None:
    with pytest.raises(ExportInputError) as exc_info:
        _resolve_target_path(tmp_path / "no_such_dir" / "out.step", "step", True)
    assert exc_info.value.field == "target_path"
    assert "parent" in exc_info.value.reason


def test_resolve_target_path_rejects_target_is_directory(tmp_path: Path) -> None:
    sub = tmp_path / "subdir"
    sub.mkdir()
    with pytest.raises(ExportInputError) as exc_info:
        _resolve_target_path(sub, "step", True)
    assert exc_info.value.field == "target_path"
    assert "directory" in exc_info.value.reason


@pytest.mark.parametrize(
    "filename,format_key,reason_must_contain",
    [
        ("out.txt", "step", "extension"),
        ("out.dat", "stl", "extension"),
        ("out.zip", "brep", "extension"),
        ("out.bin", "fcstd", "extension"),
        ("noextension", "step", "extension"),
    ],
)
def test_resolve_target_path_rejects_wrong_extension(
    tmp_path: Path, filename: str, format_key: str, reason_must_contain: str
) -> None:
    with pytest.raises(ExportInputError) as exc_info:
        _resolve_target_path(tmp_path / filename, format_key, True)
    assert exc_info.value.field == "target_path"
    assert reason_must_contain in exc_info.value.reason


def test_resolve_target_path_accepts_valid_step(tmp_path: Path) -> None:
    out = _resolve_target_path(tmp_path / "out.step", "step", True)
    assert out.suffix == ".step"


def test_resolve_target_path_accepts_stp_alias(tmp_path: Path) -> None:
    out = _resolve_target_path(tmp_path / "out.stp", "step", True)
    assert out.suffix == ".stp"


def test_resolve_target_path_accepts_brep_aliases(tmp_path: Path) -> None:
    a = _resolve_target_path(tmp_path / "out.brep", "brep", True)
    b = _resolve_target_path(tmp_path / "out.brp", "brep", True)
    assert a.suffix == ".brep"
    assert b.suffix == ".brp"


def test_resolve_target_path_accepts_fcstd_case_preserved(tmp_path: Path) -> None:
    a = _resolve_target_path(tmp_path / "out.FCStd", "fcstd", True)
    b = _resolve_target_path(tmp_path / "out.fcstd", "fcstd", True)
    assert a.suffix == ".FCStd"
    assert b.suffix == ".fcstd"


def test_resolve_target_path_rejects_existing_file_when_no_overwrite(
    tmp_path: Path,
) -> None:
    existing = tmp_path / "out.step"
    existing.write_text("placeholder")
    with pytest.raises(ExportInputError) as exc_info:
        _resolve_target_path(existing, "step", False)
    assert exc_info.value.field == "target_path"
    assert "overwrite" in exc_info.value.reason


def test_resolve_target_path_allows_existing_file_with_overwrite_true(
    tmp_path: Path,
) -> None:
    existing = tmp_path / "out.step"
    existing.write_text("placeholder")
    out = _resolve_target_path(existing, "step", True)
    assert out == existing.resolve()


def test_resolve_target_path_rejects_empty_string() -> None:
    with pytest.raises(ExportInputError) as exc_info:
        _resolve_target_path("", "step", True)
    assert exc_info.value.field == "target_path"


class TestTessellationTolerance:
    def test_rejects_zero(self) -> None:
        with pytest.raises(ExportInputError) as exc_info:
            _resolve_tessellation_tolerance(0.0)
        assert exc_info.value.field == "tessellation_tolerance"

    def test_rejects_negative(self) -> None:
        with pytest.raises(ExportInputError):
            _resolve_tessellation_tolerance(-0.001)

    def test_rejects_nan(self) -> None:
        with pytest.raises(ExportInputError):
            _resolve_tessellation_tolerance(float("nan"))

    def test_accepts_default(self) -> None:
        assert _resolve_tessellation_tolerance(0.001) == 0.001

    def test_accepts_small_positive(self) -> None:
        assert _resolve_tessellation_tolerance(1e-6) == 1e-6

    def test_rejects_non_numeric(self) -> None:
        with pytest.raises(ExportInputError):
            _resolve_tessellation_tolerance("0.001")  # type: ignore[arg-type]
