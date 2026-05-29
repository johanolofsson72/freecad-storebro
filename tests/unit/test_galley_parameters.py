"""Unit tests for spec 012 GalleyParameters validation (FR-005)."""

from __future__ import annotations

import pytest

from storebro.interior import GalleyParameters, InteriorParameterError


def test_defaults_construct() -> None:
    p = GalleyParameters()
    assert p.counter_height == 900.0
    assert p.counter_thickness == 40.0
    assert p.sink_recess_depth == 30.0
    assert p.stove_recess_depth == 20.0
    assert p.cutouts_enabled is True


@pytest.mark.parametrize(
    ("field", "name"),
    [
        ("counter_height", "galley_counter_height"),
        ("counter_thickness", "galley_counter_thickness"),
    ],
)
@pytest.mark.parametrize("value", [0.0, -1.0])
def test_non_positive_dimension_raises(field: str, name: str, value: float) -> None:
    with pytest.raises(InteriorParameterError) as exc:
        GalleyParameters(**{field: value})
    assert exc.value.field == name


def test_sink_recess_too_deep_raises() -> None:
    with pytest.raises(InteriorParameterError) as exc:
        GalleyParameters(sink_recess_depth=40.0, counter_thickness=40.0)
    assert exc.value.field == "galley_sink_recess_depth"


def test_stove_recess_too_deep_raises() -> None:
    with pytest.raises(InteriorParameterError) as exc:
        GalleyParameters(stove_recess_depth=45.0, counter_thickness=40.0)
    assert exc.value.field == "galley_stove_recess_depth"


def test_cutouts_disabled_allowed() -> None:
    assert GalleyParameters(cutouts_enabled=False).cutouts_enabled is False
