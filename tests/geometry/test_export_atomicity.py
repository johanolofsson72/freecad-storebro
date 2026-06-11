"""Geometry test: atomic write across writers (T041).

Covers FR-008. Each writer monkeypatched to force a FreeCAD-side failure
mid-write; the test asserts no partial file at target AND no leftover tmp.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import storebro.export as export_mod
from storebro import ExportWriteError, build_hull, export_brep, export_step, export_stl


def _no_partial_file(target: Path, prefix_pattern: str) -> None:
    assert not target.exists(), f"FR-008 violation: partial file at {target}"
    leftovers = list(target.parent.glob(prefix_pattern))
    assert leftovers == [], f"FR-008 violation: leftover tmp files {leftovers}"


def test_step_freecad_failure_no_partial(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    hull = build_hull()
    out = tmp_path / "fail.step"

    # spec 026: export_step now writes via the Shape method (canonical.exportStep),
    # not the geometry-less Part.export path. Part.Shape is immutable, so force the
    # failure inside the try block via the module helper (same as the brep test).
    def boom(*a: object, **k: object) -> None:
        raise RuntimeError("forced (test)")

    monkeypatch.setattr(export_mod, "_sorted_subshapes", boom)

    with pytest.raises(ExportWriteError):
        export_step(hull.body, out)
    _no_partial_file(out, ".fail.step.*")


def test_brep_freecad_failure_no_partial(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    hull = build_hull()
    out = tmp_path / "fail.brep"

    def boom(*a: object, **k: object) -> None:
        raise RuntimeError("forced (test)")

    # exportBrep is a method on Shape, not a module-level function; monkeypatch
    # via the export module's _sorted_subshapes to return a mock shape whose
    # exportBrep raises.
    class FakeShape:
        def exportBrep(self, _: str) -> None:
            raise RuntimeError("forced (test)")

    monkeypatch.setattr(export_mod, "_sorted_subshapes", lambda s: FakeShape())

    with pytest.raises(ExportWriteError):
        export_brep(hull.body, out)
    _no_partial_file(out, ".fail.brep.*")


def test_stl_meshing_failure_no_partial(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    hull = build_hull()
    out = tmp_path / "fail.stl"

    def boom(*a: object, **k: object) -> None:
        raise RuntimeError("forced (test)")

    monkeypatch.setattr(export_mod, "_build_canonical_mesh", boom)

    with pytest.raises(ExportWriteError):
        export_stl(hull.body, out)
    _no_partial_file(out, ".fail.stl.*")
