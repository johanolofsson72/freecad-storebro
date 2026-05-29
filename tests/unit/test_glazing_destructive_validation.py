"""Spec 011 — destructive glazing parameter-validation tests (T022).

Dataclass-layer negative paths across the 6 attack categories. Cross-body
guards (recess vs. half-beam, opening vs. wall, frame vs. opening, porthole
vs. waterline) need the built solid and live in the geometry tier.

NOTE: like every deck/hull dataclass since spec 003, the `value <= 0` guards
do not reject non-finite NaN/inf — tracked as a module-wide deferral, not
bolted onto spec 011 (see spec 010's `reject_non_finite_dimensions`).
"""

from __future__ import annotations

import pytest

from storebro.deck import (
    CabinWindowParameters,
    DeckParameterError,
    WindshieldGlazingParameters,
)
from storebro.hull import HullParameterError, PortholeParameters


# Category 1: invalid input (negative, zero).
@pytest.mark.parametrize("value", [-1.0, 0.0])
def test_porthole_invalid_diameter_raises(value: float) -> None:
    with pytest.raises(HullParameterError):
        PortholeParameters(diameter=value)


@pytest.mark.parametrize("value", [-1.0, 0.0])
def test_cabin_window_invalid_height_raises(value: float) -> None:
    with pytest.raises(DeckParameterError):
        CabinWindowParameters(height=value)


# Category 4: boundary values.
def test_corner_radius_exactly_half_height_ok() -> None:
    # 2*r == height is the inclusive boundary — must be allowed.
    p = CabinWindowParameters(corner_radius=175.0, height=350.0)
    assert p.corner_radius == 175.0


def test_corner_radius_just_over_half_height_raises() -> None:
    with pytest.raises(DeckParameterError):
        CabinWindowParameters(corner_radius=175.1, height=350.0)


def test_porthole_forward_equals_aft_when_both_set() -> None:
    # forward == aft (both non-zero) is degenerate → reject.
    with pytest.raises(HullParameterError):
        PortholeParameters(forward_x=2000.0, aft_x=2000.0)


# Category: extreme magnitude (large but valid → no raise).
def test_extreme_but_valid_porthole_constructs() -> None:
    assert PortholeParameters(diameter=1e6, recess_depth=1e5).diameter == 1e6


# Zero-count / disabled no-ops must NOT raise.
def test_zero_and_disabled_no_ops() -> None:
    PortholeParameters(count_per_side=0)
    CabinWindowParameters(count_per_side=0)
    WindshieldGlazingParameters(enabled=False)


# Negative counts DO raise.
@pytest.mark.parametrize(
    ("ctor", "kwargs", "exc", "name"),
    [
        (PortholeParameters, {"count_per_side": -1}, HullParameterError, "porthole_count_per_side"),
        (
            CabinWindowParameters,
            {"count_per_side": -1},
            DeckParameterError,
            "cabin_window_count_per_side",
        ),
    ],
)
def test_negative_counts_raise(ctor: type, kwargs: dict[str, int], exc: type, name: str) -> None:
    with pytest.raises(exc) as ei:
        ctor(**kwargs)
    assert ei.value.parameter_name == name
