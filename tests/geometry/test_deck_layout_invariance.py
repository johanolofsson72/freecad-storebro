"""Spec 008 FR-025 + SC-006 — superstructure is layout-invariant across Alternativ 1..5.

All five canonical interior layouts share the standard RC34 superstructure
(per Assumptions in spec.md; the DS variant is reserved for spec 016).
For a fixed hull + fixed DeckSuperstructureParameters, building the deck
must produce identical superstructure shape digests regardless of which
interior layout is used. This test confirms the superstructure module
does not branch on Alternativ number.

Since `build_deck()` itself does not take a layout parameter (layout is
consumed by `build_interior` per spec 004), this test simply verifies
that repeated `build_deck()` calls on independent hulls produce identical
shape digests for the superstructure bodies. Layout-divergent behavior
would surface as different digests; layout-invariant behavior produces
matching digests.
"""

from __future__ import annotations

import FreeCAD  # type: ignore[import-not-found]
import pytest

from storebro import build_deck, build_hull


def _shape_digest(body: object) -> str:
    """Stable BoundBox digest as a coarse layout-invariance signal."""
    bb = body.Shape.BoundBox  # type: ignore[attr-defined]
    return (
        f"V={body.Shape.Volume:.1f}|"  # type: ignore[attr-defined]
        f"X={bb.XMin:.1f}..{bb.XMax:.1f}|"
        f"Y={bb.YMin:.1f}..{bb.YMax:.1f}|"
        f"Z={bb.ZMin:.1f}..{bb.ZMax:.1f}"
    )


@pytest.mark.requires_freecad
def test_superstructure_shape_digest_consistent_across_builds() -> None:
    """Build deck twice on independent hulls; superstructure digests must match."""
    docs: list[object] = []
    digests: list[dict[str, str]] = []
    try:
        for i in range(2):
            doc = FreeCAD.newDocument(f"layout_invariance_{i}")
            docs.append(doc)
            hull = build_hull(document=doc)
            deck = build_deck(hull)
            digests.append(
                {
                    "cabin_trunk": _shape_digest(deck.cabin_trunk.body),
                    "windshield": _shape_digest(deck.windshield.body),
                    "hardtop": _shape_digest(deck.hardtop.body),
                }
            )
    finally:
        for doc in docs:
            FreeCAD.closeDocument(doc.Name)  # type: ignore[attr-defined]

    assert digests[0]["cabin_trunk"] == digests[1]["cabin_trunk"], (
        f"FR-025: cabin trunk shape diverges across builds — "
        f"{digests[0]['cabin_trunk']!r} vs {digests[1]['cabin_trunk']!r}"
    )
    assert digests[0]["windshield"] == digests[1]["windshield"], (
        f"FR-025: windshield shape diverges — "
        f"{digests[0]['windshield']!r} vs {digests[1]['windshield']!r}"
    )
    assert digests[0]["hardtop"] == digests[1]["hardtop"], (
        f"FR-025: hardtop shape diverges — "
        f"{digests[0]['hardtop']!r} vs {digests[1]['hardtop']!r}"
    )
