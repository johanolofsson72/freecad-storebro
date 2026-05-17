"""Geometry test: storebro build rejects unknown layout (T022, SC-007).

Covers the third US1 acceptance scenario: an invalid layout name surfaces
spec 004's InteriorParameterError as exit code 1 with a clear error message
on stderr that names the offending argument.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storebro.cli import main

pytestmark = pytest.mark.requires_freecad


def test_storebro_build_unknown_layout_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """SC-007: invalid layout → exit 1 + error message naming the offender."""
    out = tmp_path / "x.FCStd"
    rc = main(["build", "--layout", "BogusLayout", "--out", str(out)])
    captured = capsys.readouterr()
    assert rc == 1, f"expected exit 1 for invalid layout, got {rc}"
    assert "error:" in captured.err
    assert "BogusLayout" in captured.err
    assert not out.exists(), "no file should be written on failure"
