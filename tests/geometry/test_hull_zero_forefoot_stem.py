"""Spec 009 T010 — geometry tests for the thin-forefoot stem topology.

Implementation drift (documented in StationTopology docstring + spec 009
closure note): the spec's ``DEGENERATE_VERTEX`` topology was found to
overshoot wildly under Ruled=False loft interpolation. The implementation
substitutes ``PENTAGON_THIN_STEM`` — a thin-WIDTH stem section (5 mm
half-width, rounded to 7 vertices since spec 032). Spec 033 deepened its
forefoot to 0.30 m for a fuller bow, so it is no longer a literal "zero
forefoot" — only the section width is thin. Topologically compatible with
the loft.

When ``station_count >= 8``, the stem station MUST use the thin pentagon.
When ``station_count < 8``, the stem MUST retain the spec 007
pentagon-with-80mm-forefoot topology.
"""

from __future__ import annotations

import pytest

from storebro.hull import (
    THIN_STEM_HALF_WIDTH_M,
    HullParameters,
    build_hull,
)

pytestmark = pytest.mark.requires_freecad


def _find_stem_sketch(body: object) -> object:
    """Return the station sketch whose name (stripped of FreeCAD's auto-numbering
    suffix) ends with 'Stem'."""
    for obj in body.Group:  # type: ignore[attr-defined]
        if obj.TypeId == "Sketcher::SketchObject":
            base_name = obj.Name.rstrip("0123456789")
            if base_name.endswith("Stem"):
                return obj
    raise AssertionError("no stem sketch found in HullBody")


def _max_x_extent_mm(sketch: object) -> float:
    """Return the maximum X-coordinate across all vertices in the sketch."""
    max_x = 0.0
    for geom in sketch.Geometry:  # type: ignore[attr-defined]
        for attr in ("StartPoint", "EndPoint"):
            pt = getattr(geom, attr, None)
            if pt is not None:
                max_x = max(max_x, abs(pt.x))
    return max_x


def test_default_stem_is_thin_pentagon() -> None:
    """station_count=9 (default) → thin rounded stem sketch.

    Spec 032 made the standard hull a 7-vertex rounded-bilge section (the
    3-facet bilge round adds two vertices to the old 5-vertex pentagon), so the
    closed stem loop now has 7 line segments. The stem stays thin: its maximum
    X-extent is still THIN_STEM_HALF_WIDTH_M * 1000 mm.
    """
    hull = build_hull()
    stem = _find_stem_sketch(hull.body)
    line_segments = [
        g for g in stem.Geometry if g.TypeId == "Part::GeomLineSegment"
    ]
    assert len(line_segments) == 7
    max_x_mm = _max_x_extent_mm(stem)
    expected_mm = THIN_STEM_HALF_WIDTH_M * 1000.0
    assert abs(max_x_mm - expected_mm) <= 1.0, (
        f"stem half-width {max_x_mm} mm != expected {expected_mm} mm"
    )


def test_legacy_station_count_keeps_pentagon_stem() -> None:
    """station_count=5 → thin rounded stem (7 segments) and ~40 mm half-width.

    Station count is longitudinal and independent of the per-station vertex
    count; the standard hull's rounded bilge (spec 032) gives every station —
    stem included — a 7-vertex section regardless of station_count.
    """
    hull = build_hull(HullParameters(station_count=5))
    stem = _find_stem_sketch(hull.body)
    line_segments = [
        g for g in stem.Geometry if g.TypeId == "Part::GeomLineSegment"
    ]
    assert len(line_segments) == 7
    max_x_mm = _max_x_extent_mm(stem)
    # spec 007 legacy stem half-width = 40 mm.
    assert 35.0 <= max_x_mm <= 45.0, (
        f"legacy stem half-width {max_x_mm} mm should be ~40 mm"
    )


def test_threshold_station_count_uses_thin_stem() -> None:
    """station_count=8 (the threshold) → stem is the thin pentagon."""
    hull = build_hull(HullParameters(station_count=8))
    stem = _find_stem_sketch(hull.body)
    max_x_mm = _max_x_extent_mm(stem)
    expected_mm = THIN_STEM_HALF_WIDTH_M * 1000.0
    assert abs(max_x_mm - expected_mm) <= 1.0
