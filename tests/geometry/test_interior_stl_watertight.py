"""Geometry test: furnished interior still exports watertight STL (T022).

Covers spec 012 SC-002 — the galley boolean cut must not break STL export.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storebro import build_deck, build_hull, build_interior, export_stl


@pytest.mark.requires_freecad
def test_furnished_model_stl(freecad_doc: object, tmp_path: Path) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout="Alternativ1")
    out = tmp_path / "furnished.stl"
    artifact = export_stl(interior.document, str(out))
    assert out.is_file()
    assert artifact.byte_count > 0
    galley = next(c for c in interior.compartments if c.spec.compartment_type == "galley")
    assert len(galley.furniture[0].Shape.Solids) == 1
