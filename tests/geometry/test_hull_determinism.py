"""Geometry test: structural determinism for fixed inputs (T035).

Covers FR-005, SC-003. Two builds with identical parameters produce
structurally identical Bodies (same volume, bbox, topology counts).
"""

from __future__ import annotations

import FreeCAD  # type: ignore[import-not-found]

from storebro import HullParameters, build_hull

RELATIVE_TOL = 1.0e-9


def _close(a: float, b: float) -> bool:
    if b == 0.0:
        return abs(a - b) <= RELATIVE_TOL
    return abs(a - b) / abs(b) <= RELATIVE_TOL


def test_two_builds_yield_identical_volume_and_bbox() -> None:
    doc1 = FreeCAD.newDocument("Determinism1")
    doc2 = FreeCAD.newDocument("Determinism2")
    try:
        params = HullParameters()
        h1 = build_hull(params, document=doc1)
        h2 = build_hull(params, document=doc2)

        assert _close(h1.volume, h2.volume), f"volume drift: {h1.volume} vs {h2.volume}"

        for i, name in enumerate(("length", "width", "height")):
            assert _close(h1.bbox[i], h2.bbox[i]), (
                f"bbox {name} drift: {h1.bbox[i]} vs {h2.bbox[i]}"
            )
    finally:
        FreeCAD.closeDocument(doc1.Name)
        FreeCAD.closeDocument(doc2.Name)


def test_two_builds_yield_identical_topology_counts() -> None:
    doc1 = FreeCAD.newDocument("DeterminismTop1")
    doc2 = FreeCAD.newDocument("DeterminismTop2")
    try:
        params = HullParameters()
        h1 = build_hull(params, document=doc1)
        h2 = build_hull(params, document=doc2)

        s1 = h1.body.Shape
        s2 = h2.body.Shape
        assert len(s1.Vertexes) == len(s2.Vertexes)
        assert len(s1.Edges) == len(s2.Edges)
        assert len(s1.Faces) == len(s2.Faces)
    finally:
        FreeCAD.closeDocument(doc1.Name)
        FreeCAD.closeDocument(doc2.Name)
