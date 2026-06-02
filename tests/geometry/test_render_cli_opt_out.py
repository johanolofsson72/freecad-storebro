"""Geometry tests: --no-colors opt-out + export invariance (spec 015 T012).

Covers FR-008, FR-009, FR-012 and contract invariant 4: disabling coloring
leaves no Render data properties, and appearance-free exports (STEP/STL/BREP)
are byte-identical with or without colors.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import FreeCAD  # type: ignore[import-not-found]

from storebro import build_deck, build_hull, build_propulsion, export_step, export_stl


def test_disabled_adds_no_render_properties(freecad_doc: Any) -> None:
    hull = build_hull(document=freecad_doc, apply_render_attributes=False)
    deck = build_deck(hull, apply_render_attributes=False)
    prop = build_propulsion(hull, deck, apply_render_attributes=False)

    bodies = [
        hull.body,
        deck.deck_plate.body,
        deck.rubrail.body,
        *(e.body for e in prop.engines),
        *(p.body for p in prop.propellers),
    ]
    for body in bodies:
        assert "RenderColor" not in body.PropertiesList, body.Label
        assert "RenderMaterialName" not in body.PropertiesList, body.Label


def test_default_build_does_add_render_properties(freecad_doc: Any) -> None:
    hull = build_hull(document=freecad_doc)  # default on
    assert "RenderColor" in hull.body.PropertiesList


def test_step_export_byte_identical_regardless_of_colours(tmp_path: Path) -> None:
    """STEP carries no appearance → colour toggle must not change the bytes."""
    doc_c = FreeCAD.newDocument("colour_on")
    try:
        hull_c = build_hull(document=doc_c, apply_render_attributes=True)
        art_c = export_step(hull_c.body, str(tmp_path / "on.step"))
    finally:
        FreeCAD.closeDocument(doc_c.Name)

    doc_n = FreeCAD.newDocument("colour_off")
    try:
        hull_n = build_hull(document=doc_n, apply_render_attributes=False)
        art_n = export_step(hull_n.body, str(tmp_path / "off.step"))
    finally:
        FreeCAD.closeDocument(doc_n.Name)

    assert art_c.sha256 == art_n.sha256


def test_stl_export_byte_identical_regardless_of_colours(tmp_path: Path) -> None:
    doc_c = FreeCAD.newDocument("stl_on")
    try:
        hull_c = build_hull(document=doc_c, apply_render_attributes=True)
        art_c = export_stl(hull_c.body, str(tmp_path / "on.stl"))
    finally:
        FreeCAD.closeDocument(doc_c.Name)

    doc_n = FreeCAD.newDocument("stl_off")
    try:
        hull_n = build_hull(document=doc_n, apply_render_attributes=False)
        art_n = export_stl(hull_n.body, str(tmp_path / "off.stl"))
    finally:
        FreeCAD.closeDocument(doc_n.Name)

    assert art_c.sha256 == art_n.sha256
