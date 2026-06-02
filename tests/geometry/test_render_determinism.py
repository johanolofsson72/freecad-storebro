"""Geometry test: coloring is deterministic + headless-safe (spec 015 T014).

Two independent builds with identical inputs produce identical render attributes
(contract invariant 6 / FR-004), and the applier never crashes headless where
ViewObject is None (FR-005).
"""

from __future__ import annotations

from typing import Any

import FreeCAD  # type: ignore[import-not-found]

from storebro import build_deck, build_hull


def _colour_map(deck: Any, hull: Any) -> dict[str, tuple[tuple[int, ...], str]]:
    out: dict[str, tuple[tuple[int, ...], str]] = {}
    bodies = [
        hull.body,
        deck.deck_plate.body,
        deck.cabin_trunk.body,
        deck.windshield.body,
        deck.rubrail.body,
        deck.railings.body,
        deck.cleats.body,
    ]
    for b in bodies:
        out[b.Label] = (
            tuple(round(c * 255) for c in b.RenderColor),
            b.RenderMaterialName,
        )
    return out


def test_two_builds_have_identical_attributes() -> None:
    doc_a = FreeCAD.newDocument("det_a")
    try:
        hull_a = build_hull(document=doc_a)
        deck_a = build_deck(hull_a)
        map_a = _colour_map(deck_a, hull_a)
    finally:
        FreeCAD.closeDocument(doc_a.Name)

    doc_b = FreeCAD.newDocument("det_b")
    try:
        hull_b = build_hull(document=doc_b)
        deck_b = build_deck(hull_b)
        map_b = _colour_map(deck_b, hull_b)
    finally:
        FreeCAD.closeDocument(doc_b.Name)

    assert map_a == map_b


def test_applier_is_headless_safe(freecad_doc: Any) -> None:
    """In console mode obj.ViewObject is None — coloring must still succeed."""
    hull = build_hull(document=freecad_doc)
    assert getattr(hull.body, "ViewObject", None) is None
    # Build succeeded with coloring on → headless path works.
    assert "RenderColor" in hull.body.PropertiesList
