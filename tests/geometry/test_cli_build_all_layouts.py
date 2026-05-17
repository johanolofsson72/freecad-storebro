"""Geometry test: every canonical --layout builds successfully (T026).

Exhaustive coverage of Alternativ1..Alternativ5. Each layout must produce a
non-empty .FCStd.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storebro.cli import main

pytestmark = pytest.mark.requires_freecad


CANONICAL_LAYOUTS = (
    "Alternativ1",
    "Alternativ2",
    "Alternativ3",
    "Alternativ4",
    "Alternativ5",
)


@pytest.mark.parametrize("layout", CANONICAL_LAYOUTS)
def test_storebro_build_each_canonical_layout(
    layout: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / f"{layout}.FCStd"
    rc = main(["build", "--layout", layout, "--out", str(out)])
    captured = capsys.readouterr()
    assert rc == 0, f"layout {layout}: exit {rc}; stderr={captured.err!r}"
    assert out.is_file()
    assert out.stat().st_size > 0
