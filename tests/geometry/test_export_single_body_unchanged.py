"""Geometry test: single-body export stays deterministic (spec 026 T010).

Covers SC-005, FR-010. STL/BREP single-body output is unchanged + deterministic;
STEP single-body now contains real B-rep geometry (the spec 026 bugfix to the
spec 002 `Part.export`-of-a-raw-shape path) and is deterministic.
"""

from __future__ import annotations

import contextlib

import FreeCAD  # type: ignore[import-not-found]
import Part  # type: ignore[import-not-found]
import pytest

from storebro import build_hull, export_brep, export_step, export_stl


@pytest.mark.requires_freecad
def test_step_single_body_now_has_geometry(freecad_doc, tmp_path) -> None:
    hull = build_hull(document=freecad_doc)
    art = export_step(hull.body, tmp_path / "hull.step")
    assert art.byte_count > 0
    shape = Part.Shape()
    shape.read(str(tmp_path / "hull.step"))  # would raise / be empty pre-fix
    assert len(shape.Faces) == len(hull.body.Shape.Faces)  # full B-rep round-trips


@pytest.mark.requires_freecad
@pytest.mark.parametrize(("fn", "ext"), [(export_step, "step"), (export_brep, "brep"), (export_stl, "stl")])
def test_single_body_deterministic(fn, ext) -> None:
    doc1 = FreeCAD.newDocument("Single1")
    doc2 = FreeCAD.newDocument("Single2")
    try:
        import tempfile
        from pathlib import Path

        t = Path(tempfile.mkdtemp())
        a1 = fn(build_hull(document=doc1).body, t / f"a1.{ext}")
        a2 = fn(build_hull(document=doc2).body, t / f"a2.{ext}")
        assert a1.sha256 == a2.sha256
    finally:
        for doc in (doc1, doc2):
            with contextlib.suppress(Exception):
                FreeCAD.closeDocument(doc.Name)
