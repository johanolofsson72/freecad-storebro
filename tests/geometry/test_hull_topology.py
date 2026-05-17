"""Geometry test: closed-shell + symmetry topology (T030).

Covers FR-009 (symmetric about centerline) and FR-010 (closed watertight shell).
"""

from __future__ import annotations

from storebro import build_hull


def test_hull_shape_is_closed(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    # FR-010: outer shell is closed / watertight.
    # The Body's Tip Shape should be a closed solid.
    shape = hull.body.Shape
    assert shape.isClosed() is True


def test_hull_bbox_y_extent_is_symmetric_about_zero(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    # FR-009: symmetric about the X-Z plane (y → -y). The bounding-box
    # midpoint in Y should be approximately zero.
    bb = hull.body.Shape.BoundBox
    midpoint_y = (bb.YMin + bb.YMax) / 2.0
    # Allow 1 mm tolerance (FreeCAD reports mm).
    assert abs(midpoint_y) < 1.0


def test_hull_bbox_y_extent_matches_beam(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    bb = hull.body.Shape.BoundBox
    # YLength is in mm; convert to m and compare to beam_max within 5%
    # (loft-vs-station approximation; tighter than ±1% is unreasonable
    # for the half-section approximation we use).
    measured_beam_m = bb.YLength / 1000.0
    assert abs(measured_beam_m - hull.parameters.beam_max) / hull.parameters.beam_max < 0.05
