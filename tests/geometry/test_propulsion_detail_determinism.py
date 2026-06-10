"""Geometry test: spec 021 detailed-propulsion reproducibility (T028).

Covers FR-008, SC-002, SC-008, FR-014 + spec.allium DeterministicShapeDigest.
Two independent default (detailed) builds produce byte-identical component
volumes for every detailed body, and a single-screw detailed build applies the
detail per-train.
"""

from __future__ import annotations

import contextlib

import FreeCAD  # type: ignore[import-not-found]

from storebro import build_deck, build_hull, build_propulsion
from storebro.propulsion import PropulsionParameters

_GROUPS = ("engines", "shafts", "propellers", "rudders", "struts")


def _volumes(prop: object) -> dict[str, list[float]]:
    return {g: sorted(w.body.Shape.Volume for w in getattr(prop, g)) for g in _GROUPS}


def test_two_detailed_builds_identical_volumes() -> None:
    doc1 = FreeCAD.newDocument("Det021_1")
    doc2 = FreeCAD.newDocument("Det021_2")
    try:
        a = build_propulsion(h1 := build_hull(document=doc1), build_deck(h1))
        b = build_propulsion(h2 := build_hull(document=doc2), build_deck(h2))
        va, vb = _volumes(a), _volumes(b)
        for g in _GROUPS:
            assert len(va[g]) == len(vb[g]) and len(va[g]) > 0, g
            for x, y in zip(va[g], vb[g], strict=True):
                # Byte-identical (the spike proved exact equality, not just close).
                assert x == y, f"{g}: volume drift {x} vs {y}"
    finally:
        for doc in (doc1, doc2):
            with contextlib.suppress(Exception):
                FreeCAD.closeDocument(doc.Name)


def test_full_assembly_stl_exportable(freecad_doc: object) -> None:
    import tempfile
    from pathlib import Path

    prop = build_propulsion(h := build_hull(document=freecad_doc), build_deck(h))
    out = Path(tempfile.gettempdir()) / "prop021_assembly.stl"
    for grp in _GROUPS:
        for w in getattr(prop, grp):
            w.body.Shape.exportStl(str(out))
            assert out.stat().st_size > 0


def test_single_screw_detail_applied_per_train(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    prop = build_propulsion(
        hull, deck, PropulsionParameters(engine_count=1, engine_offset_y_mm=0.0)
    )
    assert len(prop.engines) == 1  # type: ignore[attr-defined]
    assert prop.engines[0].detail_applied is True  # type: ignore[attr-defined]
    assert prop.propellers[0].airfoil_applied is True  # type: ignore[attr-defined]
    assert prop.shafts[0].has_coupling_flange is True  # type: ignore[attr-defined]
    assert len(prop.struts) >= 1  # type: ignore[attr-defined]
