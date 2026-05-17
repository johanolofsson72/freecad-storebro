"""Geometry test: failed build leaves no orphan Bodies (T033).

Covers SC-008 + FR-018.
"""

from __future__ import annotations

import pytest

import storebro.deck as deck_mod
from storebro import DeckConstructionError, build_deck, build_hull


def test_failure_mid_build_rolls_back_all_added_bodies(
    freecad_doc: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    hull = build_hull(document=freecad_doc)
    objects_before = [obj.Name for obj in freecad_doc.Objects]

    def forced_failure(*args: object, **kwargs: object) -> None:
        raise RuntimeError("forced failure during hardtop build (test)")

    # Force a failure during the 4th sub-Body so 3 are already added.
    monkeypatch.setattr(deck_mod, "_build_hardtop", forced_failure)

    with pytest.raises(DeckConstructionError) as exc_info:
        build_deck(hull)

    assert exc_info.value.underlying is not None
    assert isinstance(exc_info.value.underlying, RuntimeError)

    # No orphan Bodies remain in the document.
    objects_after = [obj.Name for obj in freecad_doc.Objects]
    assert objects_after == objects_before, (
        f"FR-018/SC-008 violation: rollback left orphans. "
        f"before={objects_before}, after={objects_after}"
    )
