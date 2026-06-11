"""Geometry test: a scrubbed FCStd reloads with valid geometry (spec 028 T005).

Covers FR-004, FR-011 (the hard constraint — the determinism scrub MUST NOT break
the document). The consistent bijective renumbering of Object IDs / hash tags is
only valid because the reloaded shapes stay valid with unchanged volume.
"""

from __future__ import annotations

import FreeCAD  # type: ignore[import-not-found]
import pytest

from storebro import build_deck, build_hull, build_interior, export_fcstd


@pytest.mark.requires_freecad
def test_scrubbed_fcstd_reopens_with_valid_geometry(freecad_doc: object, tmp_path) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    build_interior(hull, deck, layout="Alternativ1")
    pre_volume = hull.body.Shape.Volume

    out = tmp_path / "boat.FCStd"
    export_fcstd(freecad_doc, out)

    reopened = FreeCAD.openDocument(str(out))
    try:
        bodies_with_shape = [
            o for o in reopened.Objects if getattr(o, "Shape", None) is not None and o.Shape.Faces
        ]
        assert bodies_with_shape, "reopened document has no shape-bearing bodies"
        for obj in bodies_with_shape:
            assert obj.Shape.isValid(), f"{obj.Name}: shape invalid after scrub"
        hb = next(o for o in reopened.Objects if o.Name == "HullBody")
        assert hb.Shape.isValid()
        assert hb.Shape.Volume == pytest.approx(pre_volume, rel=1e-9)
    finally:
        FreeCAD.closeDocument(reopened.Name)
