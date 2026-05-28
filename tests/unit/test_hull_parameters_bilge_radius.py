"""Spec 009 T019 — unit tests for HullParameters.bilge_radius validation."""

from __future__ import annotations

import pytest

from storebro.hull import (
    DEFAULT_BILGE_RADIUS_M,
    HullParameterError,
    HullParameters,
)


def test_default_bilge_radius_is_0_10() -> None:
    """Reduced from 0.20 to 0.10 in spec 009 implementation (closure note:
    Sketcher.fillet() fails on amidships station above ~0.13 m radius at
    the v1.0.3 anchor profile)."""
    assert HullParameters().bilge_radius == DEFAULT_BILGE_RADIUS_M == 0.10


def test_zero_bilge_radius_is_accepted() -> None:
    HullParameters(bilge_radius=0.0)


def test_bilge_radius_at_maximum_is_accepted() -> None:
    p_default = HullParameters()
    HullParameters(bilge_radius=p_default.max_bilge_radius)


def test_negative_bilge_radius_raises() -> None:
    with pytest.raises(HullParameterError) as exc_info:
        HullParameters(bilge_radius=-0.01)
    assert exc_info.value.parameter_name == "bilge_radius"


def test_bilge_radius_exceeding_maximum_raises() -> None:
    with pytest.raises(HullParameterError) as exc_info:
        HullParameters(bilge_radius=5.0)
    err = exc_info.value
    assert err.parameter_name == "bilge_radius"
    # Message must include the maximum legal value for the default parameters.
    p_default = HullParameters()
    assert f"{p_default.max_bilge_radius:.3f}" in err.valid_range


def test_bilge_radius_just_above_maximum_raises() -> None:
    p_default = HullParameters()
    with pytest.raises(HullParameterError):
        HullParameters(bilge_radius=p_default.max_bilge_radius + 0.001)
