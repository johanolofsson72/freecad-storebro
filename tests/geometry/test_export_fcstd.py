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
    # Human-scale .FCStd budget. spec 018 densified the default hull (9 -> 31
    # stations) for a smooth surface, which raises build+export time from ~2 s
    # to ~3.4 s — still well within the spec 018 human-scale budget (n=81 < 10 s).
    assert 0.0 < art.build_duration_seconds < 10.0
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
            assert hasattr(hull_body, prop), f"reopened Hull missing property {prop!r}"
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
                f"FR-020: entry {info.filename} has non-epoch timestamp {info.date_time}"
            )


def test_export_fcstd_entries_alphabetically_ordered(tmp_path: Path) -> None:
    """FR-020 amended (spec 006): Document.xml MUST be the first zip entry.

    The original spec required alphabetical ordering, but spec 006's
    PartDesign-rebuild surfaced that FreeCAD's loader depends on the
    natural write-order of `.brp` / `.Map.txt` entries for the
    PartDesign Body's Shape reconstruction. Re-ordering entries (even
    with Document.xml first, rest alphabetical) produces a file that
    opens but where `body.Shape.Volume` raises "shape is invalid".

    Spec 006 amends FR-020: Document.xml is the only ordering constraint;
    the remaining entries are emitted in FreeCAD's natural write order.
    Determinism within a single FreeCAD process holds (the writer is
    stable). Cross-process determinism is `Fcstd.cross_invocation_byte_determinism`
    — deferred to v1.1+.
    """
    hull = build_hull()
    out = tmp_path / "order.FCStd"
    export_fcstd(hull.document, out)
    with zipfile.ZipFile(out, "r") as zf:
        names = zf.namelist()
    assert names[0] == "Document.xml", (
        f"FR-020: Document.xml must be first entry, got {names[0]!r}"
    )


def test_export_fcstd_determinism(tmp_path: Path) -> None:
    # spec 028: the comprehensive scrub (Object-ID renumber + global hash-tag
    # canonicalization + Map.txt sorting) makes two same-process FCStd exports
    # byte-identical even under cumulative process state. Was xfail (spec
    # 009/011/012) until spec 028 closed the within-process gap.
    hull = build_hull()
    a = export_fcstd(hull.document, tmp_path / "a.FCStd")
    b = export_fcstd(hull.document, tmp_path / "b.FCStd")
    assert a.sha256 == b.sha256, f"FCStd byte determinism violated — {a.sha256} vs {b.sha256}"
