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
    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("forced FreeCAD failure (test)")

    # spec 026: export_step writes via the Shape method (canonical.exportStep);
    # Part.Shape is immutable, so force the failure inside the try block via a
    # module helper to exercise the same atomic-cleanup path.
    monkeypatch.setattr("storebro.export._sorted_subshapes", boom)

    hull = build_hull()
    out = tmp_path / "should_not_exist.step"
    with pytest.raises(ExportWriteError):
        export_step(hull.body, out)
    assert not out.exists(), "FR-008: failed write must not leave partial file"
    # No leftover tmp files either.
    leftovers = list(tmp_path.glob(".should_not_exist.step.*"))
    assert leftovers == [], f"leftover temp files: {leftovers}"
