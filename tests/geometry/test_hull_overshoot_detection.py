"""Spec 009 T011 — overshoot detection is a no-op in v1.0.3.

Spec 009 originally required fail-fast B-spline overshoot detection. Per the
spec 009 closure note, the B-spline loft is deferred to v1.1+ because
empirical testing in FreeCAD 1.1.1 found the interpolation fundamentally
unstable for the Storebro hull profile (overshoots 22 mm to 1900 mm,
intermittent degenerate shapes). The Ruled=True (piecewise-linear) loft
cannot overshoot by construction, so the detector is a no-op in v1.0.3.

These tests assert the no-op behavior and reserve the detector slot for
the v1.1+ B-spline work to re-enable.
"""

from __future__ import annotations

import pytest

from storebro.hull import HullParameters, build_hull

pytestmark = pytest.mark.requires_freecad


def test_default_hull_builds_cleanly_without_overshoot_error() -> None:
    """Default parameters build cleanly under Ruled=True (no overshoot risk)."""
    build_hull()


def test_legacy_station_count_builds_cleanly() -> None:
    """station_count=5 builds cleanly (matches spec 007 baseline)."""
    build_hull(HullParameters(station_count=5))


def test_high_station_count_builds_cleanly() -> None:
    """High station counts that would previously overshoot now build cleanly
    because the loft is Ruled=True."""
    build_hull(HullParameters(station_count=15))
