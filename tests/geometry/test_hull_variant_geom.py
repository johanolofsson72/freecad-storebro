"""Geometry test: spec 031 hard-chine hull variant (requires FreeCAD).

Covers FR-002, FR-005, FR-008, FR-010 + spec.allium HullBody. The standard build is a single
valid solid (and the pre-031 default); the hard-chine build is a single valid solid that
encloses a different volume; both reproduce within tolerance; the variant + applied flag are
recorded on the Hull wrapper."""

from __future__ import annotations

import FreeCAD  # type: ignore[import-not-found]
import pytest

from storebro import build_hull

RELATIVE_TOL = 1.0e-9


def _close(a: float, b: float) -> bool:
    if b == 0.0:
        return abs(a - b) <= RELATIVE_TOL
    return abs(a - b) / abs(b) <= RELATIVE_TOL


@pytest.mark.requires_freecad
def test_standard_hull_is_single_valid_solid(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc, hull_variant="standard")
    assert len(hull.body.Shape.Solids) == 1
    assert hull.body.Shape.isValid()
    assert hull.hull_variant == "standard"
    assert hull.variant_applied is True


@pytest.mark.requires_freecad
def test_hard_chine_hull_is_single_valid_solid(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc, hull_variant="hard_chine")
    assert len(hull.body.Shape.Solids) == 1
    assert hull.body.Shape.isValid()
    assert hull.hull_variant == "hard_chine"
    # FR-010: a successful hard-chine build did not fall back.
    assert hull.variant_applied is True


@pytest.mark.requires_freecad
def test_hard_chine_differs_from_standard() -> None:
    doc_s = FreeCAD.newDocument("HV_std")
    doc_h = FreeCAD.newDocument("HV_hard")
    try:
        std = build_hull(document=doc_s, hull_variant="standard")
        hard = build_hull(document=doc_h, hull_variant="hard_chine")
        # The flatter bottom + outboard chine changes the enclosed volume measurably.
        assert not _close(std.body.Shape.Volume, hard.body.Shape.Volume)
    finally:
        FreeCAD.closeDocument(doc_s.Name)
        FreeCAD.closeDocument(doc_h.Name)


@pytest.mark.requires_freecad
def test_hard_chine_volume_is_reproducible() -> None:
    # FR-008: same variant + params twice in one process → identical volume.
    doc1 = FreeCAD.newDocument("HV_r1")
    doc2 = FreeCAD.newDocument("HV_r2")
    try:
        v1 = build_hull(document=doc1, hull_variant="hard_chine").body.Shape.Volume
        v2 = build_hull(document=doc2, hull_variant="hard_chine").body.Shape.Volume
        assert _close(v1, v2), f"hard-chine volume drift {v1} vs {v2}"
    finally:
        FreeCAD.closeDocument(doc1.Name)
        FreeCAD.closeDocument(doc2.Name)


@pytest.mark.requires_freecad
def test_standard_variant_matches_default_build() -> None:
    # FR-002/SC-001: explicit "standard" == the default build (byte/volume).
    doc_d = FreeCAD.newDocument("HV_default")
    doc_s = FreeCAD.newDocument("HV_explicit_std")
    try:
        default = build_hull(document=doc_d).body.Shape.Volume
        explicit = build_hull(document=doc_s, hull_variant="standard").body.Shape.Volume
        assert _close(default, explicit)
    finally:
        FreeCAD.closeDocument(doc_d.Name)
        FreeCAD.closeDocument(doc_s.Name)
