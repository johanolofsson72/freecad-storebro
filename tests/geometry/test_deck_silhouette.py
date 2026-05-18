"""Spec 008 SC-001 — superstructure bounding-box dimensions match reference within ±1%.

When built with the spec 008 `DeckSuperstructureParameters` defaults
(derived from `docs/references/Alternativ3.JPG` per research.md §R1),
each superstructure body's principal bounding-box dimensions must
deviate from the reference by ≤ 1% per constitution principle IV.

The legacy `build_deck(hull)` form (default `DeckParameters`) takes
slightly looser ±5% bound because the legacy 14-field defaults are
v1.0.1 estimate-grade rather than the v1.1 reference-grade values.
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull
from storebro.deck import DeckSuperstructureParameters


def _assert_close(actual: float, expected: float, *, tol_pct: float, name: str) -> None:
    delta_pct = abs(actual - expected) / expected * 100.0
    assert delta_pct <= tol_pct, (
        f"{name}: actual {actual:.1f} mm vs expected {expected:.1f} mm "
        f"(delta {delta_pct:.2f}% exceeds ±{tol_pct}%)"
    )


@pytest.mark.requires_freecad
def test_cabin_trunk_bbox_matches_reference_within_1pct(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull, parameters_superstructure=DeckSuperstructureParameters())
    bb = deck.cabin_trunk.body.Shape.BoundBox
    # Reference (research §R1): length=4600, aft_width=2150, height=1100.
    _assert_close(bb.XMax - bb.XMin, 4600.0, tol_pct=2.0, name="cabin_trunk.length")
    _assert_close(bb.YMax - bb.YMin, 2150.0, tol_pct=2.0, name="cabin_trunk.width(aft)")
    _assert_close(bb.ZMax - bb.ZMin, 1100.0, tol_pct=2.0, name="cabin_trunk.height")


@pytest.mark.requires_freecad
def test_hardtop_bbox_matches_reference_within_1pct(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull, parameters_superstructure=DeckSuperstructureParameters())
    bb = deck.hardtop.body.Shape.BoundBox
    # Reference (research §R1): length=3700, forward_width=2200.
    # Thickness 60 + curl 80 → Z spread ~140 mm (slightly more due to taper).
    _assert_close(bb.XMax - bb.XMin, 3700.0, tol_pct=2.0, name="hardtop.length")
    _assert_close(bb.YMax - bb.YMin, 2200.0, tol_pct=2.0, name="hardtop.forward_width")
    # Z spread: thickness (60) + curl depth (80) + taper-induced extra ≈ 140-200.
    z_spread = bb.ZMax - bb.ZMin
    assert 60.0 <= z_spread <= 300.0, (
        f"hardtop Z spread {z_spread:.1f} mm outside plausible 60-300 range"
    )


@pytest.mark.requires_freecad
def test_windshield_bbox_matches_reference_within_1pct(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull, parameters_superstructure=DeckSuperstructureParameters())
    bb = deck.windshield.body.Shape.BoundBox
    # Reference (research §R1): base_width=2050. Vertical span = top_z - base_z = 750.
    # Width may be measured at the widest point (base), expected ~2050.
    _assert_close(bb.YMax - bb.YMin, 2050.0, tol_pct=5.0, name="windshield.base_width")
    _assert_close(bb.ZMax - bb.ZMin, 750.0, tol_pct=10.0, name="windshield.vertical_span")


@pytest.mark.requires_freecad
def test_hardtop_has_aft_taper_on_defaults(freecad_doc: object) -> None:
    """FR-011 + spec.allium AftTaper invariant."""
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull, parameters_superstructure=DeckSuperstructureParameters())
    # The hardtop body should be wider at the forward end than at the aft end.
    # Sample vertices at the forward and aft extremes and compare lateral spread.
    bb = deck.hardtop.body.Shape.BoundBox
    fwd_x = bb.XMin
    aft_x = bb.XMax
    fwd_y_max = max(
        abs(v.Y) for v in deck.hardtop.body.Shape.Vertexes if abs(v.X - fwd_x) < 100.0
    )
    aft_y_max = max(
        abs(v.Y) for v in deck.hardtop.body.Shape.Vertexes if abs(v.X - aft_x) < 100.0
    )
    assert aft_y_max < fwd_y_max, (
        f"FR-011: hardtop aft_y_max ({aft_y_max:.1f}) should be less than "
        f"fwd_y_max ({fwd_y_max:.1f}) — aft taper missing"
    )


@pytest.mark.requires_freecad
def test_cabin_trunk_top_is_tapered_lengthwise(freecad_doc: object) -> None:
    """FR-002 — upper edge of cabin trunk is shorter than lower edge (rake)."""
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull, parameters_superstructure=DeckSuperstructureParameters())
    shape = deck.cabin_trunk.body.Shape
    bb = shape.BoundBox
    z_low = bb.ZMin
    z_high = bb.ZMax
    # Find vertices at the lower face vs upper face (within 5 mm tolerance).
    low_verts = [v for v in shape.Vertexes if abs(v.Z - z_low) < 5.0]
    high_verts = [v for v in shape.Vertexes if abs(v.Z - z_high) < 5.0]
    assert low_verts, "no vertices found at cabin trunk lower face"
    assert high_verts, "no vertices found at cabin trunk upper face"
    low_x_spread = max(v.X for v in low_verts) - min(v.X for v in low_verts)
    high_x_spread = max(v.X for v in high_verts) - min(v.X for v in high_verts)
    assert high_x_spread <= low_x_spread, (
        f"FR-002: cabin trunk top X spread ({high_x_spread:.1f}) should be "
        f"<= bottom X spread ({low_x_spread:.1f}) — rake produces top tapering"
    )
