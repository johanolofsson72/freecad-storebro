"""Geometry test: hull uses PartDesign feature types only (spec 006 T009).

Covers FR-002 (PartDesign workbench), FR-010 (no raw mesh / no legacy
Part-workbench features inside the Body), FR-013 (Body.Tip is the mirror),
and spec.allium invariant `NoLegacyPartFeaturesInsideBody`.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

import pytest

from storebro import build_hull

pytestmark = pytest.mark.requires_freecad


_LEGACY_TYPES = {
    "Part::Loft",
    "Part::Mirroring",
    "Part::MultiFuse",
    "Part::Feature",
    "Mesh::Feature",
}


def test_hull_body_typeid_is_partdesign_body(freecad_doc: Any) -> None:
    hull = build_hull(document=freecad_doc)
    assert hull.body.TypeId == "PartDesign::Body"


def test_hull_body_tip_is_mirror_feature(freecad_doc: Any) -> None:
    hull = build_hull(document=freecad_doc)
    assert hull.body.Tip is not None
    assert hull.body.Tip.TypeId == "PartDesign::Mirrored"


def test_hull_body_contains_expected_feature_types(freecad_doc: Any) -> None:
    """Body's children: 1 Origin + N datum planes + N sketches + 1 AdditiveLoft
    + 1 Mirrored, where N = parameters.station_count (default 9 per spec 009;
    was 5 in spec 007)."""
    hull = build_hull(document=freecad_doc)
    type_counts = Counter(obj.TypeId for obj in hull.body.Group)

    # spec 009: station_count default = 9 (was 5 in spec 007).
    expected_n = hull.parameters.station_count

    # PartDesign-derived counts
    assert type_counts.get("PartDesign::Plane", 0) == expected_n, (
        f"expected {expected_n} PartDesign::Plane datums, "
        f"got {type_counts.get('PartDesign::Plane', 0)}"
    )
    assert type_counts.get("Sketcher::SketchObject", 0) == expected_n, (
        f"expected {expected_n} Sketcher::SketchObject sketches, "
        f"got {type_counts.get('Sketcher::SketchObject', 0)}"
    )
    assert type_counts.get("PartDesign::AdditiveLoft", 0) == 1
    assert type_counts.get("PartDesign::Mirrored", 0) == 1
    # The Body's auto-created Origin lives on `body.Origin`, not in
    # `body.Group` (which lists only the additive features). Verify it
    # exists separately:
    assert hull.body.Origin is not None
    assert hull.body.Origin.TypeId == "App::Origin"


def test_hull_body_contains_no_legacy_part_features(freecad_doc: Any) -> None:
    """FR-010 + spec.allium NoLegacyPartFeaturesInsideBody."""
    hull = build_hull(document=freecad_doc)
    type_ids = {obj.TypeId for obj in hull.body.Group}
    leaked = type_ids & _LEGACY_TYPES
    assert not leaked, (
        f"FR-010 violation: legacy Part-workbench feature types leaked into "
        f"PartDesign Body: {leaked}"
    )


def test_hull_body_has_shape_with_positive_volume(freecad_doc: Any) -> None:
    """FR-007 — closed manifold solid with positive volume."""
    hull = build_hull(document=freecad_doc)
    shape = hull.body.Shape
    assert shape is not None
    assert shape.Volume > 0.0, f"hull volume must be positive, got {shape.Volume}"
    assert shape.isClosed(), "hull shape must be closed (no open edges)"
