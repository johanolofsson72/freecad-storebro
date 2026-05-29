"""Geometry test: failed glazing cut rolls back the build (T019).

Covers spec 011 FR-012, SC-006 + spec.allium RollbackOnPartialFailure, for
both the hull (portholes) and the deck (cabin windows).
"""

from __future__ import annotations

import pytest

import storebro.deck as deck_mod
import storebro.hull as hull_mod
from storebro import DeckConstructionError, build_deck, build_hull
from storebro.hull import HullConstructionError


def test_porthole_failure_rolls_back_hull(
    freecad_doc: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    objects_before = [o.Name for o in freecad_doc.Objects]

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("forced porthole-cut failure (test)")

    monkeypatch.setattr(hull_mod, "_cut_portholes", boom)
    with pytest.raises(HullConstructionError):
        build_hull(document=freecad_doc)
    assert [o.Name for o in freecad_doc.Objects] == objects_before


def test_cabin_window_failure_rolls_back_deck(
    freecad_doc: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    hull = build_hull(document=freecad_doc)
    objects_before = [o.Name for o in freecad_doc.Objects]

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("forced cabin-window-cut failure (test)")

    monkeypatch.setattr(deck_mod, "_cut_cabin_windows", boom)
    with pytest.raises(DeckConstructionError):
        build_deck(hull)
    assert [o.Name for o in freecad_doc.Objects] == objects_before
