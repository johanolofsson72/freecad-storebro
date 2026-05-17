"""Geometry test: STL tessellation tolerance behavior (T037).

Covers FR-010. Tighter tolerance → more triangles → larger files.
"""

from __future__ import annotations

from pathlib import Path

from storebro import build_hull, export_stl


def test_finer_tolerance_produces_more_triangles(tmp_path: Path) -> None:
    hull = build_hull()

    coarse = export_stl(
        hull.body, tmp_path / "coarse.stl", tessellation_tolerance=0.005
    )
    default = export_stl(hull.body, tmp_path / "default.stl")
    fine = export_stl(
        hull.body, tmp_path / "fine.stl", tessellation_tolerance=0.0001
    )

    assert fine.byte_count > default.byte_count > coarse.byte_count, (
        "FR-010: tighter tolerance must produce larger STL "
        f"(coarse={coarse.byte_count}, default={default.byte_count}, "
        f"fine={fine.byte_count})"
    )
