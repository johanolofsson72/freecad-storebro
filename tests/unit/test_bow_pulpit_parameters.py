"""Unit tests for spec 010 BowPulpitParameters validation (FR-003, FR-006)."""

from __future__ import annotations

import pytest

from storebro.deck import BowPulpitParameters, DeckParameterError


def test_defaults_construct() -> None:
    p = BowPulpitParameters()
    assert p.tube_diameter == 25.0
    assert p.height == 600.0
    assert p.forward_extent == 400.0
    assert p.stanchion_count == 2


@pytest.mark.parametrize("value", [0.0, -1.0])
def test_non_positive_tube_diameter_raises(value: float) -> None:
    with pytest.raises(DeckParameterError) as exc:
        BowPulpitParameters(tube_diameter=value)
    assert exc.value.parameter_name == "bow_pulpit_tube_diameter"


@pytest.mark.parametrize("value", [0.0, -1.0])
def test_non_positive_height_raises(value: float) -> None:
    with pytest.raises(DeckParameterError) as exc:
        BowPulpitParameters(height=value)
    assert exc.value.parameter_name == "bow_pulpit_height"


def test_negative_forward_extent_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        BowPulpitParameters(forward_extent=-1.0)
    assert exc.value.parameter_name == "bow_pulpit_forward_extent"


def test_zero_forward_extent_allowed() -> None:
    assert BowPulpitParameters(forward_extent=0.0).forward_extent == 0.0


def test_negative_stanchion_count_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        BowPulpitParameters(stanchion_count=-1)
    assert exc.value.parameter_name == "bow_pulpit_stanchion_count"


def test_zero_stanchion_count_allowed() -> None:
    """Zero-stanchion fallback (FR-016)."""
    assert BowPulpitParameters(stanchion_count=0).stanchion_count == 0
