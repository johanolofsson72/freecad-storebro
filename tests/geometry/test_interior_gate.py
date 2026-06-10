"""Geometry test: the furnish-by-type dispatch (T006, repurposed for spec 013/025).

Spec 012 furnished only Alt1/Alt2; spec 013 widened to all five canonical
layouts; spec 025 drops the layout-name gate entirely so furniture is dispatched
by compartment TYPE for every layout — custom (non-canonical) layouts now furnish
too. This test asserts every canonical layout is furnished, and that a custom
YAML layout's furnishable-type compartments are furnished (not boxed).

Covers spec 013 FR-001 + spec 025 FR-002, SC-002.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from storebro import build_deck, build_hull, build_interior

_CUSTOM_YAML = """\
schema_version: 1
layout_name: CustomTest
source: test
compartments:
  - name: ForwardCabin
    type: forward_cabin
    position: { x: 0.5, y: 0, z: 0.5 }
    dimensions: { length: 2.0, width: 1.8, height: 1.1 }
  - name: Salon
    type: salon
    position: { x: 3.0, y: 0, z: 0.5 }
    dimensions: { length: 3.0, width: 2.4, height: 1.6 }
"""


@pytest.mark.requires_freecad
@pytest.mark.parametrize(
    "layout",
    ["Alternativ1", "Alternativ2", "Alternativ3", "Alternativ4", "Alternativ5"],
)
def test_all_canonical_layouts_are_furnished(freecad_doc: object, layout: str) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout=layout)
    assert all(c.is_furnished for c in interior.compartments)
    for c in interior.compartments:
        assert len(c.furniture) >= 1


@pytest.mark.requires_freecad
def test_custom_layout_furnished_by_type(freecad_doc: object, tmp_path: Path) -> None:
    # spec 025 — custom layouts now furnish by compartment type (FR-002).
    custom = tmp_path / "custom.yaml"
    custom.write_text(_CUSTOM_YAML, encoding="utf-8")
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout=str(custom))
    assert all(c.is_furnished for c in interior.compartments)
    for c in interior.compartments:
        assert c.furniture != ()  # furnished, not a bare box
