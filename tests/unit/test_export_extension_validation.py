"""Unit test (no FreeCAD): spec 026 new-format extension + gzip validation (T006).

Covers FR-008 (extension validation) via `_resolve_target_path` directly.
"""

from __future__ import annotations

import pytest

from storebro import ExportInputError
from storebro.export import _resolve_target_path


def test_obj_iges_dxf_extensions_accepted(tmp_path) -> None:
    assert _resolve_target_path(tmp_path / "b.obj", "obj", True).suffix == ".obj"
    assert _resolve_target_path(tmp_path / "b.iges", "iges", True).suffix == ".iges"
    assert _resolve_target_path(tmp_path / "b.igs", "iges", True).suffix == ".igs"
    assert _resolve_target_path(tmp_path / "b.dxf", "dxf", True).suffix == ".dxf"


def test_wrong_extension_rejected(tmp_path) -> None:
    with pytest.raises(ExportInputError):
        _resolve_target_path(tmp_path / "b.step", "obj", True)
    with pytest.raises(ExportInputError):
        _resolve_target_path(tmp_path / "b.txt", "iges", True)


def test_gzip_requires_gz_suffix(tmp_path) -> None:
    # gzip=True with no .gz → rejected
    with pytest.raises(ExportInputError):
        _resolve_target_path(tmp_path / "b.stl", "stl", True, gzip_enabled=True)
    # gzip=True with .gz and correct inner extension → accepted
    p = _resolve_target_path(tmp_path / "b.stl.gz", "stl", True, gzip_enabled=True)
    assert p.suffix == ".gz"


def test_gz_suffix_without_gzip_rejected(tmp_path) -> None:
    with pytest.raises(ExportInputError):
        _resolve_target_path(tmp_path / "b.stl.gz", "stl", True, gzip_enabled=False)


def test_gzip_inner_extension_must_match(tmp_path) -> None:
    with pytest.raises(ExportInputError):
        _resolve_target_path(tmp_path / "b.obj.gz", "stl", True, gzip_enabled=True)
