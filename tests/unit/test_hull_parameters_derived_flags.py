"""Spec 009 T008 — unit tests for HullParameters computed properties."""

from __future__ import annotations

import pytest

from storebro.hull import (
    B_SPLINE_STATION_COUNT_THRESHOLD,
    HullParameters,
)


@pytest.mark.parametrize("n", [3, 5, 7, 8, 9, 11, 15, 21])
def test_uses_b_spline_loft_is_always_false_in_v103(n: int) -> None:
    """B-spline loft is deferred to v1.1+ — flag always reports False in v1.0.3."""
    assert HullParameters(station_count=n).uses_b_spline_loft is False


@pytest.mark.parametrize("n", [8, 9, 11, 15, 21])
def test_uses_zero_forefoot_stem_at_or_above_threshold(n: int) -> None:
    assert HullParameters(station_count=n).uses_zero_forefoot_stem is True


@pytest.mark.parametrize("n", [3, 5, 7])
def test_uses_zero_forefoot_stem_below_threshold(n: int) -> None:
    assert HullParameters(station_count=n).uses_zero_forefoot_stem is False


def test_uses_bilge_arc_is_always_false_in_v103() -> None:
    """Bilge arc is deferred to v1.1+ — flag always reports False in v1.0.3."""
    assert HullParameters(bilge_radius=0.20).uses_bilge_arc is False


def test_uses_bilge_arc_false_when_radius_zero() -> None:
    assert HullParameters(bilge_radius=0.0).uses_bilge_arc is False


def test_max_bilge_radius_is_min_of_half_beam_and_draft() -> None:
    p = HullParameters()
    assert p.max_bilge_radius == min(p.beam_max / 2.0, p.draft)


def test_b_spline_threshold_constant_is_eight() -> None:
    assert B_SPLINE_STATION_COUNT_THRESHOLD == 8


def test_computed_properties_are_read_only() -> None:
    p = HullParameters()
    with pytest.raises(AttributeError):
        p.uses_b_spline_loft = False  # type: ignore[misc]
