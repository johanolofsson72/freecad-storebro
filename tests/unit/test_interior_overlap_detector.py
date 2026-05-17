"""Unit tests for compartment overlap detection (T022).

Covers FR-012.
"""

from __future__ import annotations

import pytest

from storebro import InteriorParameterError
from storebro.interior import (
    CompartmentSpec,
    Dimensions3D,
    Position3D,
    _aabb_intersection_volume,
    _validate_no_overlaps,
)


def _spec(name, x, z=0.5, length=2.0, width=1.0, height=1.0):
    return CompartmentSpec(
        name=name,
        compartment_type="forward_cabin",
        position=Position3D(x, 0, z),
        dimensions=Dimensions3D(length, width, height),
    )


def test_disjoint_pair_zero_volume() -> None:
    a = _spec("A", x=0.0)
    b = _spec("B", x=3.0)  # disjoint
    assert _aabb_intersection_volume(a, b) == 0.0


def test_face_touching_zero_volume() -> None:
    a = _spec("A", x=0.0, length=2.0)
    b = _spec("B", x=2.0, length=2.0)  # face-touching at x=2
    assert _aabb_intersection_volume(a, b) == 0.0


def test_full_overlap_full_volume() -> None:
    a = _spec("A", x=0.0, length=2.0, width=1.0, height=1.0)
    b = _spec("B", x=0.0, length=2.0, width=1.0, height=1.0)
    assert _aabb_intersection_volume(a, b) == pytest.approx(2.0 * 1.0 * 1.0)


def test_partial_overlap() -> None:
    a = _spec("A", x=0.0, length=2.0, width=1.0, height=1.0)
    b = _spec("B", x=1.0, length=2.0, width=1.0, height=1.0)  # 1m x-overlap
    assert _aabb_intersection_volume(a, b) == pytest.approx(1.0 * 1.0 * 1.0)


def test_validate_no_overlaps_passes_for_disjoint() -> None:
    a = _spec("A", x=0.0)
    b = _spec("B", x=3.0)
    _validate_no_overlaps((a, b), "test")


def test_validate_no_overlaps_passes_for_face_touching() -> None:
    a = _spec("A", x=0.0, length=2.0)
    b = _spec("B", x=2.0, length=2.0)
    _validate_no_overlaps((a, b), "test")


def test_validate_no_overlaps_rejects_volumetric_overlap() -> None:
    a = _spec("A", x=0.0, length=2.0)
    b = _spec("B", x=1.0, length=2.0)
    with pytest.raises(InteriorParameterError) as exc:
        _validate_no_overlaps((a, b), "test")
    assert "A" in exc.value.reason
    assert "B" in exc.value.reason
