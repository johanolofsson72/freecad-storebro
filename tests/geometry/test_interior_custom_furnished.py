"""Geometry test: custom-layout furniture mode (spec 025 US2, T011).

Covers FR-002, FR-008, SC-002. A non-canonical layout's compartments are
furnished by type, not boxed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storebro import build_deck, build_hull, build_interior

_CUSTOM = """schema_version: 1
layout_name: CustomFurnishTest
source: test
compartments:
  - {name: VBerth, type: forward_cabin, position: {x: 0.5, y: 0, z: 0.6}, dimensions: {length: 2.4, width: 2.0, height: 1.2}}
  - {name: Galley, type: galley, position: {x: 3.2, y: 0, z: 0.5}, dimensions: {length: 1.4, width: 2.0, height: 1.2}}
  - {name: Head, type: head, position: {x: 5.0, y: 0, z: 0.5}, dimensions: {length: 1.2, width: 1.6, height: 1.4}}
"""


@pytest.mark.requires_freecad
def test_custom_layout_furnished_by_type(freecad_doc: object, tmp_path: Path) -> None:
    p = tmp_path / "custom.yaml"
    p.write_text(_CUSTOM)
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout=str(p))

    assert len(interior.compartments) == 3
    for c in interior.compartments:
        assert c.is_furnished, f"{c.spec.name} should be furnished by type, not boxed"
        assert len(c.furniture) >= 2  # furniture piece(s) + a bulkhead, not a bare box
        for pc in c.furniture:
            assert pc.Shape.isValid()

    galley = next(c for c in interior.compartments if c.spec.compartment_type == "galley")
    counter = next(p for p in galley.furniture if "GalleyCounter" in p.Label)
    assert len(counter.Shape.Solids) == 1 and counter.Shape.isValid()
