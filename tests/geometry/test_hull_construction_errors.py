"""Geometry test: FreeCAD-side construction failure wrapping (T029).

Covers FR-015 + Edge Cases — when FreeCAD raises during construction,
the error is wrapped in HullConstructionError with parameters + underlying
attributes set.
"""

from __future__ import annotations

import pytest

import storebro.hull as hull_mod
from storebro import HullConstructionError, build_hull


def test_freecad_failure_wrapped_in_construction_error(
    freecad_doc: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    _ = freecad_doc

    def broken_compute_stations(_p: object, _variant: str = "standard") -> list[object]:
        raise RuntimeError("forced failure for test (simulated FreeCAD error)")

    monkeypatch.setattr(hull_mod, "_compute_stations", broken_compute_stations)

    with pytest.raises(HullConstructionError) as exc_info:
        build_hull()
    assert exc_info.value.parameters is not None
    assert exc_info.value.underlying is not None
    assert isinstance(exc_info.value.underlying, RuntimeError)
    assert "forced failure" in str(exc_info.value.underlying)
