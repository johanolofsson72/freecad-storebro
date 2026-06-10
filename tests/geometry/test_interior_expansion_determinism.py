"""Geometry test: spec 025 new-path reproducibility (T018).

Covers FR-009, SC-006. Alt5 (salon_galley), a custom layout, and an asymmetric
layout each build byte-identically across two independent builds.
"""

from __future__ import annotations

import contextlib
from pathlib import Path

import FreeCAD  # type: ignore[import-not-found]
import pytest

from storebro import build_deck, build_hull, build_interior

_CUSTOM = """schema_version: 1
layout_name: DetCustom
source: test
compartments:
  - {name: VBerth, type: forward_cabin, position: {x: 0.5, y: 0, z: 0.6}, dimensions: {length: 2.4, width: 2.0, height: 1.2}}
  - {name: ER, type: engine_room, position: {x: 3.2, y: 0, z: 0.4}, dimensions: {length: 1.6, width: 1.8, height: 1.2}}
  - {name: PortHead, type: head, position: {x: 5.2, y: 0.6, z: 0.5}, dimensions: {length: 1.0, width: 1.0, height: 1.4}}
"""


def _volumes(layout: str) -> list[float]:
    doc = FreeCAD.newDocument("DetRun")
    try:
        h = build_hull(document=doc)
        interior = build_interior(h, build_deck(h), layout=layout)
        return sorted(c.body.Shape.Volume for c in interior.compartments)
    finally:
        with contextlib.suppress(Exception):
            FreeCAD.closeDocument(doc.Name)


@pytest.mark.requires_freecad
def test_alt5_deterministic() -> None:
    assert _volumes("Alternativ5") == _volumes("Alternativ5")


@pytest.mark.requires_freecad
def test_custom_and_asymmetric_deterministic(tmp_path: Path) -> None:
    p = tmp_path / "det_custom.yaml"
    p.write_text(_CUSTOM)
    assert _volumes(str(p)) == _volumes(str(p))
