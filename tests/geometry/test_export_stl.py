"""Geometry test: STL writer end-to-end (T036).

Covers FR-001 (STL), FR-010 (tessellation), FR-011 (binary), SC-002 (10s budget).
"""

from __future__ import annotations

from pathlib import Path

from storebro import build_hull, export_stl


def test_export_stl_round_trip(tmp_path: Path) -> None:
    hull = build_hull()
    out = tmp_path / "out.stl"
    art = export_stl(hull.body, out)

    assert art.format == "stl"
    assert art.byte_count > 0
    assert 0.0 < art.build_duration_seconds < 10.0  # SC-002 STL budget (A1)
    assert out.is_file()


def test_export_stl_is_binary_not_ascii(tmp_path: Path) -> None:
    hull = build_hull()
    out = tmp_path / "binary.stl"
    export_stl(hull.body, out)
    payload = out.read_bytes()
    # FR-011: binary STL must NOT start with "solid " (ASCII STL header).
    assert not payload.startswith(b"solid "), "FR-011: STL must be binary, not ASCII"
    # Binary STL: first 80 bytes header, then uint32 triangle count.
    assert len(payload) >= 84
    triangle_count = int.from_bytes(payload[80:84], "little")
    assert triangle_count > 0, "binary STL has zero triangles"


def test_export_stl_determinism(tmp_path: Path) -> None:
    hull = build_hull()
    a = export_stl(hull.body, tmp_path / "a.stl")
    b = export_stl(hull.body, tmp_path / "b.stl")
    assert a.sha256 == b.sha256, f"STL byte determinism violated — {a.sha256} vs {b.sha256}"
