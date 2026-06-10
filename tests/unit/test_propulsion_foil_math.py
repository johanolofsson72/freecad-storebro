"""Unit test (no FreeCAD): NACA foil-math helpers (spec 021 T006).

Covers FR-001/FR-002 foil section shape + SC-003/SC-004 + spec.allium foil
section properties. Pure Python — the helpers import no FreeCAD.
"""

from __future__ import annotations

from storebro.propulsion import (
    _naca_section_polyline,
    _naca_symmetric_half_thickness,
    _rotate2d,
)


def test_half_thickness_zero_at_leading_and_trailing_edge() -> None:
    assert _naca_symmetric_half_thickness(0.0, 0.12) == 0.0
    # Closed trailing edge: the -0.1036 coefficient makes yt(1) == 0.
    assert abs(_naca_symmetric_half_thickness(1.0, 0.12)) < 1e-9


def test_half_thickness_positive_interior_peaks_forward() -> None:
    samples = [(x / 100.0, _naca_symmetric_half_thickness(x / 100.0, 0.18)) for x in range(1, 100)]
    assert all(y > 0.0 for _, y in samples)
    x_at_max = max(samples, key=lambda p: p[1])[0]
    # NACA 4-digit max thickness is at ~30% chord (forward of mid-chord).
    assert 0.2 < x_at_max < 0.45


def test_thickness_scales_with_ratio() -> None:
    thin = _naca_symmetric_half_thickness(0.3, 0.08)
    thick = _naca_symmetric_half_thickness(0.3, 0.18)
    assert thick > thin > 0.0


def test_section_polyline_closed_loop_starts_at_leading_edge() -> None:
    pts = _naca_section_polyline(100.0, 0.12, 16)
    assert len(pts) >= 16
    assert pts[0] == (0.0, 0.0)  # leading edge at the origin
    # Upper surface has +v, lower surface -v: section spans both signs.
    assert max(v for _, v in pts) > 0.0
    assert min(v for _, v in pts) < 0.0


def test_section_polyline_max_thickness_in_interior() -> None:
    pts = _naca_section_polyline(300.0, 0.18, 24)
    # The thickest chordwise station is in the interior, not at either edge.
    by_u: dict[float, list[float]] = {}
    for u, v in pts:
        by_u.setdefault(round(u, 3), []).append(v)
    spans = {u: (max(vs) - min(vs)) for u, vs in by_u.items() if len(vs) >= 2}
    u_thickest = max(spans, key=lambda k: spans[k])
    assert 0.0 < u_thickest < 300.0


def test_section_polyline_deterministic() -> None:
    a = _naca_section_polyline(123.4, 0.15, 20)
    b = _naca_section_polyline(123.4, 0.15, 20)
    assert a == b


def test_rotate2d_preserves_lengths_and_rotates() -> None:
    pts = [(1.0, 0.0), (0.0, 1.0)]
    out = _rotate2d(pts, 90.0)
    assert abs(out[0][0] - 0.0) < 1e-9 and abs(out[0][1] - 1.0) < 1e-9
    # zero rotation is identity
    assert _rotate2d(pts, 0.0) == pts
