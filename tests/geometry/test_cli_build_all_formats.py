"""Geometry test: every --format value writes successfully (T025).

Exhaustive coverage of fcstd, step, stl, brep. Each invocation must exit 0
and produce a non-empty file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storebro.cli import main

pytestmark = pytest.mark.requires_freecad


_FORMAT_EXT = {
    "fcstd": "FCStd",
    "step": "step",
    "stl": "stl",
    "brep": "brep",
}


@pytest.mark.parametrize("fmt", list(_FORMAT_EXT.keys()))
def test_storebro_build_writes_each_format(
    fmt: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / f"boat.{_FORMAT_EXT[fmt]}"
    rc = main(["build", "--format", fmt, "--out", str(out)])
    captured = capsys.readouterr()
    assert rc == 0, f"format {fmt}: exit {rc}; stderr={captured.err!r}"
    assert out.is_file()
    assert out.stat().st_size > 0
