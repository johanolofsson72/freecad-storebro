"""Unit tests for spec 010 DeckHardwareParameters composite (FR-012)."""

from __future__ import annotations

from storebro.deck import (
    AnchorLockerParameters,
    BowPulpitParameters,
    CleatParameters,
    DeckHardwareParameters,
    LifelineParameters,
    RubrailParameters,
)


def test_defaults_construct_all_subcomponents() -> None:
    p = DeckHardwareParameters()
    assert isinstance(p.rubrail, RubrailParameters)
    assert isinstance(p.bow_pulpit, BowPulpitParameters)
    assert isinstance(p.lifelines, LifelineParameters)
    assert isinstance(p.anchor_locker, AnchorLockerParameters)
    assert isinstance(p.cleats, CleatParameters)


def test_default_factory_independence() -> None:
    """Each composite instance gets its own sub-dataclass instances."""
    a = DeckHardwareParameters()
    b = DeckHardwareParameters()
    assert a.rubrail is not b.rubrail
    assert a.cleats is not b.cleats


def test_overrides_are_carried() -> None:
    p = DeckHardwareParameters(
        rubrail=RubrailParameters(height=80.0),
        cleats=CleatParameters(station_count=3),
    )
    assert p.rubrail.height == 80.0
    assert p.cleats.station_count == 3
    # Non-overridden components keep defaults.
    assert p.lifelines.line_count == 1


def test_frozen() -> None:
    import dataclasses

    p = DeckHardwareParameters()
    try:
        p.rubrail = RubrailParameters()  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:  # pragma: no cover
        raise AssertionError("DeckHardwareParameters should be frozen")
