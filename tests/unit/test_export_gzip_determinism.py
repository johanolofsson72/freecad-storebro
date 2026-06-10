"""Unit test (no FreeCAD): spec 026 deterministic gzip + DXF bytes (T005/T016).

Covers FR-006 (deterministic gzip) + the hand-written R12 DXF byte-shape.
"""

from __future__ import annotations

import gzip

from storebro.export import _maybe_gzip, _write_r12_dxf


def test_maybe_gzip_passthrough_when_disabled() -> None:
    data = b"abc123" * 50
    assert _maybe_gzip(data, False) is data


def test_maybe_gzip_deterministic_and_roundtrips() -> None:
    data = b"storebro export bytes" * 200
    g1 = _maybe_gzip(data, True)
    g2 = _maybe_gzip(data, True)
    assert g1 == g2  # mtime zeroed, no embedded filename → byte-identical
    assert gzip.decompress(g1) == data
    assert g1 != data  # actually compressed


def test_dxf_bytes_deterministic_ascii_no_timestamp() -> None:
    segs = [(0.0, 0.0, 10.0, 0.0), (10.0, 0.0, 10.0, 5.0)]
    a = _write_r12_dxf(segs)
    b = _write_r12_dxf(segs)
    assert a == b
    assert a.startswith(b"0\nSECTION\n2\nENTITIES\n")
    assert a.endswith(b"0\nENDSEC\n0\nEOF\n")
    assert b"LINE" in a
    # R12 ASCII carries no timestamp/handles → fully deterministic by construction
    text = a.decode("ascii")
    assert "10\n0.000000" in text and "EOF" in text


def test_dxf_bytes_change_with_segments() -> None:
    a = _write_r12_dxf([(0.0, 0.0, 1.0, 1.0)])
    b = _write_r12_dxf([(0.0, 0.0, 2.0, 2.0)])
    assert a != b
