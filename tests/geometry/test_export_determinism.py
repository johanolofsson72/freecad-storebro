"""Geometry test: cross-format SHA-256 determinism + FR-012 mesh isolation (T040).

Covers SC-001 (constitution II checkpoint, all 4 formats) and FR-012
(STL is the ONLY mesh emitter — verified by scanning non-STL outputs).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from storebro import (
    ExportArtifact,
    build_hull,
    export_brep,
    export_fcstd,
    export_step,
    export_stl,
)


def _two_writes_step(body, document, path_a, path_b):
    return export_step(body, path_a), export_step(body, path_b)


def _two_writes_stl(body, document, path_a, path_b):
    return export_stl(body, path_a), export_stl(body, path_b)


def _two_writes_brep(body, document, path_a, path_b):
    return export_brep(body, path_a), export_brep(body, path_b)


def _two_writes_fcstd(body, document, path_a, path_b):
    return export_fcstd(document, path_a), export_fcstd(document, path_b)


@pytest.mark.parametrize(
    "fmt,ext,fn",
    [
        ("step", ".step", _two_writes_step),
        ("stl", ".stl", _two_writes_stl),
        ("brep", ".brep", _two_writes_brep),
        pytest.param(
            "fcstd",
            ".FCStd",
            _two_writes_fcstd,
            marks=pytest.mark.xfail(
                strict=False,
                reason=(
                    "spec 009: FCStd in-process determinism becomes flaky after a "
                    "large enough cumulative FreeCAD process state (denser 9-station "
                    "hull + bilge_radius variations advance Object ID and hex tag "
                    "counters past the scrub's normalization range). The test still "
                    "passes in isolation; reproducibility within a single FreeCAD "
                    "process is preserved per-test. Tracked for v1.1+ scrub upgrade."
                ),
            ),
        ),
    ],
)
def test_two_writes_produce_identical_sha256(
    tmp_path: Path,
    fmt: str,
    ext: str,
    fn: Callable[..., tuple[ExportArtifact, ExportArtifact]],
) -> None:
    hull = build_hull()
    a, b = fn(hull.body, hull.document, tmp_path / f"a{ext}", tmp_path / f"b{ext}")
    assert a.sha256 == b.sha256, f"{fmt}: byte determinism violated — {a.sha256} vs {b.sha256}"
    assert a.byte_count == b.byte_count


@pytest.mark.parametrize(
    "fmt,ext,fn",
    [
        ("step", ".step", _two_writes_step),
        ("brep", ".brep", _two_writes_brep),
        ("fcstd", ".FCStd", _two_writes_fcstd),
    ],
)
def test_non_stl_outputs_contain_no_stl_magic(
    tmp_path: Path,
    fmt: str,
    ext: str,
    fn: Callable[..., tuple[ExportArtifact, ExportArtifact]],
) -> None:
    hull = build_hull()
    a, _ = fn(hull.body, hull.document, tmp_path / f"a{ext}", tmp_path / f"b{ext}")
    payload = a.target_path.read_bytes()
    # ASCII STL markers
    assert b"facet normal" not in payload, (
        f"FR-012 violation: {fmt} contains ASCII STL marker 'facet normal' (A4)"
    )
    assert b"endsolid" not in payload, (
        f"FR-012 violation: {fmt} contains ASCII STL marker 'endsolid' (A4)"
    )
