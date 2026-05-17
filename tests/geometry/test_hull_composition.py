"""Geometry test: user-document composition (T028).

Covers FR-016 contract guarantee 3 — a caller-supplied document is not
renamed and its top-level objects are not mutated.
"""

from __future__ import annotations

import FreeCAD  # type: ignore[import-not-found]

from storebro import build_hull


def test_user_supplied_document_name_preserved() -> None:
    doc = FreeCAD.newDocument("UserSuppliedDoc")
    original_name = doc.Name
    try:
        build_hull(document=doc)
        assert doc.Name == original_name
    finally:
        FreeCAD.closeDocument(doc.Name)


def test_user_supplied_document_existing_objects_not_mutated() -> None:
    doc = FreeCAD.newDocument("UserSuppliedDoc2")
    try:
        my_cube = doc.addObject("Part::Box", "MyCube")
        my_cube.Length = 1.0
        original_length = my_cube.Length
        build_hull(document=doc)
        # MyCube must still exist with its original Length.
        assert hasattr(doc, "MyCube")
        assert doc.MyCube.Length == original_length
    finally:
        FreeCAD.closeDocument(doc.Name)
