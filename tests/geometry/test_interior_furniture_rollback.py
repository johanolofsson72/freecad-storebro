"""Geometry test: failed furniture build rolls back (T020).

Covers spec 012 FR-012, SC-005 + spec.allium RollbackOnPartialFailure.
"""

from __future__ import annotations

import pytest

import storebro.interior as interior_mod
from storebro import InteriorConstructionError, build_deck, build_hull, build_interior


def test_furniture_failure_rolls_back(freecad_doc: object, monkeypatch: pytest.MonkeyPatch) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    objects_before = [o.Name for o in freecad_doc.Objects]

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("forced furniture-build failure (test)")

    monkeypatch.setattr(interior_mod, "_build_salon_furniture", boom)
    with pytest.raises(InteriorConstructionError):
        build_interior(hull, deck, layout="Alternativ1")
    assert [o.Name for o in freecad_doc.Objects] == objects_before
