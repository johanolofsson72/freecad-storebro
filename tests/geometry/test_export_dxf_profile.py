"""Geometry test: 2D DXF profile export (spec 026 US5, T016).

Covers FR-005, SC-002, SC-003, SC-007.
"""

from __future__ import annotations

import pytest

from storebro import ExportInputError, build_deck, build_hull, export_dxf_profile


@pytest.mark.requires_freecad
def test_dxf_profile_valid_and_deterministic(freecad_doc, tmp_path) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    bodies = [hull.body, deck.deck_plate.body]
    a1 = export_dxf_profile(bodies, tmp_path / "p1.dxf")
    a2 = export_dxf_profile(bodies, tmp_path / "p2.dxf")
    assert a1.format == "dxf" and a1.byte_count > 0
    text = (tmp_path / "p1.dxf").read_text()
    assert "ENTITIES" in text and "LINE" in text  # projected outline edges
    assert a1.sha256 == a2.sha256  # hand-written ASCII → deterministic


@pytest.mark.requires_freecad
def test_dxf_unsupported_plane_rejected(freecad_doc, tmp_path) -> None:
    hull = build_hull(document=freecad_doc)
    with pytest.raises(ExportInputError):
        export_dxf_profile(hull.body, tmp_path / "p.dxf", plane="xy")
