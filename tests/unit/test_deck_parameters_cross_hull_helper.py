"""Unit test for _validate_cross_hull_constraints (T035).

Covers FR-004 + FR-012 cross-hull validation logic using stub hull objects.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from storebro import DeckParameterError, DeckParameters
from storebro.deck import _validate_cross_hull_constraints


def _stub_hull(loa: float, beam_max: float) -> SimpleNamespace:
    return SimpleNamespace(parameters=SimpleNamespace(loa=loa, beam_max=beam_max))


def test_cabin_longer_than_loa_rejected() -> None:
    hull = _stub_hull(loa=10.0, beam_max=3.2)
    params = DeckParameters(cabin_trunk_length=10.0)  # >= loa
    with pytest.raises(DeckParameterError) as exc_info:
        _validate_cross_hull_constraints(hull, params)
    assert "cabin_trunk_length" in exc_info.value.parameter_name


def test_cabin_past_bow_rejected() -> None:
    hull = _stub_hull(loa=10.0, beam_max=3.2)
    params = DeckParameters(cabin_trunk_length=4.5, cabin_trunk_fwd_offset=7.0)
    with pytest.raises(DeckParameterError) as exc_info:
        _validate_cross_hull_constraints(hull, params)
    assert "fwd_offset+length" in exc_info.value.parameter_name


def test_cabin_too_wide_rejected() -> None:
    hull = _stub_hull(loa=10.35, beam_max=3.20)
    params = DeckParameters(cabin_trunk_width=2.50, deck_side_walkway=0.40)
    # 2.50 + 2*0.40 = 3.30 > 3.20
    with pytest.raises(DeckParameterError) as exc_info:
        _validate_cross_hull_constraints(hull, params)
    assert "width" in exc_info.value.parameter_name


def test_default_params_on_default_hull_accepted() -> None:
    hull = _stub_hull(loa=10.35, beam_max=3.20)
    params = DeckParameters()
    # Should not raise.
    _validate_cross_hull_constraints(hull, params)
