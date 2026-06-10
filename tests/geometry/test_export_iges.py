"""Geometry test: IGES export (spec 026 US3, T014).

Covers FR-004, SC-002, SC-003. The global-section date is scrubbed so two
exports are byte-identical.
"""

from __future__ import annotations

import contextlib

import FreeCAD  # type: ignore[import-not-found]
import Part  # type: ignore[import-not-found]
import pytest

from storebro import build_deck, build_hull, export_iges


@pytest.mark.requires_freecad
def test_iges_valid_brep_for_body_and_assembly(freecad_doc, tmp_path) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    art = export_iges([hull.body, deck.deck_plate.body], tmp_path / "asm.iges")
    assert art.format == "iges" and art.byte_count > 0
    shape = Part.Shape()
    shape.read(str(tmp_path / "asm.iges"))  # re-imports as B-rep
    assert len(shape.Faces) > 0


@pytest.mark.requires_freecad
def test_iges_determinism_date_scrubbed() -> None:
    doc1 = FreeCAD.newDocument("Iges1")
    doc2 = FreeCAD.newDocument("Iges2")
    try:
        import tempfile
        from pathlib import Path

        t = Path(tempfile.mkdtemp())
        h1 = build_hull(document=doc1)
        h2 = build_hull(document=doc2)
        a1 = export_iges([h1.body, build_deck(h1).deck_plate.body], t / "a1.iges")
        a2 = export_iges([h2.body, build_deck(h2).deck_plate.body], t / "a2.iges")
        assert a1.sha256 == a2.sha256  # global-section date scrubbed
    finally:
        for doc in (doc1, doc2):
            with contextlib.suppress(Exception):
                FreeCAD.closeDocument(doc.Name)
