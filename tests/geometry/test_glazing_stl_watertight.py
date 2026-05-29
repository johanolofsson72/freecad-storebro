"""Geometry test: glazed hull still exports a watertight STL (T021).

Covers spec 011 SC-004 — the spec 009 non-manifold regression guard. The
blind-recess cuts must not break STL export.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storebro import build_hull, export_stl


@pytest.mark.requires_freecad
def test_glazed_hull_stl_is_watertight(freecad_doc: object, tmp_path: Path) -> None:
    hull = build_hull(document=freecad_doc)
    out = tmp_path / "glazed_hull.stl"
    artifact = export_stl(hull.document, str(out))
    assert out.is_file()
    assert artifact.byte_count > 0
    # The exported solid is a single closed manifold (the cuts are blind).
    assert len(hull.body.Shape.Solids) == 1
    assert hull.body.Shape.isValid()
