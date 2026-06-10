"""Geometry test: full-assembly export (spec 026 US1, T009).

Covers FR-001, SC-001, SC-003. A multi-body STEP/STL/BREP export reflects every
body (not just the hull) and is deterministic.
"""

from __future__ import annotations

import contextlib

import FreeCAD  # type: ignore[import-not-found]
import Part  # type: ignore[import-not-found]
import pytest

from storebro import build_deck, build_hull, export_brep, export_step, export_stl


def _bodies(doc):
    hull = build_hull(document=doc)
    deck = build_deck(hull)
    return hull, deck, [hull.body, deck.deck_plate.body]


@pytest.mark.requires_freecad
def test_step_assembly_contains_all_bodies(freecad_doc, tmp_path) -> None:
    hull, _deck, bodies = _bodies(freecad_doc)
    single = export_step(hull.body, tmp_path / "hull.step")
    asm = export_step(bodies, tmp_path / "asm.step")
    assert asm.byte_count > single.byte_count  # assembly is larger than the hull alone
    s = Part.Shape()
    s.read(str(tmp_path / "asm.step"))
    assert len(s.Solids) >= 2  # hull + deck plate, both present with geometry


@pytest.mark.requires_freecad
def test_stl_assembly_bbox_spans_all_bodies(freecad_doc, tmp_path) -> None:
    import Mesh

    hull, _deck, bodies = _bodies(freecad_doc)
    export_stl(bodies, tmp_path / "asm.stl")
    # The merged mesh's reimported bbox spans at least the hull's full extent.
    m = Mesh.Mesh(str(tmp_path / "asm.stl"))
    assert m.BoundBox.XLength >= hull.body.Shape.BoundBox.XLength - 1.0


@pytest.mark.requires_freecad
def test_assembly_determinism() -> None:
    import tempfile
    from pathlib import Path

    doc1 = FreeCAD.newDocument("Asm1")
    doc2 = FreeCAD.newDocument("Asm2")
    try:
        t = Path(tempfile.mkdtemp())
        h1 = build_hull(document=doc1)
        h2 = build_hull(document=doc2)
        b1 = [h1.body, build_deck(h1).deck_plate.body]
        b2 = [h2.body, build_deck(h2).deck_plate.body]
        for fmt, fn in (("step", export_step), ("brep", export_brep), ("stl", export_stl)):
            a1 = fn(b1, t / f"a1.{fmt}")
            a2 = fn(b2, t / f"a2.{fmt}")
            assert a1.sha256 == a2.sha256, f"{fmt}: assembly not deterministic"
    finally:
        for doc in (doc1, doc2):
            with contextlib.suppress(Exception):
                FreeCAD.closeDocument(doc.Name)
