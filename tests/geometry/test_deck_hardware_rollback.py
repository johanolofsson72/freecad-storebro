"""Geometry test: failed hardware build rolls back the whole deck (T029).

Covers spec 010 FR-013, SC-006 + spec.allium RollbackOnPartialFailure.
"""

from __future__ import annotations

import pytest

import storebro.deck as deck_mod
from storebro import DeckConstructionError, build_deck, build_hull


def test_failure_during_hardware_rolls_back_all_bodies(
    freecad_doc: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    hull = build_hull(document=freecad_doc)
    objects_before = [obj.Name for obj in freecad_doc.Objects]

    def forced_failure(*args: object, **kwargs: object) -> None:
        raise RuntimeError("forced failure during cleat build (test)")

    # Fail during cleats — by then deck plate + superstructure + rubrail +
    # bow pulpit + anchor locker are already added; all must roll back.
    monkeypatch.setattr(deck_mod, "_build_cleats", forced_failure)

    with pytest.raises(DeckConstructionError) as exc:
        build_deck(hull)
    assert isinstance(exc.value.underlying, RuntimeError)

    objects_after = [obj.Name for obj in freecad_doc.Objects]
    assert objects_after == objects_before, (
        f"FR-013/SC-006: rollback left orphans. before={objects_before}, after={objects_after}"
    )
