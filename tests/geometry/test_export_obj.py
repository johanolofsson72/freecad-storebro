"""Geometry test: OBJ export (spec 026 US2, T012).

Covers FR-003, SC-002, SC-003.
"""

from __future__ import annotations

import contextlib

import FreeCAD  # type: ignore[import-not-found]
import pytest

from storebro import build_deck, build_hull, export_obj


@pytest.mark.requires_freecad
def test_obj_valid_for_body_and_assembly(freecad_doc, tmp_path) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    for label, target in (
        (hull.body, tmp_path / "single.obj"),
        ([hull.body, deck.deck_plate.body], tmp_path / "asm.obj"),
    ):
        art = export_obj(label, target)
        assert art.format == "obj" and art.byte_count > 0
        text = target.read_text()
        assert "\nv " in ("\n" + text)  # vertices present
        assert "\nf " in ("\n" + text)  # faces present


@pytest.mark.requires_freecad
def test_obj_determinism() -> None:
    doc1 = FreeCAD.newDocument("Obj1")
    doc2 = FreeCAD.newDocument("Obj2")
    try:
        import tempfile
        from pathlib import Path

        t = Path(tempfile.mkdtemp())
        h1 = build_hull(document=doc1)
        h2 = build_hull(document=doc2)
        a1 = export_obj([h1.body, build_deck(h1).deck_plate.body], t / "a1.obj")
        a2 = export_obj([h2.body, build_deck(h2).deck_plate.body], t / "a2.obj")
        assert a1.sha256 == a2.sha256
    finally:
        for doc in (doc1, doc2):
            with contextlib.suppress(Exception):
                FreeCAD.closeDocument(doc.Name)
