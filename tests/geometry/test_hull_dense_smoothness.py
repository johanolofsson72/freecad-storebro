"""Geometry test: spec 018 dense Ruled=True smooth hull (FR-001..FR-008).

Requires FreeCAD. Asserts the densified default + higher cap produce a single
manifold, STL-exportable hull with zero beam overshoot (the Ruled=True
exactness the spike confirmed), monotonically increasing face count with
station density, the n=9 back-compat shape, and the bilge arc staying off.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from storebro import build_hull
from storebro.export import export_stl
from storebro.hull import DEFAULT_STATION_COUNT, HullParameters


def _beam_overshoot_pct(hull: object, p: HullParameters) -> float:
    bb = hull.body.Shape.BoundBox  # type: ignore[attr-defined]
    return 100.0 * (bb.YLength - p.beam_max * 1000.0) / (p.beam_max * 1000.0)


def test_default_is_thirty_one_stations() -> None:
    assert DEFAULT_STATION_COUNT == 31


@pytest.mark.parametrize("n", [3, 9, 31, 81])
def test_hull_manifold_and_exact_across_densities(freecad_doc: object, n: int) -> None:
    p = HullParameters(station_count=n)
    hull = build_hull(document=freecad_doc, parameters=p)
    sh = hull.body.Shape
    assert len(sh.Solids) == 1, f"n={n}: {len(sh.Solids)} solids"
    assert sh.isValid()
    # Ruled=True is exact: beam within ±1% (0% overshoot), SC-002.
    assert abs(_beam_overshoot_pct(hull, p)) <= 1.0


@pytest.mark.parametrize("n", [3, 9, 31, 81])
def test_hull_stl_exports_across_densities(freecad_doc: object, n: int) -> None:
    hull = build_hull(document=freecad_doc, parameters=HullParameters(station_count=n))
    with tempfile.TemporaryDirectory() as d:
        art = export_stl(hull.body, Path(d) / "h.stl")
        assert art.byte_count > 0


def test_face_count_increases_with_density(freecad_doc: object) -> None:
    # SC-003: more stations -> more lengthwise faces -> smoother read.
    counts = []
    for n in (9, 31, 81):
        hull = build_hull(document=freecad_doc, parameters=HullParameters(station_count=n))
        counts.append(len(hull.body.Shape.Faces))
    assert counts[0] < counts[1] < counts[2], counts


def test_back_compat_nine_station_shape(freecad_doc: object) -> None:
    # FR-008: pinning station_count=9 reproduces the pre-feature density.
    hull = build_hull(document=freecad_doc, parameters=HullParameters(station_count=9))
    assert len(hull.body.Shape.Solids) == 1
    assert hull.parameters.station_count == 9


def test_bilge_arc_stays_off_sharp_chine(freecad_doc: object) -> None:
    # FR-006/FR-007 outcome: the bilge arc re-defers (mesh non-watertight),
    # so the default hull uses the sharp chine and never the arc.
    p = HullParameters()  # default bilge_radius 0.10
    assert p.uses_bilge_arc is False
    hull = build_hull(document=freecad_doc, parameters=p)
    assert len(hull.body.Shape.Solids) == 1
    assert hull.body.Shape.isValid()
