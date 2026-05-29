"""Unit tests for spec 011 DeckGlazingParameters composite (FR-010)."""

from __future__ import annotations

from storebro.deck import (
    CabinWindowParameters,
    DeckGlazingParameters,
    WindshieldGlazingParameters,
)


def test_defaults_construct() -> None:
    p = DeckGlazingParameters()
    assert isinstance(p.cabin_windows, CabinWindowParameters)
    assert isinstance(p.windshield, WindshieldGlazingParameters)
    assert p.cabin_windows.count_per_side == 1
    assert p.windshield.enabled is True


def test_default_factory_independence() -> None:
    a = DeckGlazingParameters()
    b = DeckGlazingParameters()
    assert a.cabin_windows is not b.cabin_windows
    assert a.windshield is not b.windshield


def test_overrides_carried() -> None:
    p = DeckGlazingParameters(
        cabin_windows=CabinWindowParameters(count_per_side=2),
        windshield=WindshieldGlazingParameters(enabled=False),
    )
    assert p.cabin_windows.count_per_side == 2
    assert p.windshield.enabled is False
