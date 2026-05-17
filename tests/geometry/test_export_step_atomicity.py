"""Geometry test: STEP atomic write — no partial file on failure (T020).

Covers FR-008.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storebro import ExportWriteError, build_hull, export_step


def test_freecad_failure_leaves_no_partial_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import Part  # type: ignore[import-not-found]

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("forced FreeCAD failure (test)")

    monkeypatch.setattr(Part, "export", boom)

    hull = build_hull()
    out = tmp_path / "should_not_exist.step"
    with pytest.raises(ExportWriteError):
        export_step(hull.body, out)
    assert not out.exists(), "FR-008: failed write must not leave partial file"
    # No leftover tmp files either.
    leftovers = list(tmp_path.glob(".should_not_exist.step.*"))
    assert leftovers == [], f"leftover temp files: {leftovers}"
