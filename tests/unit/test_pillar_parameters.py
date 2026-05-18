"""Unit tests for spec 008 PillarParameters validation (FR-014..018, FR-026)."""

from __future__ import annotations

import pytest

from storebro.deck import DeckParameterError, PillarParameters


def test_defaults_construct_without_error() -> None:
    p = PillarParameters()
    assert p.count_per_side == 2
    assert p.diameter == 35.0
    assert p.forward_x == 5400.0
    assert p.aft_x == 7800.0
    assert p.inboard_offset_from_sheer == 80.0


def test_default_count_total_is_four() -> None:
    """4 total pillars on default (2 per side * 2 sides), matching reference photo."""
    p = PillarParameters()
    assert p.count_per_side * 2 == 4


def test_zero_count_per_side_is_allowed() -> None:
    """Zero-pillar fallback path (clarification 4) — hardtop seats on cabin trunk."""
    p = PillarParameters(count_per_side=0)
    assert p.count_per_side == 0


def test_negative_count_per_side_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        PillarParameters(count_per_side=-1)
    assert exc.value.parameter_name == "pillar_count_per_side"


@pytest.mark.parametrize("value", [0.0, -5.0])
def test_non_positive_diameter_raises(value: float) -> None:
    with pytest.raises(DeckParameterError) as exc:
        PillarParameters(diameter=value)
    assert exc.value.parameter_name == "pillar_diameter"
    assert exc.value.parameter_value == value


def test_forward_x_equal_to_aft_x_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        PillarParameters(forward_x=5000.0, aft_x=5000.0)
    assert exc.value.parameter_name == "pillar_forward_x<>aft_x"


def test_forward_x_greater_than_aft_x_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        PillarParameters(forward_x=8000.0, aft_x=5000.0)
    assert exc.value.parameter_name == "pillar_forward_x<>aft_x"


def test_negative_inboard_offset_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        PillarParameters(inboard_offset_from_sheer=-10.0)
    assert exc.value.parameter_name == "pillar_inboard_offset_from_sheer"


def test_zero_inboard_offset_is_allowed() -> None:
    """Pillar centered on the sheer line — unusual but mathematically valid."""
    p = PillarParameters(inboard_offset_from_sheer=0.0)
    assert p.inboard_offset_from_sheer == 0.0


def test_dataclass_is_frozen() -> None:
    p = PillarParameters()
    with pytest.raises(Exception):  # noqa: B017
        p.diameter = 999.0  # type: ignore[misc]
