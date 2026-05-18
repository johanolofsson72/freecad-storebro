"""Unit tests for spec 008 DeckSuperstructureParameters composite + cross-component invariants (FR-023, FR-026)."""

from __future__ import annotations

import pytest

from storebro.deck import (
    CabinTrunkParameters,
    DeckParameterError,
    DeckSuperstructureParameters,
    HardtopParameters,
    PillarParameters,
    RailingParameters,
    WindshieldParameters,
)


def test_defaults_construct_without_error() -> None:
    p = DeckSuperstructureParameters()
    assert isinstance(p.cabin_trunk, CabinTrunkParameters)
    assert isinstance(p.windshield, WindshieldParameters)
    assert isinstance(p.hardtop, HardtopParameters)
    assert isinstance(p.pillars, PillarParameters)
    assert isinstance(p.railings, RailingParameters)


def test_defaults_satisfy_cross_component_invariants() -> None:
    p = DeckSuperstructureParameters()
    assert p.railings.height_above_deck < p.hardtop.height_above_deck
    assert p.pillars.forward_x >= p.cabin_trunk.length


def test_railing_taller_than_hardtop_raises() -> None:
    # railings 2500 > hardtop default 2050.
    with pytest.raises(DeckParameterError) as exc:
        DeckSuperstructureParameters(
            railings=RailingParameters(height_above_deck=2500.0),
        )
    assert exc.value.parameter_name == "railing_height<>hardtop_height"


def test_railing_equal_to_hardtop_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        DeckSuperstructureParameters(
            hardtop=HardtopParameters(height_above_deck=2050.0),
            railings=RailingParameters(height_above_deck=2050.0),
        )
    assert exc.value.parameter_name == "railing_height<>hardtop_height"


def test_pillar_inside_cabin_footprint_raises() -> None:
    # cabin_trunk.length default 4600; pillar forward_x = 4000 < 4600.
    with pytest.raises(DeckParameterError) as exc:
        DeckSuperstructureParameters(
            pillars=PillarParameters(forward_x=4000.0, aft_x=5500.0),
        )
    assert exc.value.parameter_name == "pillar_forward_x<>cabin_trunk_length"


def test_pillar_just_outside_cabin_footprint_is_allowed() -> None:
    p = DeckSuperstructureParameters(
        pillars=PillarParameters(forward_x=4600.0, aft_x=7000.0),
    )
    assert p.pillars.forward_x == p.cabin_trunk.length


def test_custom_composite_round_trips() -> None:
    custom = DeckSuperstructureParameters(
        cabin_trunk=CabinTrunkParameters(height=1300.0),
        hardtop=HardtopParameters(length=4000.0),
    )
    assert custom.cabin_trunk.height == 1300.0
    assert custom.hardtop.length == 4000.0
    # Other fields take defaults.
    assert custom.pillars.count_per_side == 2


def test_dataclass_is_frozen() -> None:
    p = DeckSuperstructureParameters()
    with pytest.raises(Exception):  # noqa: B017
        p.cabin_trunk = CabinTrunkParameters(length=9999.0)  # type: ignore[misc]
