"""Unit tests for spec 010 LifelineParameters validation (FR-003, FR-007, FR-017)."""

from __future__ import annotations

import pytest

from storebro.deck import DeckParameterError, LifelineParameters


def test_defaults_construct() -> None:
    p = LifelineParameters()
    assert p.line_count == 1
    assert p.tube_diameter == 12.0
    assert p.height_fraction == 1.0


def test_negative_line_count_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        LifelineParameters(line_count=-1)
    assert exc.value.parameter_name == "lifeline_line_count"


def test_zero_line_count_allowed() -> None:
    """Zero lifelines is a valid no-op (FR-016)."""
    assert LifelineParameters(line_count=0).line_count == 0


@pytest.mark.parametrize("value", [0.0, -1.0])
def test_non_positive_tube_diameter_raises(value: float) -> None:
    with pytest.raises(DeckParameterError) as exc:
        LifelineParameters(tube_diameter=value)
    assert exc.value.parameter_name == "lifeline_tube_diameter"


@pytest.mark.parametrize("value", [0.0, -0.5, 1.01, 2.0])
def test_height_fraction_out_of_range_raises(value: float) -> None:
    with pytest.raises(DeckParameterError) as exc:
        LifelineParameters(height_fraction=value)
    assert exc.value.parameter_name == "lifeline_height_fraction"


@pytest.mark.parametrize("value", [0.001, 0.5, 1.0])
def test_height_fraction_in_range_ok(value: float) -> None:
    assert LifelineParameters(height_fraction=value).height_fraction == value


# --- spec 022: catenary sag ------------------------------------------------


def test_spec022_default_sag() -> None:
    assert LifelineParameters().sag_depth == 25.0


def test_negative_sag_depth_raises() -> None:
    with pytest.raises(DeckParameterError) as exc:
        LifelineParameters(sag_depth=-1.0)
    assert exc.value.parameter_name == "lifeline_sag_depth"


def test_zero_sag_depth_allowed() -> None:
    """sag_depth == 0 → straight tube (spec 010 parity)."""
    assert LifelineParameters(sag_depth=0.0).sag_depth == 0.0
