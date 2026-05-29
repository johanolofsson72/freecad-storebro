"""Unit tests for spec 010 AnchorLockerParameters validation (FR-003, FR-008)."""

from __future__ import annotations

import pytest

from storebro.deck import AnchorLockerParameters, DeckParameterError


def test_defaults_construct() -> None:
    p = AnchorLockerParameters()
    assert p.length == 500.0
    assert p.width == 400.0
    assert p.height == 150.0
    # Default sits on the foredeck near the bow (bow = XMax).
    assert p.center_x == 8500.0


@pytest.mark.parametrize(
    ("field", "name"),
    [
        ("length", "anchor_locker_length"),
        ("width", "anchor_locker_width"),
        ("height", "anchor_locker_height"),
    ],
)
@pytest.mark.parametrize("value", [0.0, -1.0])
def test_non_positive_dimension_raises(field: str, name: str, value: float) -> None:
    with pytest.raises(DeckParameterError) as exc:
        AnchorLockerParameters(**{field: value})
    assert exc.value.parameter_name == name


def test_negative_center_x_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        AnchorLockerParameters(center_x=-1.0)
    assert exc.value.parameter_name == "anchor_locker_center_x"


def test_zero_center_x_allowed() -> None:
    assert AnchorLockerParameters(center_x=0.0).center_x == 0.0
