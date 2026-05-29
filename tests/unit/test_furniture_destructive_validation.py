"""Spec 012 — destructive furniture parameter-validation tests (T023).

Dataclass-layer negative paths across the 6 attack categories. Cross-
compartment envelope guards (furniture larger than its compartment) need the
compartment dims and live in the geometry tier.

NOTE: like every deck/hull/interior dataclass, the `value <= 0` guards do not
reject non-finite NaN/inf — tracked as a module-wide deferral, not bolted onto
spec 012.
"""

from __future__ import annotations

import pytest

from storebro.interior import (
    BerthParameters,
    BulkheadParameters,
    GalleyParameters,
    HeadParameters,
    InteriorParameterError,
    SalonParameters,
)


# Category 1: invalid input (negative, zero).
@pytest.mark.parametrize("value", [-1.0, 0.0])
def test_berth_invalid_base_height_raises(value: float) -> None:
    with pytest.raises(InteriorParameterError):
        BerthParameters(base_height=value)


@pytest.mark.parametrize("value", [-1.0, 0.0])
def test_bulkhead_invalid_thickness_raises(value: float) -> None:
    with pytest.raises(InteriorParameterError):
        BulkheadParameters(thickness=value)


# Category 4: boundary values — recess exactly == thickness must be rejected
# (blind recess requires strictly less).
def test_galley_recess_equal_thickness_rejected() -> None:
    with pytest.raises(InteriorParameterError) as exc:
        GalleyParameters(sink_recess_depth=40.0, counter_thickness=40.0)
    assert exc.value.field == "galley_sink_recess_depth"


def test_galley_recess_just_below_thickness_ok() -> None:
    p = GalleyParameters(sink_recess_depth=39.9, counter_thickness=40.0)
    assert p.sink_recess_depth == 39.9


# Category: extreme but valid magnitude.
def test_extreme_but_valid_galley_constructs() -> None:
    p = GalleyParameters(counter_height=1e6, counter_thickness=1e5, sink_recess_depth=1.0)
    assert p.counter_height == 1e6


# Zero-count / disabled no-ops must NOT raise.
def test_zero_and_disabled_no_ops() -> None:
    BerthParameters(cushion_count=0)
    GalleyParameters(cutouts_enabled=False)


# Multiple invalid fields across the dataclasses.
@pytest.mark.parametrize(
    ("ctor", "kwargs", "name"),
    [
        (HeadParameters, {"toilet_height": 0.0}, "head_toilet_height"),
        (HeadParameters, {"sink_height": -1.0}, "head_sink_height"),
        (SalonParameters, {"seat_height": 0.0}, "salon_seat_height"),
        (SalonParameters, {"table_height": -5.0}, "salon_table_height"),
    ],
)
def test_assorted_non_positive_raise(ctor: type, kwargs: dict[str, float], name: str) -> None:
    with pytest.raises(InteriorParameterError) as exc:
        ctor(**kwargs)
    assert exc.value.field == name
