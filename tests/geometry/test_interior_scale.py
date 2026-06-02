"""Geometry test: interior built at true millimetre scale (spec 017).

Covers spec 017 FR-001, FR-012, SC-001, SC-002, SC-003 — the explicit guard
against regressing to the metre-magnitude defect (a 2.4 m cabin building as a
2.4 mm box, ~1000x too small).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from storebro import build_deck, build_hull, build_interior

_M_TO_MM = 1000.0

# A single unfurnished compartment via a CUSTOM (non-canonical) layout name, so
# build_interior takes the boxy `_build_compartment` path and `body` is one box
# whose bounding box equals the compartment dimensions exactly (no furniture
# insets / bulkhead trimming the extent — those would shorten a canonical
# furnished compound, see test below).
_CUSTOM_LAYOUT = textwrap.dedent(
    """\
    schema_version: 1
    layout_name: ScaleProbe
    source: spec 017 regression
    compartments:
      - name: ProbeCabin
        type: forward_cabin
        position: { x: 0.4, y: 0, z: 0.5 }
        dimensions: { length: 2.4, width: 2.0, height: 1.2 }
    """
)


@pytest.mark.requires_freecad
def test_compartment_box_built_at_mm_scale(freecad_doc: object, tmp_path: Path) -> None:
    """FR-012 / SC-001: a 2.4 m compartment yields a ~2400 mm box, not ~2.4 mm."""
    layout_file = tmp_path / "scale_probe.yaml"
    layout_file.write_text(_CUSTOM_LAYOUT, encoding="utf-8")

    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout=str(layout_file))

    cabin = interior.compartments[0]
    assert not cabin.is_furnished  # custom layout → boxy placeholder
    bb = cabin.body.Shape.BoundBox
    assert bb.XLength == pytest.approx(2400.0, rel=0.01)
    assert bb.YLength == pytest.approx(2000.0, rel=0.01)
    assert bb.ZLength == pytest.approx(1200.0, rel=0.01)
    # Positioned at position * 1000 (mm), not at the metre-magnitude origin speck.
    assert bb.XMin == pytest.approx(0.4 * _M_TO_MM, abs=1e-3)
    assert bb.ZMin == pytest.approx(0.5 * _M_TO_MM, abs=1e-3)

    # GUI display properties (already mm) agree with the geometry (FR-008).
    assert cabin.body.Length == pytest.approx(2400.0, rel=1e-9)
    assert cabin.body.Height == pytest.approx(1200.0, rel=1e-9)


@pytest.mark.requires_freecad
def test_interior_footprint_nests_in_hull(freecad_doc: object) -> None:
    """SC-003: the interior's X-Y footprint sits inside the hull and above the keel."""
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout="Alternativ1")

    hb = hull.body.Shape.BoundBox
    xs: list[float] = []
    ys: list[float] = []
    z_floor: list[float] = []
    for c in interior.compartments:
        bb = c.body.Shape.BoundBox
        xs += [bb.XMin, bb.XMax]
        ys += [bb.YMin, bb.YMax]
        z_floor.append(bb.ZMin)

    tol = 1e-3
    # X-Y footprint contained within the hull (shared mm coordinate system).
    assert min(xs) >= hb.XMin - tol
    assert max(xs) <= hb.XMax + tol
    assert min(ys) >= hb.YMin - tol
    assert max(ys) <= hb.YMax + tol
    # Interior floor sits above the keel (Z bounded below by the keel; the cabin
    # rises into the cabin-trunk headroom above the hull sheer by design).
    assert min(z_floor) >= hb.ZMin - tol
    # Scale sanity: the footprint spans metres-in-mm, not a sub-millimetre speck.
    assert max(xs) - min(xs) > 1000.0


@pytest.mark.requires_freecad
def test_galley_counter_height_at_true_scale(freecad_doc: object) -> None:
    """SC-002 representative: a furnished galley counter top sits ~900 mm above its floor."""
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout="Alternativ1")

    galley = next(c for c in interior.compartments if c.spec.compartment_type == "galley")
    assert galley.is_furnished
    counter = galley.furniture[0]  # _build_galley_counter is first
    floor_mm = galley.spec.position.z * _M_TO_MM
    # Default galley counter_height is 900 mm; the worktop top sits at floor + 900.
    assert counter.Shape.BoundBox.ZMax == pytest.approx(floor_mm + 900.0, rel=0.01)
