"""Geometry test: portholes are PartDesign::Pocket features (T010).

Covers spec 011 FR-004 + constitution III (no raw mesh).
"""

from __future__ import annotations

import pytest

from storebro import build_hull


@pytest.mark.requires_freecad
def test_portholes_are_partdesign_pockets(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    pockets = [obj for obj in hull.document.Objects if obj.TypeId == "PartDesign::Pocket"]
    assert len(pockets) == 6, "3 per side x 2 sides as PartDesign::Pocket features"


@pytest.mark.requires_freecad
def test_no_raw_mesh_objects(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    for obj in hull.document.Objects:
        assert not obj.TypeId.startswith("Mesh::"), (
            f"constitution III violation: raw mesh {obj.Label} ({obj.TypeId})"
        )


@pytest.mark.requires_freecad
def test_pockets_symmetric_port_starboard(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    port = [o for o in hull.document.Objects if o.Label.startswith("PortholePocketPort")]
    star = [o for o in hull.document.Objects if o.Label.startswith("PortholePocketStarboard")]
    assert len(port) == len(star) == 3
