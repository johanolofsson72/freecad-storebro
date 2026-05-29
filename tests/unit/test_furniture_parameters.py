"""Unit tests for spec 012 FurnitureParameters composite (FR-009)."""

from __future__ import annotations

from storebro.interior import (
    BerthParameters,
    BulkheadParameters,
    FurnitureParameters,
    GalleyParameters,
    HeadParameters,
    SalonParameters,
)


def test_defaults_construct_all_subcomponents() -> None:
    p = FurnitureParameters()
    assert isinstance(p.berth, BerthParameters)
    assert isinstance(p.galley, GalleyParameters)
    assert isinstance(p.head, HeadParameters)
    assert isinstance(p.salon, SalonParameters)
    assert isinstance(p.bulkhead, BulkheadParameters)


def test_default_factory_independence() -> None:
    a = FurnitureParameters()
    b = FurnitureParameters()
    assert a.berth is not b.berth
    assert a.galley is not b.galley


def test_overrides_carried() -> None:
    p = FurnitureParameters(
        berth=BerthParameters(base_height=400.0),
        galley=GalleyParameters(cutouts_enabled=False),
    )
    assert p.berth.base_height == 400.0
    assert p.galley.cutouts_enabled is False
    assert p.salon.seat_height == 400.0
