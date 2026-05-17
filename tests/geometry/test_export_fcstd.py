"""Geometry test: FCStd writer end-to-end + round-trip (T027).

Covers FR-001 (.FCStd), FR-020 (zip-scrub), SC-002 (3s budget), SC-004
(.FCStd reopens with parametric history intact).
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import FreeCAD  # type: ignore[import-not-found]

from storebro import build_hull, export_fcstd

REQUIRED_BODY_PROPERTIES = [
    "LOA",
    "BeamMax",
    "Draft",
    "Freeboard",
    "SheerHeightAft",
    "SheerHeightFwd",
    "DeadriseAmidships",
    "TransomAngle",
]


def test_export_fcstd_round_trip(tmp_path: Path) -> None:
    hull = build_hull()
    out = tmp_path / "out.FCStd"
    art = export_fcstd(hull.document, out)

    assert art.format == "fcstd"
    assert art.byte_count > 0
    assert 0.0 < art.build_duration_seconds < 3.0  # SC-002 .FCStd budget (A1)
    assert out.is_file()

    # SC-004: reopen in FreeCAD, verify parametric history intact.
    reopened = FreeCAD.openDocument(str(out))
    try:
        labels = [obj.Label for obj in reopened.Objects]
        assert any(label.startswith("Hull") for label in labels), (
            f"reopened doc has no Hull body — labels: {labels}"
        )
        hull_body = next(o for o in reopened.Objects if o.Label.startswith("Hull"))
        for prop in REQUIRED_BODY_PROPERTIES:
            assert hasattr(hull_body, prop), (
                f"reopened Hull missing property {prop!r}"
            )
    finally:
        FreeCAD.closeDocument(reopened.Name)


def test_export_fcstd_is_zip_with_stored_compression(tmp_path: Path) -> None:
    hull = build_hull()
    out = tmp_path / "compression.FCStd"
    export_fcstd(hull.document, out)
    with zipfile.ZipFile(out, "r") as zf:
        for info in zf.infolist():
            assert info.compress_type == zipfile.ZIP_STORED, (
                f"FR-020: entry {info.filename} uses non-STORED compression"
            )


def test_export_fcstd_entries_have_fixed_epoch(tmp_path: Path) -> None:
    hull = build_hull()
    out = tmp_path / "epoch.FCStd"
    export_fcstd(hull.document, out)
    with zipfile.ZipFile(out, "r") as zf:
        for info in zf.infolist():
            assert info.date_time == (1980, 1, 1, 0, 0, 0), (
                f"FR-020: entry {info.filename} has non-epoch timestamp "
                f"{info.date_time}"
            )


def test_export_fcstd_entries_alphabetically_ordered(tmp_path: Path) -> None:
    hull = build_hull()
    out = tmp_path / "order.FCStd"
    export_fcstd(hull.document, out)
    with zipfile.ZipFile(out, "r") as zf:
        names = zf.namelist()
    assert names == sorted(names), (
        "FR-020: zip entries are not alphabetically ordered: " + repr(names)
    )


def test_export_fcstd_determinism(tmp_path: Path) -> None:
    hull = build_hull()
    a = export_fcstd(hull.document, tmp_path / "a.FCStd")
    b = export_fcstd(hull.document, tmp_path / "b.FCStd")
    assert a.sha256 == b.sha256, (
        f"FCStd byte determinism violated — {a.sha256} vs {b.sha256}"
    )
