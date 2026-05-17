"""Geometry test: GUI-editable Body properties (T027).

Covers FR-007. Verifies that the returned Body exposes the 8 hull
dimensions as named FreeCAD properties so the GUI can show and edit them.
"""

from __future__ import annotations

from storebro import build_hull

REQUIRED_PROPERTIES = [
    "LOA",
    "BeamMax",
    "Draft",
    "Freeboard",
    "SheerHeightAft",
    "SheerHeightFwd",
    "DeadriseAmidships",
    "TransomAngle",
]


def test_body_exposes_all_named_hull_properties(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    body = hull.body
    for prop in REQUIRED_PROPERTIES:
        assert hasattr(body, prop), f"Body is missing {prop!r} property (FR-007)"


def test_property_values_match_input_parameters(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    body = hull.body
    p = hull.parameters
    # Lengths stored in mm; compare with tolerance.
    assert abs(body.LOA.Value - p.loa * 1000.0) < 1e-6
    assert abs(body.BeamMax.Value - p.beam_max * 1000.0) < 1e-6
    # Angles in degrees, no unit conversion.
    assert abs(body.DeadriseAmidships.Value - p.deadrise_amidships) < 1e-9
