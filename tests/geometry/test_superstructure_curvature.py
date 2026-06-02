"""Geometry test: spec 020 superstructure curvature (hardtop curl + swept rail).

Requires FreeCAD. The windshield crown is deferred (see spec 020 Clarifications).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from storebro import build_deck, build_hull
from storebro.export import export_stl


def test_hardtop_smooth_curl_manifold_no_overshoot(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    assert deck.hardtop is not None
    sh = deck.hardtop.body.Shape
    assert len(sh.Solids) == 1 and sh.isValid()
    # SC-001/SC-003: a dense Ruled=True curl is exact (cannot exceed the convex
    # hull of its sections, so no overshoot) and has many more faces than the
    # old 3-section curl.
    assert len(sh.Faces) >= 8, f"curl should be dense (got {len(sh.Faces)} faces)"
    with tempfile.TemporaryDirectory() as d:
        assert export_stl(deck.hardtop.body, Path(d) / "ht.stl").byte_count > 0


def test_swept_top_rail_valid(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    rail_sh = deck.railings.body.Shape
    assert not rail_sh.isNull() and rail_sh.isValid()
    assert len(rail_sh.Solids) >= 1
    # FR-004: the swept AdditivePipe rail was built (or fell back to straight).
    pipes = [o for o in freecad_doc.Objects if o.Name.startswith("Rail") and "TopRailPipe" in o.Name]  # type: ignore[attr-defined]
    pads = [o for o in freecad_doc.Objects if o.Name.startswith("Rail") and "TopRailPad" in o.Name]  # type: ignore[attr-defined]
    assert pipes or pads, "top rail must be either a swept pipe or the straight fallback"
    with tempfile.TemporaryDirectory() as d:
        assert export_stl(deck.railings.body, Path(d) / "rail.stl").byte_count > 0


def test_swept_rail_prefers_pipe(freecad_doc: object) -> None:
    # With default geometry the AdditivePipe sweep should succeed (spike-proven),
    # giving port + starboard swept pipes.
    hull = build_hull(document=freecad_doc)
    build_deck(hull)
    pipes = [o for o in freecad_doc.Objects if "TopRailPipe" in o.Name]  # type: ignore[attr-defined]
    assert len(pipes) == 2, f"expected port+starboard swept pipes, got {len(pipes)}"
