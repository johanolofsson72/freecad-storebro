"""Spec 009 T020 — bilge arc is deferred to v1.1+ in v1.0.3.

Spec 009 originally promised quarter-circle bilge arcs in every non-stem
station. Per the spec 009 closure note, the bilge arc is deferred to v1.1+
because the denser-station + arc combination produces tessellation
artifacts (non-manifold edges, self-intersections) that break the STL
export pipeline.

These tests assert the deferral: no non-stem sketches carry an arc
element in v1.0.3, regardless of the ``bilge_radius`` parameter value.
"""

from __future__ import annotations

import pytest

from storebro.hull import HullParameters, build_hull

pytestmark = pytest.mark.requires_freecad


def _non_stem_sketches(body: object) -> list[object]:
    """Return all non-stem station sketches, stripping FreeCAD's auto-numbering
    suffix when matching the 'Stem' base name."""
    out = []
    for obj in body.Group:  # type: ignore[attr-defined]
        if obj.TypeId != "Sketcher::SketchObject":
            continue
        base_name = obj.Name.rstrip("0123456789")
        if base_name.endswith("Stem"):
            continue
        out.append(obj)
    return out


def test_default_hull_non_stem_stations_have_no_arc_in_v103() -> None:
    """v1.0.3 deferral: even at default bilge_radius>0, no arcs are emitted."""
    hull = build_hull()
    non_stem = _non_stem_sketches(hull.body)
    assert non_stem, "no non-stem sketches found"
    for sketch in non_stem:
        arcs = [g for g in sketch.Geometry if g.TypeId == "Part::GeomArcOfCircle"]
        assert not arcs, (
            f"sketch {sketch.Name} unexpectedly contains arc elements in v1.0.3 — "
            "bilge arc is deferred to v1.1+"
        )


def test_zero_bilge_radius_yields_no_arc_elements() -> None:
    """bilge_radius=0 → all non-stem sketches use the legacy pentagon (no arc)."""
    hull = build_hull(HullParameters(bilge_radius=0.0))
    for sketch in _non_stem_sketches(hull.body):
        arcs = [g for g in sketch.Geometry if g.TypeId == "Part::GeomArcOfCircle"]
        assert not arcs, (
            f"sketch {sketch.Name} has unexpected arc with bilge_radius=0"
        )


def test_custom_bilge_radius_does_not_emit_arc_in_v103() -> None:
    """Even with bilge_radius>0, v1.0.3 defers the arc generation."""
    hull = build_hull(HullParameters(bilge_radius=0.10))
    for sketch in _non_stem_sketches(hull.body):
        arcs = [g for g in sketch.Geometry if g.TypeId == "Part::GeomArcOfCircle"]
        assert not arcs, (
            f"sketch {sketch.Name} unexpectedly contains arc elements in v1.0.3"
        )
