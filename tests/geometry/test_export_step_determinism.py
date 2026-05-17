"""Geometry test: STEP byte-identical reproducibility (T019).

Covers FR-002, SC-001 (constitution II checkpoint, STEP).
"""

from __future__ import annotations

from pathlib import Path

from storebro import build_hull, export_step


def test_two_step_writes_produce_identical_sha256(tmp_path: Path) -> None:
    hull = build_hull()
    a = export_step(hull.body, tmp_path / "a.step")
    b = export_step(hull.body, tmp_path / "b.step")
    assert a.sha256 == b.sha256, f"STEP byte determinism violated — {a.sha256} vs {b.sha256}"
    assert a.byte_count == b.byte_count
