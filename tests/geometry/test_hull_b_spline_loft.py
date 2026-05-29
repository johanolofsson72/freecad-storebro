"""Spec 009 T009 + T035 — geometry tests for the denser-station hull.

US1 MVP. Verifies that default-parameter ``build_hull()`` produces a hull with:
    1. station_count = DEFAULT_STATION_COUNT (9) station sketches
    2. AdditiveLoft with Ruled=True (piecewise-linear; B-spline deferred
       to v1.1+ per spec 009 closure note)
    3. Closed Shape with positive Volume
    4. Body.Tip is the PartDesign::Mirrored feature
    5. Geometry-construction time within HULL_BUILD_TIME_BUDGET_SECONDS budget
"""

from __future__ import annotations

import time

import pytest

from storebro.hull import (
    DEFAULT_STATION_COUNT,
    HULL_BUILD_TIME_BUDGET_SECONDS,
    HullGlazingParameters,
    HullParameters,
    PortholeParameters,
    build_hull,
)

pytestmark = pytest.mark.requires_freecad

# spec 011: glazing off, to count only the station sketches and see the mirror
# as Tip (default portholes add 6 sketches and make the Tip a Pocket).
_NO_PORTHOLES = HullGlazingParameters(portholes=PortholeParameters(count_per_side=0))


def test_default_hull_has_station_count_sketches() -> None:
    hull = build_hull(parameters_glazing=_NO_PORTHOLES)
    sketches = [
        obj
        for obj in hull.body.Group
        if obj.TypeId == "Sketcher::SketchObject"
    ]
    assert len(sketches) == DEFAULT_STATION_COUNT


def test_default_hull_loft_is_ruled_true() -> None:
    """v1.0.3 ships with Ruled=True everywhere; B-spline deferred to v1.1+."""
    hull = build_hull()
    lofts = [
        obj
        for obj in hull.body.Group
        if obj.TypeId == "PartDesign::AdditiveLoft"
    ]
    assert len(lofts) == 1
    assert lofts[0].Ruled is True


def test_default_hull_shape_is_closed_and_has_positive_volume() -> None:
    hull = build_hull()
    assert hull.body.Shape.isClosed() is True
    assert hull.body.Shape.Volume > 0


def test_default_hull_tip_is_mirrored_feature() -> None:
    # With glazing off the Tip is the mirror; default portholes append Pockets
    # after it (covered by tests/geometry/test_hull_partdesign_feature_types.py).
    hull = build_hull(parameters_glazing=_NO_PORTHOLES)
    assert hull.body.Tip.TypeId == "PartDesign::Mirrored"


def test_legacy_station_count_uses_ruled_true_loft() -> None:
    """station_count=5 also uses Ruled=True (matches spec 007 baseline)."""
    hull = build_hull(HullParameters(station_count=5))
    lofts = [
        obj
        for obj in hull.body.Group
        if obj.TypeId == "PartDesign::AdditiveLoft"
    ]
    assert len(lofts) == 1
    assert lofts[0].Ruled is True


def test_legacy_station_count_has_five_sketches() -> None:
    hull = build_hull(HullParameters(station_count=5), parameters_glazing=_NO_PORTHOLES)
    sketches = [
        obj
        for obj in hull.body.Group
        if obj.TypeId == "Sketcher::SketchObject"
    ]
    assert len(sketches) == 5


def test_default_hull_build_within_time_budget() -> None:
    """T035 / SC-010: geometry construction completes within budget."""
    params = HullParameters()
    started = time.perf_counter()
    build_hull(params)
    elapsed = time.perf_counter() - started
    assert elapsed <= HULL_BUILD_TIME_BUDGET_SECONDS, (
        f"hull build took {elapsed:.2f}s, exceeds budget "
        f"{HULL_BUILD_TIME_BUDGET_SECONDS}s"
    )
