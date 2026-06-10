"""Unit test (no FreeCAD): spec 021 detail parameter defaults + validation (T007).

Covers FR-011 (validation before any FreeCAD call) + FR-009 (per-part flags).
"""

from __future__ import annotations

import math

import pytest

from storebro.propulsion import (
    EngineParameters,
    PropellerParameters,
    PropulsionParameterError,
    RudderParameters,
    ShaftParameters,
)


def test_detail_defaults_on() -> None:
    assert EngineParameters().detailed is True
    assert ShaftParameters().coupling_flange is True
    assert ShaftParameters().strut_bearing is True
    assert ShaftParameters().shaft_log_fairing is True
    assert PropellerParameters().airfoil_blades is True
    assert RudderParameters().naca_foil is True


def test_detail_off_is_accepted() -> None:
    EngineParameters(detailed=False)
    ShaftParameters(coupling_flange=False, strut_bearing=False, shaft_log_fairing=False)
    PropellerParameters(airfoil_blades=False)
    RudderParameters(naca_foil=False)


@pytest.mark.parametrize("ratio", [0.0, 1.0, 1.5, -0.1, math.inf, math.nan])
def test_propeller_thickness_ratio_rejected(ratio: float) -> None:
    with pytest.raises(PropulsionParameterError):
        PropellerParameters(naca_thickness_ratio=ratio)


def test_propeller_requires_twist() -> None:
    with pytest.raises(PropulsionParameterError):
        PropellerParameters(root_pitch_deg=30.0, tip_pitch_deg=30.0)
    # off → equal pitches allowed (unused)
    PropellerParameters(airfoil_blades=False, root_pitch_deg=30.0, tip_pitch_deg=30.0)


def test_propeller_min_sections() -> None:
    with pytest.raises(PropulsionParameterError):
        PropellerParameters(blade_sections=1)


@pytest.mark.parametrize("ratio", [0.0, 1.2, -0.2, math.nan])
def test_rudder_thickness_ratio_rejected(ratio: float) -> None:
    with pytest.raises(PropulsionParameterError):
        RudderParameters(naca_thickness_ratio=ratio)


def test_coupling_flange_must_exceed_shaft_diameter() -> None:
    with pytest.raises(PropulsionParameterError):
        ShaftParameters(diameter_mm=45.0, coupling_flange_diameter_mm=40.0)


def test_coupling_thickness_and_bolts() -> None:
    with pytest.raises(PropulsionParameterError):
        ShaftParameters(coupling_flange_thickness_mm=0.0)
    with pytest.raises(PropulsionParameterError):
        ShaftParameters(coupling_bolt_count=-1)
    # bolt count 0 is valid (a plain collar)
    ShaftParameters(coupling_bolt_count=0)


def test_strut_validation() -> None:
    with pytest.raises(PropulsionParameterError):
        ShaftParameters(strut_count=0)
    with pytest.raises(PropulsionParameterError):
        ShaftParameters(strut_arm_width_mm=-5.0)


def test_fairing_ratio_must_exceed_one() -> None:
    with pytest.raises(PropulsionParameterError):
        ShaftParameters(shaft_log_fairing_diameter_ratio=1.0)
    with pytest.raises(PropulsionParameterError):
        ShaftParameters(shaft_log_fairing_length_mm=0.0)


def test_engine_sump_must_stay_inside_block() -> None:
    with pytest.raises(PropulsionParameterError):
        EngineParameters(width_mm=200.0, sump_inset_mm=120.0)  # 2*120 >= 200


def test_engine_manifold_stub_count_non_negative() -> None:
    with pytest.raises(PropulsionParameterError):
        EngineParameters(manifold_stub_count=-1)
    EngineParameters(manifold_stub_count=0)  # zero stubs is valid
