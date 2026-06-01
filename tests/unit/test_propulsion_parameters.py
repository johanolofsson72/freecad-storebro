"""Unit tests for spec 014 PropulsionParameters composite (FR-006, T013).

Covers the cross-invariants, default_factory independence, and the
rudder_count=None -> engine_count resolution.
"""

from __future__ import annotations

import pytest

from storebro.propulsion import (
    EngineParameters,
    PropulsionParameterError,
    PropulsionParameters,
    ShaftParameters,
    _resolve_rudder_count,
)


def test_defaults_are_twin_screw() -> None:
    p = PropulsionParameters()
    assert p.engine_count == 2
    assert p.engine_offset_y_mm == 400.0
    assert p.rudder_count is None  # resolves to engine_count at build time


def test_default_factory_independence() -> None:
    a = PropulsionParameters()
    b = PropulsionParameters()
    assert a.engine_bed is not b.engine_bed
    assert a.shaft is not b.shaft


@pytest.mark.parametrize("value", [0, 3, -1])
def test_engine_count_out_of_range_raises(value: int) -> None:
    with pytest.raises(PropulsionParameterError) as exc:
        PropulsionParameters(engine_count=value, engine_offset_y_mm=0.0)
    assert exc.value.parameter_name == "engine_count"


def test_single_screw_with_offset_raises() -> None:
    with pytest.raises(PropulsionParameterError) as exc:
        PropulsionParameters(engine_count=1, engine_offset_y_mm=400.0)
    assert exc.value.parameter_name == "engine_offset_y_mm"


def test_twin_screw_without_offset_raises() -> None:
    with pytest.raises(PropulsionParameterError) as exc:
        PropulsionParameters(engine_count=2, engine_offset_y_mm=0.0)
    assert exc.value.parameter_name == "engine_offset_y_mm"


def test_explicit_rudder_count_out_of_range_raises() -> None:
    with pytest.raises(PropulsionParameterError) as exc:
        PropulsionParameters(rudder_count=3)
    assert exc.value.parameter_name == "rudder_count"


def test_shaft_exit_not_aft_of_engine_raises() -> None:
    with pytest.raises(PropulsionParameterError) as exc:
        PropulsionParameters(
            engine=EngineParameters(station_x_mm=1000.0),
            shaft=ShaftParameters(exit_x_mm=1500.0),
        )
    assert exc.value.parameter_name == "shaft.exit_x_mm"


def test_single_screw_centred_is_valid() -> None:
    p = PropulsionParameters(engine_count=1, engine_offset_y_mm=0.0)
    assert p.engine_count == 1


@pytest.mark.parametrize("engine_count", [1, 2])
def test_rudder_count_resolves_to_engine_count(engine_count: int) -> None:
    offset = 0.0 if engine_count == 1 else 400.0
    base = PropulsionParameters(engine_count=engine_count, engine_offset_y_mm=offset)
    resolved = _resolve_rudder_count(base)
    assert resolved.rudder_count == engine_count


def test_explicit_rudder_count_preserved() -> None:
    base = PropulsionParameters(engine_count=2, engine_offset_y_mm=400.0, rudder_count=1)
    resolved = _resolve_rudder_count(base)
    assert resolved.rudder_count == 1
