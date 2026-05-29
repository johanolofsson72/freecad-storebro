"""Unit tests for spec 011 WindshieldGlazingParameters validation (FR-003)."""

from __future__ import annotations

import pytest

from storebro.deck import DeckParameterError, WindshieldGlazingParameters


def test_defaults_construct() -> None:
    p = WindshieldGlazingParameters()
    assert p.enabled is True
    assert p.frame_border == 60.0
    assert p.glass_thickness == 6.0


def test_disabled_allowed() -> None:
    assert WindshieldGlazingParameters(enabled=False).enabled is False


@pytest.mark.parametrize(
    ("field", "name"),
    [
        ("frame_border", "windshield_frame_border"),
        ("glass_thickness", "windshield_glass_thickness"),
    ],
)
@pytest.mark.parametrize("value", [0.0, -1.0])
def test_non_positive_dimension_raises(field: str, name: str, value: float) -> None:
    with pytest.raises(DeckParameterError) as exc:
        WindshieldGlazingParameters(**{field: value})
    assert exc.value.parameter_name == name
