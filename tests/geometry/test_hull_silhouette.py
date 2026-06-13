"""Geometry test: hull silhouette dimensions match storebropassion.de reference.

Spec 007 FR-010 + SC-004. The bounding box of the hull Body's Shape must
match the reference within tolerance:
- X-extent (LOA): 10.35m ±1%
- Y-extent (beam): 3.20m ±2% (the loft tapering may shave a few mm off the max)
- Z-extent (draft + freeboard envelope): between 1500mm and 2300mm
"""

from __future__ import annotations

from typing import Any

import pytest

from storebro import build_hull

pytestmark = pytest.mark.requires_freecad


def test_hull_silhouette_loa_within_one_percent(freecad_doc: Any) -> None:
    """Bbox X-extent matches LOA (10.35m) within ±1%."""
    hull = build_hull(document=freecad_doc)
    bbox_x_m = hull.body.Shape.BoundBox.XLength / 1000.0
    assert abs(bbox_x_m - 10.35) / 10.35 <= 0.01, (
        f"LOA tolerance: expected 10.35m ±1%, got {bbox_x_m:.3f}m"
    )


def test_hull_silhouette_beam_within_two_percent(freecad_doc: Any) -> None:
    """Bbox Y-extent matches beam_max (3.20m) within ±2%."""
    hull = build_hull(document=freecad_doc)
    bbox_y_m = hull.body.Shape.BoundBox.YLength / 1000.0
    assert abs(bbox_y_m - 3.20) / 3.20 <= 0.02, (
        f"Beam tolerance: expected 3.20m ±2%, got {bbox_y_m:.3f}m"
    )


def test_hull_silhouette_z_in_envelope(freecad_doc: Any) -> None:
    """Bbox Z-extent in the freeboard + draft envelope (1.5m - 2.6m).

    Spec 032 sweeping sheer peaks the bow deck at ``sheer_height_fwd * 1.22``,
    so the Z-extent (draft 1.10 + ~1.42 bow peak ≈ 2.49 m) sits above the old
    2.3 m bound — the upper bound is raised to 2.6 m to match the rounded hull.
    """
    hull = build_hull(document=freecad_doc)
    bbox_z_m = hull.body.Shape.BoundBox.ZLength / 1000.0
    assert 1.5 <= bbox_z_m <= 2.6, (
        f"Hull Z-extent out of envelope: expected 1.5m - 2.6m, got {bbox_z_m:.3f}m"
    )


def test_hull_shape_is_closed_manifold(freecad_doc: Any) -> None:
    """Sanity: the silhouette tests imply a valid closed solid."""
    hull = build_hull(document=freecad_doc)
    assert hull.body.Shape.isClosed()
    assert hull.body.Shape.Volume > 0.0
