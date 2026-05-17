"""Geometry test: BREP writer end-to-end (T030).

Covers FR-001 (BREP), FR-016 (LF endings), FR-018 (creator sentinel),
SC-002 (3s budget).
"""

from __future__ import annotations

from pathlib import Path

from storebro import build_hull, export_brep


def test_export_brep_round_trip(tmp_path: Path) -> None:
    hull = build_hull()
    out = tmp_path / "out.brep"
    art = export_brep(hull.body, out)

    assert art.format == "brep"
    assert art.byte_count > 0
    assert 0.0 < art.build_duration_seconds < 3.0  # SC-002 BREP budget (A1)
    assert out.is_file()


def test_export_brep_lf_endings_only(tmp_path: Path) -> None:
    hull = build_hull()
    out = tmp_path / "lf.brep"
    export_brep(hull.body, out)
    payload = out.read_bytes()
    assert b"\r\n" not in payload, "FR-016: BREP MUST have LF endings only (A2)"


def test_export_brep_dbrep_magic(tmp_path: Path) -> None:
    hull = build_hull()
    out = tmp_path / "magic.brep"
    export_brep(hull.body, out)
    payload = out.read_bytes()
    assert b"DBRep_DrawableShape" in payload, "BREP magic marker missing"


def test_export_brep_originator_sentinel(tmp_path: Path) -> None:
    hull = build_hull()
    out = tmp_path / "sentinel.brep"
    export_brep(hull.body, out)
    payload = out.read_text(encoding="utf-8")
    # FreeCAD may or may not include an Originator comment in BREP; if present
    # it MUST be the project sentinel (FR-018).
    if "Originator" in payload:
        assert "freecad-storebro" in payload


def test_export_brep_determinism(tmp_path: Path) -> None:
    hull = build_hull()
    a = export_brep(hull.body, tmp_path / "a.brep")
    b = export_brep(hull.body, tmp_path / "b.brep")
    assert a.sha256 == b.sha256
