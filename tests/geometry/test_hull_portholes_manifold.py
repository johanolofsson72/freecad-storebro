"""Geometry test: portholes cut into the hull, hull stays manifold (T009).

Covers spec 011 FR-001, FR-007, FR-008, SC-001 + spec.allium
HullManifoldAfterGlazing / AllPortholesAboveWaterline.
"""

from __future__ import annotations

import pytest

from storebro import (
    HullGlazingParameters,
    PortholeParameters,
    build_hull,
)
from storebro.hull import _WATERLINE_Z_MM, HullParameterError


@pytest.mark.requires_freecad
def test_default_hull_has_six_portholes_and_stays_manifold(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    assert hull.portholes is not None
    assert hull.portholes.count == 6  # 3 per side
    shape = hull.body.Shape
    assert len(shape.Solids) == 1, "FR-008: hull must remain a single solid"
    assert shape.isValid()


@pytest.mark.requires_freecad
def test_porthole_pockets_above_waterline(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    pockets = [obj for obj in hull.document.Objects if obj.Label.startswith("PortholePocket")]
    assert pockets, "FR-001: portholes expected on default parameters"
    # The cut regions (pocket sketches) sit above the waterline.
    sketches = [obj for obj in hull.document.Objects if obj.Label.startswith("PortholeSketch")]
    for sk in sketches:
        zmin = sk.Shape.BoundBox.ZMin
        assert zmin > _WATERLINE_Z_MM, f"{sk.Label} below waterline"


@pytest.mark.requires_freecad
def test_zero_portholes_leaves_hull_uncut(freecad_doc: object) -> None:
    hg = HullGlazingParameters(portholes=PortholeParameters(count_per_side=0))
    hull = build_hull(document=freecad_doc, parameters_glazing=hg)
    assert hull.portholes.count == 0
    assert len(hull.body.Shape.Solids) == 1


@pytest.mark.requires_freecad
def test_recess_deeper_than_half_beam_rejected(freecad_doc: object) -> None:
    hg = HullGlazingParameters(
        portholes=PortholeParameters(recess_depth=5000.0)  # > any half-beam
    )
    with pytest.raises(HullParameterError) as exc:
        build_hull(document=freecad_doc, parameters_glazing=hg)
    assert exc.value.parameter_name == "porthole_recess_depth<>half_beam"
