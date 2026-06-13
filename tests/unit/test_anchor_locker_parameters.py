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
    assert p.center_x == 9400.0


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


# --- spec 022: recessed cavity + lid ---------------------------------------


def test_spec022_defaults() -> None:
    p = AnchorLockerParameters()
    assert p.cavity_depth == 90.0
    assert p.cavity_inset == 40.0
    assert p.lid is True
    assert p.lid_thickness == 20.0


@pytest.mark.parametrize("value", [-1.0, 150.0, 200.0])
def test_cavity_depth_out_of_range_raises(value: float) -> None:
    # Valid range is [0, height) = [0, 150) at defaults.
    with pytest.raises(DeckParameterError) as exc:
        AnchorLockerParameters(cavity_depth=value)
    assert exc.value.parameter_name == "anchor_locker_cavity_depth"


def test_zero_cavity_depth_allowed() -> None:
    """cavity_depth == 0 → solid box, no cavity, no lid (spec 010 parity)."""
    assert AnchorLockerParameters(cavity_depth=0.0).cavity_depth == 0.0


@pytest.mark.parametrize("value", [0.0, -1.0, 200.0])
def test_cavity_inset_out_of_range_raises(value: float) -> None:
    # Valid range is (0, min(length, width)/2) = (0, 200) at defaults.
    with pytest.raises(DeckParameterError) as exc:
        AnchorLockerParameters(cavity_inset=value)
    assert exc.value.parameter_name == "anchor_locker_cavity_inset"


@pytest.mark.parametrize("value", [0.0, -2.0])
def test_non_positive_lid_thickness_raises(value: float) -> None:
    with pytest.raises(DeckParameterError) as exc:
        AnchorLockerParameters(lid_thickness=value)
    assert exc.value.parameter_name == "anchor_locker_lid_thickness"


def test_lid_can_be_disabled() -> None:
    assert AnchorLockerParameters(lid=False).lid is False
