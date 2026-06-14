"""Unit tests for spec 023 DsWindowParameters detailing fields + HelmParameters."""

from __future__ import annotations

import pytest

from storebro.deck import DeckParameterError, DsWindowParameters
from storebro.interior import (
    _COMPARTMENT_TYPES,  # type: ignore[attr-defined]
    HelmParameters,
    InteriorParameterError,
)

# --- DsWindowParameters spec 023 fields ------------------------------------


def test_ds_window_spec023_defaults() -> None:
    p = DsWindowParameters()
    assert p.front_window is True
    assert p.front_length == 1400.0
    assert p.front_height == 420.0
    assert p.mullions_per_window == 2  # spec 033: more divided window band
    assert p.mullion_width == 40.0
    assert p.helm_door is True
    assert p.helm_door_length == 650.0
    assert p.helm_door_height == 1100.0
    assert p.helm_door_side == "Starboard"


def test_negative_mullions_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        DsWindowParameters(mullions_per_window=-1)
    assert exc.value.parameter_name == "ds_window_mullions_per_window"


def test_zero_mullions_allowed() -> None:
    assert DsWindowParameters(mullions_per_window=0).mullions_per_window == 0


@pytest.mark.parametrize("side", ["port", "starboard", "left", ""])
def test_bad_helm_door_side_raises(side: str) -> None:
    with pytest.raises(DeckParameterError) as exc:
        DsWindowParameters(helm_door_side=side)
    assert exc.value.parameter_name == "ds_window_helm_door_side"


@pytest.mark.parametrize(
    ("field", "name"),
    [
        ("front_length", "ds_window_front_length"),
        ("front_height", "ds_window_front_height"),
        ("mullion_width", "ds_window_mullion_width"),
        ("helm_door_length", "ds_window_helm_door_length"),
        ("helm_door_height", "ds_window_helm_door_height"),
    ],
)
@pytest.mark.parametrize("value", [0.0, -1.0])
def test_non_positive_dims_raise(field: str, name: str, value: float) -> None:
    with pytest.raises(DeckParameterError) as exc:
        DsWindowParameters(**{field: value})
    assert exc.value.parameter_name == name


def test_front_window_and_helm_door_toggle() -> None:
    p = DsWindowParameters(front_window=False, helm_door=False)
    assert p.front_window is False
    assert p.helm_door is False


# --- HelmParameters (DS interior) ------------------------------------------


def test_helm_defaults() -> None:
    p = HelmParameters()
    assert p.console_height == 1100.0
    assert p.console_depth == 500.0
    assert p.seat_height == 550.0


@pytest.mark.parametrize("field", ["console_height", "console_depth", "seat_height"])
@pytest.mark.parametrize("value", [0.0, -1.0])
def test_helm_non_positive_raises(field: str, value: float) -> None:
    with pytest.raises(InteriorParameterError):
        HelmParameters(**{field: value})


def test_helm_in_compartment_types() -> None:
    assert "helm" in _COMPARTMENT_TYPES
