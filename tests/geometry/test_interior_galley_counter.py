"""Geometry test: galley counter with blind recesses, stays manifold (T012).

Covers spec 012 FR-005, FR-007, SC-002 + spec.allium GalleyCounterAlwaysManifold.
"""

from __future__ import annotations

import pytest

from storebro import (
    FurnitureParameters,
    GalleyParameters,
    build_deck,
    build_hull,
    build_interior,
)
from storebro.interior import InteriorParameterError


def _galley(interior: object) -> object:
    return next(c for c in interior.compartments if c.spec.compartment_type == "galley")


@pytest.mark.requires_freecad
def test_galley_counter_is_single_solid(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck, layout="Alternativ1")
    counter = _galley(interior).furniture[0]
    shape = counter.Shape
    assert len(shape.Solids) == 1, "FR-007: galley counter must stay a single solid"
    assert shape.isValid()


@pytest.mark.requires_freecad
def test_cutouts_disabled_gives_plain_counter(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    fp = FurnitureParameters(galley=GalleyParameters(cutouts_enabled=False))
    plain = build_interior(hull, deck, layout="Alternativ1", parameters_furniture=fp)
    # A plain counter encloses more volume than one with recesses.
    fp2 = FurnitureParameters(galley=GalleyParameters(cutouts_enabled=True))
    recessed = build_interior(
        build_hull(), build_deck(build_hull()), layout="Alternativ1", parameters_furniture=fp2
    )
    assert _galley(plain).furniture[0].Shape.Volume >= _galley(recessed).furniture[0].Shape.Volume


@pytest.mark.requires_freecad
def test_recess_deeper_than_counter_rejected(freecad_doc: object) -> None:
    # Caught at the dataclass layer before any build.
    with pytest.raises(InteriorParameterError):
        GalleyParameters(sink_recess_depth=50.0, counter_thickness=40.0)
