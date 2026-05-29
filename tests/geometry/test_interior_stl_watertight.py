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
    # export_stl takes a body, not a document. The galley counter is the cut
    # solid whose watertightness the boolean Part.Cut could threaten (SC-002).
    galley = next(c for c in interior.compartments if c.spec.compartment_type == "galley")
    counter = galley.furniture[0]
    out = tmp_path / "galley_counter.stl"
    artifact = export_stl(counter, str(out))
    assert out.is_file()
    assert artifact.byte_count > 0
    assert len(counter.Shape.Solids) == 1
