"""Geometry test: a mid-build failure rolls the document back (T034).

Covers spec 014 FR-010, SC-006 + spec.allium RollbackOnPartialFailure.
"""

from __future__ import annotations

import pytest

from storebro import build_deck, build_hull, build_propulsion
from storebro import propulsion as prop_mod
from storebro.propulsion import PropulsionConstructionError


def test_rollback_leaves_no_orphan_objects(
    freecad_doc: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    names_before = {obj.Name for obj in hull.document.Objects}

    def _boom(*args: object, **kwargs: object) -> object:
        raise RuntimeError("injected failure during propeller build")

    # Fail partway through (after beds/engines/shafts of the first train).
    monkeypatch.setattr(prop_mod, "_build_propeller", _boom)

    with pytest.raises(PropulsionConstructionError):
        build_propulsion(hull, deck)

    names_after = {obj.Name for obj in hull.document.Objects}
    assert names_after == names_before, "rollback must remove every object added mid-build"


def test_parameter_error_passes_through_not_wrapped(
    freecad_doc: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    from storebro.propulsion import PropulsionParameterError

    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)

    def _raise_param(*args: object, **kwargs: object) -> object:
        raise PropulsionParameterError("engine_bed.height_mm", -1.0, "> 0")

    monkeypatch.setattr(prop_mod, "_build_engine_bed", _raise_param)
    with pytest.raises(PropulsionParameterError):
        build_propulsion(hull, deck)
