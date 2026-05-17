"""Geometry test: default build_hull() call (T026).

Covers FR-001, FR-017, SC-002 (30-s build budget).
"""

from __future__ import annotations

from storebro import build_hull


def test_default_call_returns_hull_with_body(freecad_doc: object) -> None:
    _ = freecad_doc  # fixture ensures an active doc exists
    hull = build_hull()
    assert hull.body is not None
    assert hull.label == "Hull"
    assert hull.volume > 0.0


def test_default_call_within_sc002_budget(freecad_doc: object) -> None:
    _ = freecad_doc
    hull = build_hull()
    # SC-002: under 30 s on a developer laptop (analyze remediation A3)
    assert 0.0 < hull.build_duration_seconds < 30.0


def test_second_call_in_same_document_auto_numbers_label(freecad_doc: object) -> None:
    h1 = build_hull(document=freecad_doc)
    h2 = build_hull(document=freecad_doc)
    assert h1.label == "Hull"
    # FreeCAD auto-numbers on label collision (FR-017).
    assert h2.label == "Hull001" or h2.label.startswith("Hull")
    assert h2.label != h1.label


def test_custom_name_used_for_body_label(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc, name="MyHull")
    assert hull.label == "MyHull"
