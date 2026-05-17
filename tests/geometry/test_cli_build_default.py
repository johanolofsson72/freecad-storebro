"""Geometry test: storebro build --out (T020, US1 MVP).

Covers the P1 user story end-to-end: a single `storebro build` invocation
produces a valid `.FCStd` file with hull + deck + interior composed.

Skipped when FreeCAD is not importable on the host (see geometry/conftest.py).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from storebro.cli import main

pytestmark = pytest.mark.requires_freecad


SUMMARY_PATTERN = re.compile(
    r"^wrote fcstd to (?P<path>.+) "
    r"\((?P<bytes>\d+) bytes, SHA-256 (?P<hash>[0-9a-f]{64})\)$"
)


def test_storebro_build_default_writes_fcstd(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """US1: `storebro build --out <path>` produces a non-empty .FCStd."""
    out = tmp_path / "boat.FCStd"
    rc = main(["build", "--out", str(out)])
    captured = capsys.readouterr()
    assert rc == 0, f"build exited {rc}; stderr={captured.err!r}"
    assert out.is_file(), f"missing output: {out}"
    assert out.stat().st_size > 0, "output is empty"

    summary_line = captured.out.strip().splitlines()[-1]
    match = SUMMARY_PATTERN.match(summary_line)
    assert match is not None, f"summary line did not match FR-006 pattern: {summary_line!r}"
    assert match.group("path") == str(out.resolve())
    assert int(match.group("bytes")) == out.stat().st_size
