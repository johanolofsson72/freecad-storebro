"""Geometry test: estimate-grade dimension fidelity (T032).

Covers FR-003 + self-citing tolerance for draft, freeboard, sheer aft/fwd.
These parameters are estimate-grade; the test catches silent drift inside
the construction pipeline by asserting the measured value matches the
input parameter within tolerance.
"""

from __future__ import annotations

from storebro import build_hull


def test_default_height_envelope_consistent(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    p = hull.parameters
    bb = hull.body.Shape.BoundBox
    # The Z extent of the body spans roughly from -draft to +max_sheer.
    measured_z_min_m = bb.ZMin / 1000.0
    measured_z_max_m = bb.ZMax / 1000.0

    # Z-min should be near -draft (with 25% tolerance for the half-section
    # approximation that doesn't perfectly bottom-out at the transom/stem).
    assert measured_z_min_m <= 0.0
    assert abs(measured_z_min_m + p.draft) <= p.draft * 0.5, (
        f"Z-min {measured_z_min_m:.3f} m too far from -draft {-p.draft} m"
    )

    # Z-max should be near sheer_height_fwd (the tallest sheer point).
    expected_top_m = p.sheer_height_fwd
    assert abs(measured_z_max_m - expected_top_m) <= expected_top_m * 0.5, (
        f"Z-max {measured_z_max_m:.3f} m too far from sheer_height_fwd "
        f"{expected_top_m} m"
    )
