"""Unit tests for spec 011 HullGlazingParameters composite (FR-010)."""

from __future__ import annotations

from storebro.hull import HullGlazingParameters, PortholeParameters


def test_defaults_construct() -> None:
    p = HullGlazingParameters()
    assert isinstance(p.portholes, PortholeParameters)
    assert p.portholes.count_per_side == 3


def test_default_factory_independence() -> None:
    a = HullGlazingParameters()
    b = HullGlazingParameters()
    assert a.portholes is not b.portholes


def test_override_carried() -> None:
    p = HullGlazingParameters(portholes=PortholeParameters(count_per_side=5))
    assert p.portholes.count_per_side == 5
