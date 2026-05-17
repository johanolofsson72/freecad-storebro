"""Unit test: HullParameters.stem_rake_angle validation.

Spec 007 FR-002. The new `stem_rake_angle` field validates against the
[0, 30] degree range. Out-of-range values raise HullParameterError with
parameter_name='stem_rake_angle' and valid_range='[0, 30] degrees'.
"""

from __future__ import annotations

import pytest

from storebro import HullParameterError, HullParameters


@pytest.mark.parametrize("rake", [-1.0, 30.5, 45.0, 90.0])
def test_stem_rake_out_of_range_raises(rake: float) -> None:
    """Stem rake outside [0, 30] degrees raises HullParameterError."""
    with pytest.raises(HullParameterError) as exc_info:
        HullParameters(stem_rake_angle=rake)
    assert exc_info.value.parameter_name == "stem_rake_angle"
    assert exc_info.value.parameter_value == rake
    assert "[0, 30] degrees" in exc_info.value.valid_range


@pytest.mark.parametrize("rake", [0.0, 6.0, 15.0, 30.0])
def test_stem_rake_in_range_constructs(rake: float) -> None:
    """Stem rake inside [0, 30] degrees constructs successfully."""
    params = HullParameters(stem_rake_angle=rake)
    assert params.stem_rake_angle == rake


def test_stem_rake_default_is_six_degrees() -> None:
    """Default stem_rake_angle is 6.0° (Einar Runius semi-displacement)."""
    params = HullParameters()
    assert params.stem_rake_angle == 6.0


def test_reference_dict_includes_stem_rake() -> None:
    """REFERENCE_STOREBRO_ROYAL_CRUISER_34_1972 mirrors the new field."""
    ref = HullParameters.REFERENCE_STOREBRO_ROYAL_CRUISER_34_1972
    assert "stem_rake_angle" in ref
    assert ref["stem_rake_angle"] == 6.0
