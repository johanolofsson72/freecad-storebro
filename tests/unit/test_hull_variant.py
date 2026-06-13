"""Unit tests for spec 031 hull_variant (FR-001..004, FR-007, FR-010, SC-002, SC-003).

No FreeCAD required. The unknown-variant guard runs before any FreeCAD call, and
`_compute_stations` is pure Python, so the reshaping is fully unit-testable here. Geometry
assertions (manifold, reproducible, variant-differs in the built solid) live in
tests/geometry/test_hull_variant_geom.py (requires_freecad)."""

from __future__ import annotations

import dataclasses
import inspect

import pytest

from storebro.hull import (
    _HARD_CHINE_CHINE_Z_FACTOR,
    Hull,
    HullParameterError,
    HullParameters,
    _compute_stations,
    build_hull,
)


def test_build_hull_default_variant_is_standard() -> None:
    assert inspect.signature(build_hull).parameters["hull_variant"].default == "standard"


def test_unknown_variant_raises_before_freecad() -> None:
    # FR-007/SC-003: the guard precedes ensure_supported_freecad, so this raises
    # without a FreeCAD runtime.
    with pytest.raises(HullParameterError) as exc:
        build_hull(hull_variant="deep_vee")  # type: ignore[arg-type]
    assert exc.value.parameter_name == "hull_variant"


def test_hull_wrapper_has_variant_fields_with_defaults() -> None:
    # FR-010: Hull records the variant + applied flag, defaulting to standard/True.
    fields = {f.name: f for f in dataclasses.fields(Hull)}
    assert fields["hull_variant"].default == "standard"
    assert fields["variant_applied"].default is True


def test_standard_stations_unchanged_vs_no_arg() -> None:
    # FR-002: the "standard" path equals the pre-031 (no-arg) station set.
    p = HullParameters()
    assert _compute_stations(p, "standard") == _compute_stations(p)


def test_standard_chine_z_factor_is_default() -> None:
    p = HullParameters()
    for prof in _compute_stations(p, "standard"):
        assert prof.chine_z_factor == 0.6


def test_hard_chine_pushes_chine_outboard_and_raises_it() -> None:
    # FR-003/FR-004: every non-stem station's chine moves outboard (larger
    # half_beam_at_bottom) and up (chine_z_factor 0.35), vertex count stays 5.
    p = HullParameters()
    std = _compute_stations(p, "standard")
    hard = _compute_stations(p, "hard_chine")
    assert len(std) == len(hard)
    n = len(hard)
    reshaped = 0
    for i, (s, h) in enumerate(zip(std, hard, strict=True)):
        assert h.vertex_count == 5
        assert h.x_position == s.x_position
        is_stem = i == n - 1
        if is_stem:
            continue  # stem (thin/legacy) is left alone
        assert h.half_beam_at_bottom > s.half_beam_at_bottom, f"station {i} chine not pushed out"
        assert h.chine_z_factor == _HARD_CHINE_CHINE_Z_FACTOR
        reshaped += 1
    assert reshaped >= 1


def test_amidships_chine_ratio_is_higher_for_hard_chine() -> None:
    # SC-002: at the amidships station (max topside half-beam) the hard-chine
    # chine_beam_ratio exceeds the standard ratio by a clear margin.
    p = HullParameters()
    std = _compute_stations(p, "standard")
    hard = _compute_stations(p, "hard_chine")
    # Amidships = the station with the widest topside half-beam.
    mid = max(range(len(std)), key=lambda i: std[i].half_beam_at_top)
    std_ratio = std[mid].half_beam_at_bottom / std[mid].half_beam_at_top
    hard_ratio = hard[mid].half_beam_at_bottom / hard[mid].half_beam_at_top
    assert hard_ratio > std_ratio
    assert hard_ratio - std_ratio > 0.1  # measurable margin (≈0.30 by design)


def test_hard_chine_keeps_topside_half_beam() -> None:
    # The reshaping moves only v1 (the chine); the topside half-beam is untouched.
    p = HullParameters()
    std = _compute_stations(p, "standard")
    hard = _compute_stations(p, "hard_chine")
    for s, h in zip(std, hard, strict=True):
        assert h.half_beam_at_top == s.half_beam_at_top
