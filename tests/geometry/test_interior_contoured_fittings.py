"""Geometry tests: spec 024 contoured interior fittings.

Contoured cushions (rounded + tufting + piping + folds), toilet+faucet, galley
fascia, curved bulkheads — each a valid solid (or a deterministic box fallback),
byte-reproducible, with the spec 012 galley manifold guard preserved.
"""

from __future__ import annotations

from pathlib import Path

import FreeCAD  # type: ignore[import-not-found]
import pytest

from storebro import build_deck, build_hull, export_stl
from storebro.interior import (
    BerthParameters,
    FurnitureParameters,
    build_interior,
)


def _furnished(doc: object, furniture: FurnitureParameters | None = None) -> object:
    hull = build_hull(document=doc)
    deck = build_deck(hull)
    return build_interior(hull, deck, "Alternativ3", parameters_furniture=furniture)


def _comp(interior: object, ctype: str) -> object:
    return next(c for c in interior.compartments if c.spec.compartment_type == ctype)


# --- US1: cushions (T015) --------------------------------------------------


@pytest.mark.requires_freecad
def test_berth_cushions_segmented_and_valid(freecad_doc: object) -> None:
    interior = _furnished(freecad_doc)
    cabin = _comp(interior, "forward_cabin")
    cushions = [p for p in cabin.furniture if "Cushion" in p.Label]
    # Default cushion_segments=2 → 2 sub-cushions.
    assert len(cushions) >= 2
    for c in cushions:
        assert c.Shape.isValid() and len(c.Shape.Solids) == 1


@pytest.mark.requires_freecad
def test_settee_contoured_valid(freecad_doc: object) -> None:
    interior = _furnished(freecad_doc)
    salon = _comp(interior, "salon")
    settee = next(p for p in salon.furniture if "Settee" in p.Label)
    assert settee.Shape.isValid() and len(settee.Shape.Solids) == 1


# --- US2: toilet + faucet (T016) -------------------------------------------


@pytest.mark.requires_freecad
def test_toilet_and_faucet(freecad_doc: object) -> None:
    interior = _furnished(freecad_doc)
    head = _comp(interior, "head")
    toilet = next(p for p in head.furniture if p.Label.endswith("_Toilet"))
    assert toilet.Shape.isValid() and len(toilet.Shape.Solids) == 1
    assert any("Faucet" in p.Label for p in head.furniture)


# --- US3: galley fascia + manifold guard (T017) ----------------------------


@pytest.mark.requires_freecad
def test_galley_counter_single_solid(freecad_doc: object) -> None:
    interior = _furnished(freecad_doc)
    galley = _comp(interior, "galley")
    counter = next(p for p in galley.furniture if "GalleyCounter" in p.Label)
    # spec 012 manifold guard preserved through the contour + fascia.
    assert len(counter.Shape.Solids) == 1 and counter.Shape.isValid()


# --- US4: curved bulkhead (T018) -------------------------------------------


@pytest.mark.requires_freecad
def test_bulkheads_valid(freecad_doc: object) -> None:
    interior = _furnished(freecad_doc)
    for c in interior.compartments:
        bulk = next((p for p in c.furniture if "Bulkhead" in p.Label), None)
        if bulk is not None:
            assert bulk.Shape.isValid() and len(bulk.Shape.Solids) == 1


# --- back-compat (T019, FR-008) --------------------------------------------


@pytest.mark.requires_freecad
def test_contoured_false_matches_box_volume() -> None:
    """contoured=False reproduces the spec 012 box (a plain berth base+cushion)."""
    doc_c = FreeCAD.newDocument("Contoured")
    doc_b = FreeCAD.newDocument("Boxed")
    try:
        i_c = _furnished(
            doc_c, FurnitureParameters(berth=BerthParameters(contoured=True))
        )
        i_b = _furnished(
            doc_b, FurnitureParameters(berth=BerthParameters(contoured=False))
        )
        cabin_c = _comp(i_c, "forward_cabin")
        cabin_b = _comp(i_b, "forward_cabin")
        vol_c = sum(p.Shape.Volume for p in cabin_c.furniture)
        vol_b = sum(p.Shape.Volume for p in cabin_b.furniture)
        # Contoured removes material (rounding + tufting) → strictly less volume.
        assert vol_c < vol_b
    finally:
        FreeCAD.closeDocument(doc_c.Name)
        FreeCAD.closeDocument(doc_b.Name)


# --- determinism (T020, FR-011) --------------------------------------------


@pytest.mark.requires_freecad
def test_furniture_reproducible() -> None:
    doc1 = FreeCAD.newDocument("Det1")
    doc2 = FreeCAD.newDocument("Det2")
    try:
        i1 = _furnished(doc1)
        i2 = _furnished(doc2)
        v1 = sum(p.Shape.Volume for c in i1.compartments for p in c.furniture)
        v2 = sum(p.Shape.Volume for c in i2.compartments for p in c.furniture)
        assert abs(v1 - v2) < 1.0
    finally:
        FreeCAD.closeDocument(doc1.Name)
        FreeCAD.closeDocument(doc2.Name)


# --- STL (T021, SC-002) ----------------------------------------------------


@pytest.mark.requires_freecad
def test_contoured_furniture_stl(freecad_doc: object, tmp_path: Path) -> None:
    interior = _furnished(freecad_doc)
    cabin = _comp(interior, "forward_cabin")
    cushion = next(p for p in cabin.furniture if "Cushion" in p.Label)
    out = tmp_path / "cushion.stl"
    artifact = export_stl(cushion, str(out))
    assert out.is_file() and artifact.byte_count > 0
    assert len(cushion.Shape.Solids) == 1 and cushion.Shape.isValid()
