"""Spec 009 T017 — backward-compat tests for legacy HullParameters callers.

Pre-v1.0.3 callers construct ``HullParameters`` without ``station_count``
or ``bilge_radius``. They must continue to work; the new fields take their
v1.0.3 defaults silently.
"""

from __future__ import annotations

from storebro.hull import (
    DEFAULT_BILGE_RADIUS_M,
    DEFAULT_STATION_COUNT,
    HullParameters,
)


def test_default_construction_succeeds() -> None:
    p = HullParameters()
    assert p.station_count == DEFAULT_STATION_COUNT
    assert p.bilge_radius == DEFAULT_BILGE_RADIUS_M


def test_legacy_field_only_construction_succeeds() -> None:
    p = HullParameters(loa=10.34, beam_max=3.13, draft=1.10)
    assert p.station_count == DEFAULT_STATION_COUNT
    assert p.bilge_radius == DEFAULT_BILGE_RADIUS_M


def test_legacy_full_field_set_succeeds() -> None:
    p = HullParameters(
        loa=10.34,
        beam_max=3.13,
        draft=1.10,
        freeboard=0.95,
        deadrise_amidships=8.0,
        sheer_height_aft=0.95,
        sheer_height_fwd=1.16,
        transom_angle=5.0,
        stem_rake_angle=6.0,
    )
    assert p.station_count == DEFAULT_STATION_COUNT
    assert p.bilge_radius == DEFAULT_BILGE_RADIUS_M


def test_explicit_legacy_station_count_opts_into_legacy_loft() -> None:
    p = HullParameters(station_count=5)
    assert p.uses_b_spline_loft is False
    assert p.uses_zero_forefoot_stem is False


def test_explicit_zero_bilge_radius_opts_into_sharp_chine() -> None:
    p = HullParameters(bilge_radius=0.0)
    assert p.uses_bilge_arc is False
