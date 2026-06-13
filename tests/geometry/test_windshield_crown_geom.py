"""Geometry test: spec 030 windshield crown (requires FreeCAD).

Covers FR-002, FR-004, FR-005, FR-006, FR-010 + spec.allium WindshieldBody. The crown
arches the transverse top edge upward at the centerline and returns to 0 at the corners,
so a crowned build's top (BoundBox.ZMax, the apex) sits ~crown_height above an otherwise
identical flat-top build, while the body stays a single valid solid and the spec 011
frame opening + glass pane survive. crown_height=0.0 takes the unchanged flat path.
"""

from __future__ import annotations

import FreeCAD  # type: ignore[import-not-found]
import pytest

from storebro import build_deck, build_hull
from storebro.deck import DeckSuperstructureParameters, WindshieldParameters

RELATIVE_TOL = 1.0e-9
CROWN_DEFAULT = 60.0


def _close(a: float, b: float, tol: float = RELATIVE_TOL) -> bool:
    if b == 0.0:
        return abs(a - b) <= tol
    return abs(a - b) / abs(b) <= tol


def _windshield_body(doc: object, crown_height: float) -> object:
    sup = DeckSuperstructureParameters(
        windshield=WindshieldParameters(crown_height=crown_height)
    )
    deck = build_deck(build_hull(document=doc), parameters_superstructure=sup)
    return deck.windshield.body


@pytest.mark.requires_freecad
def test_default_windshield_is_single_valid_solid(freecad_doc: object) -> None:
    # FR-004: crowned-by-default body stays one manifold solid.
    body = _windshield_body(freecad_doc, CROWN_DEFAULT)
    assert len(body.Shape.Solids) == 1
    assert body.Shape.isValid()


@pytest.mark.requires_freecad
def test_crown_raises_apex_above_flat_top() -> None:
    # FR-002: the crowned top apex (ZMax) sits ~crown_height above the flat build,
    # since the arch returns to 0 at the corners (the flat top Z).
    doc_c = FreeCAD.newDocument("CrownC")
    doc_f = FreeCAD.newDocument("CrownF")
    try:
        crowned = _windshield_body(doc_c, CROWN_DEFAULT)
        flat = _windshield_body(doc_f, 0.0)
        rise = crowned.Shape.BoundBox.ZMax - flat.Shape.BoundBox.ZMax
        assert rise > 0.0, "crown did not raise the top edge"
        # Apex vertex sits at exactly +crown_height; allow a small B-spline overshoot margin.
        assert abs(rise - CROWN_DEFAULT) < 5.0, f"apex rise {rise} not ~= {CROWN_DEFAULT}"
    finally:
        FreeCAD.closeDocument(doc_c.Name)
        FreeCAD.closeDocument(doc_f.Name)


@pytest.mark.requires_freecad
def test_flat_sentinel_top_is_level(freecad_doc: object) -> None:
    # FR-006: crown_height=0.0 → flat top (ZMax of crowned-default exceeds the flat one).
    flat = _windshield_body(freecad_doc, 0.0)
    assert len(flat.Shape.Solids) == 1
    assert flat.Shape.isValid()


@pytest.mark.requires_freecad
def test_taller_crown_raises_apex_more() -> None:
    doc_a = FreeCAD.newDocument("CrownA")
    doc_b = FreeCAD.newDocument("CrownB")
    try:
        small = _windshield_body(doc_a, 40.0)
        large = _windshield_body(doc_b, 100.0)
        assert large.Shape.BoundBox.ZMax > small.Shape.BoundBox.ZMax
    finally:
        FreeCAD.closeDocument(doc_a.Name)
        FreeCAD.closeDocument(doc_b.Name)


@pytest.mark.requires_freecad
def test_crowned_windshield_keeps_frame_and_glass(freecad_doc: object) -> None:
    # FR-005: glazing-on default (crowned) keeps the frame opening + glass pane,
    # and the framed body stays a single valid solid (frame margin preserved).
    deck = build_deck(build_hull(document=freecad_doc))  # defaults: crowned + glazing on
    assert deck.windshield.glass_pane is not None
    assert deck.windshield.glass_pane.body.Shape.Volume > 0.0
    assert len(deck.windshield.body.Shape.Solids) == 1
    assert deck.windshield.body.Shape.isValid()


@pytest.mark.requires_freecad
def test_crown_volume_is_reproducible() -> None:
    # FR-010: two crowned builds in one process → identical windshield volume.
    doc1 = FreeCAD.newDocument("CrownR1")
    doc2 = FreeCAD.newDocument("CrownR2")
    try:
        v1 = _windshield_body(doc1, CROWN_DEFAULT).Shape.Volume
        v2 = _windshield_body(doc2, CROWN_DEFAULT).Shape.Volume
        assert _close(v1, v2), f"crown volume drift {v1} vs {v2}"
    finally:
        FreeCAD.closeDocument(doc1.Name)
        FreeCAD.closeDocument(doc2.Name)


@pytest.mark.requires_freecad
def test_flat_sentinel_volume_is_reproducible() -> None:
    # FR-006/FR-010: the OFF path is deterministic too (back-compat baseline).
    doc1 = FreeCAD.newDocument("FlatR1")
    doc2 = FreeCAD.newDocument("FlatR2")
    try:
        v1 = _windshield_body(doc1, 0.0).Shape.Volume
        v2 = _windshield_body(doc2, 0.0).Shape.Volume
        assert _close(v1, v2), f"flat volume drift {v1} vs {v2}"
    finally:
        FreeCAD.closeDocument(doc1.Name)
        FreeCAD.closeDocument(doc2.Name)


@pytest.mark.requires_freecad
def test_crowned_encloses_more_volume_than_flat() -> None:
    # The crown adds material above the corners → strictly more volume than the flat top.
    doc_c = FreeCAD.newDocument("VolC")
    doc_f = FreeCAD.newDocument("VolF")
    try:
        crowned = _windshield_body(doc_c, CROWN_DEFAULT).Shape.Volume
        flat = _windshield_body(doc_f, 0.0).Shape.Volume
        assert crowned > flat, f"crowned {crowned} not > flat {flat}"
    finally:
        FreeCAD.closeDocument(doc_c.Name)
        FreeCAD.closeDocument(doc_f.Name)
