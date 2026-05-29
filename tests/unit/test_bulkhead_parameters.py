"""Unit tests for spec 012 BulkheadParameters validation (FR-003)."""

from __future__ import annotations

import pytest

from storebro.interior import BulkheadParameters, InteriorParameterError


def test_defaults_construct() -> None:
    assert BulkheadParameters().thickness == 25.0


@pytest.mark.parametrize("value", [0.0, -1.0])
def test_non_positive_thickness_raises(value: float) -> None:
    with pytest.raises(InteriorParameterError) as exc:
        BulkheadParameters(thickness=value)
    assert exc.value.field == "bulkhead_thickness"
