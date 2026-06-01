"""Destructive validation tests for spec 014 propulsion (T035).

Library-equivalent of the 6 destructive attack categories applied to the
public parameter API (no FreeCAD needed):

1. Invalid input — garbage / negative / zero dimensions
2. Boundary values — angle 0/30, blade 2/6, engine_count 0/3
3. Wrong order — shaft exit not aft of engine
4. Skip/None inputs — rudder_count None resolves; deck optional path
5. Timing/race — N/A for a pure builder (documented)
6. Extreme magnitudes — non-finite, huge offsets

Note: non-finite hardening is enforced via _require_positive/_require_non_negative
here; this is stricter than the deck modules, whose non-finite hardening remains a
documented module-wide deferral.
"""

from __future__ import annotations

import pytest

from storebro.propulsion import (
    EngineParameters,
    PropellerParameters,
    PropulsionParameterError,
    PropulsionParameters,
    ShaftParameters,
)


# 1 + 6: garbage / non-finite dimensions
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1.0, 0.0])
def test_engine_dimension_rejects_garbage(value: float) -> None:
    with pytest.raises(PropulsionParameterError):
        EngineParameters(length_mm=value)


# 2: boundary — engine_count
@pytest.mark.parametrize("value", [0, 3])
def test_engine_count_boundary_rejected(value: int) -> None:
    with pytest.raises(PropulsionParameterError):
        PropulsionParameters(engine_count=value, engine_offset_y_mm=0.0)


# 2: boundary — shaft angle just outside [0, 30]
@pytest.mark.parametrize("value", [-0.001, 30.001])
def test_shaft_angle_boundary_rejected(value: float) -> None:
    with pytest.raises(PropulsionParameterError):
        ShaftParameters(angle_deg=value)


# 2: boundary — blade count just outside [2, 6]
@pytest.mark.parametrize("value", [1, 7])
def test_blade_count_boundary_rejected(value: int) -> None:
    with pytest.raises(PropulsionParameterError):
        PropellerParameters(blade_count=value)


# 3: wrong order — shaft exit at/forward of the engine station
@pytest.mark.parametrize("exit_x", [3500.0, 4000.0])
def test_shaft_exit_not_aft_rejected(exit_x: float) -> None:
    with pytest.raises(PropulsionParameterError):
        PropulsionParameters(
            engine=EngineParameters(station_x_mm=3500.0),
            shaft=ShaftParameters(exit_x_mm=exit_x),
        )


# 4: None resolves; explicit valid values accepted
def test_rudder_count_none_accepted_at_construction() -> None:
    p = PropulsionParameters()
    assert p.rudder_count is None


# 6: extreme offset is accepted at dataclass level (build-context guard rejects
#    it against the sampled hull — see geometry tier). Dataclass only requires >= 0.
def test_huge_offset_passes_dataclass_but_is_non_negative() -> None:
    p = PropulsionParameters(engine_count=2, engine_offset_y_mm=1.0e9)
    assert p.engine_offset_y_mm == 1.0e9


def test_negative_offset_rejected() -> None:
    with pytest.raises(PropulsionParameterError):
        PropulsionParameters(engine_count=2, engine_offset_y_mm=-1.0)
