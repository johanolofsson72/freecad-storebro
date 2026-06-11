"""Unit tests (no FreeCAD): spec 029 — non-finite (nan/inf) rejection.

Every parameter dataclass with a float geometry/dimension field must reject
`nan`, `+inf`, and `-inf` at construction, raising its module's ParameterError
(FR-001/FR-002/FR-009, SC-001/SC-003). Finite "auto" sentinels stay accepted
(FR-006). Covers a representative field of every guarded dataclass across
hull / deck / interior / propulsion.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from storebro.deck import (
    AnchorLockerParameters,
    BowPulpitParameters,
    CabinTrunkParameters,
    CabinWindowParameters,
    CleatParameters,
    DeckParameterError,
    DeckParameters,
    DsWindowParameters,
    HardtopParameters,
    LifelineParameters,
    PillarParameters,
    RailingParameters,
    RubrailParameters,
    WindshieldGlazingParameters,
    WindshieldParameters,
)
from storebro.hull import (
    HullGlazingParameters,
    HullParameterError,
    HullParameters,
    PortholeParameters,
)
from storebro.interior import (
    BerthParameters,
    BulkheadParameters,
    Dimensions3D,
    EngineRoomParameters,
    GalleyParameters,
    HeadParameters,
    HelmParameters,
    InteriorParameterError,
    Position3D,
    SalonParameters,
    WetLockerParameters,
)
from storebro.propulsion import (
    EngineBedParameters,
    EngineParameters,
    PropellerParameters,
    PropulsionParameterError,
    PropulsionParameters,
    RudderParameters,
    ShaftParameters,
)

INF = float("inf")
NAN = float("nan")

# (id, constructor taking the bad value, expected error type). One representative
# float field per guarded dataclass.
_CASES: list[tuple[str, Callable[[float], object], type[Exception]]] = [
    # hull.py
    ("hull.loa", lambda v: HullParameters(loa=v), HullParameterError),
    ("hull.beam_max", lambda v: HullParameters(beam_max=v), HullParameterError),
    ("hull.draft", lambda v: HullParameters(draft=v), HullParameterError),
    ("hull.bilge_radius", lambda v: HullParameters(bilge_radius=v), HullParameterError),
    ("porthole.diameter", lambda v: PortholeParameters(diameter=v), HullParameterError),
    ("porthole.forward_x", lambda v: PortholeParameters(forward_x=v), HullParameterError),
    ("hull_glazing.glass_thickness", lambda v: HullGlazingParameters(glass_thickness=v), HullParameterError),
    # deck.py
    ("deck.deck_plate_thickness", lambda v: DeckParameters(deck_plate_thickness=v), DeckParameterError),
    ("cabin_trunk.length", lambda v: CabinTrunkParameters(length=v), DeckParameterError),
    ("windshield.top_z", lambda v: WindshieldParameters(top_z=v), DeckParameterError),
    ("hardtop.length", lambda v: HardtopParameters(length=v), DeckParameterError),
    ("pillar.diameter", lambda v: PillarParameters(diameter=v), DeckParameterError),
    ("railing.post_diameter", lambda v: RailingParameters(post_diameter=v), DeckParameterError),
    ("rubrail.height", lambda v: RubrailParameters(height=v), DeckParameterError),
    ("bow_pulpit.tube_diameter", lambda v: BowPulpitParameters(tube_diameter=v), DeckParameterError),
    ("lifeline.tube_diameter", lambda v: LifelineParameters(tube_diameter=v), DeckParameterError),
    ("anchor_locker.length", lambda v: AnchorLockerParameters(length=v), DeckParameterError),
    ("cleat.length", lambda v: CleatParameters(length=v), DeckParameterError),
    ("cabin_window.length", lambda v: CabinWindowParameters(length=v), DeckParameterError),
    ("windshield_glazing.glass_thickness", lambda v: WindshieldGlazingParameters(glass_thickness=v), DeckParameterError),
    ("ds_window.glass_thickness", lambda v: DsWindowParameters(glass_thickness=v), DeckParameterError),
    # interior.py
    ("position3d.x", lambda v: Position3D(x=v, y=0.0, z=0.0), InteriorParameterError),
    ("position3d.y", lambda v: Position3D(x=0.0, y=v, z=0.0), InteriorParameterError),
    ("dimensions3d.length", lambda v: Dimensions3D(length=v, width=2.0, height=1.0), InteriorParameterError),
    ("berth.base_height", lambda v: BerthParameters(base_height=v), InteriorParameterError),
    ("galley.counter_height", lambda v: GalleyParameters(counter_height=v), InteriorParameterError),
    ("head.toilet_height", lambda v: HeadParameters(toilet_height=v), InteriorParameterError),
    ("salon.seat_height", lambda v: SalonParameters(seat_height=v), InteriorParameterError),
    ("helm.console_height", lambda v: HelmParameters(console_height=v), InteriorParameterError),
    ("bulkhead.thickness", lambda v: BulkheadParameters(thickness=v), InteriorParameterError),
    ("engine_room.block_height", lambda v: EngineRoomParameters(block_height=v), InteriorParameterError),
    ("wet_locker.locker_height", lambda v: WetLockerParameters(locker_height=v), InteriorParameterError),
    # propulsion.py
    ("engine_bed.length_mm", lambda v: EngineBedParameters(length_mm=v), PropulsionParameterError),
    ("engine.length_mm", lambda v: EngineParameters(length_mm=v), PropulsionParameterError),
    ("shaft.diameter_mm", lambda v: ShaftParameters(diameter_mm=v), PropulsionParameterError),
    ("shaft.fairing_diameter_ratio", lambda v: ShaftParameters(shaft_log_fairing_diameter_ratio=v), PropulsionParameterError),
    ("propeller.diameter_mm", lambda v: PropellerParameters(diameter_mm=v), PropulsionParameterError),
    ("propeller.root_pitch_deg", lambda v: PropellerParameters(root_pitch_deg=v), PropulsionParameterError),
    ("rudder.chord_mm", lambda v: RudderParameters(chord_mm=v), PropulsionParameterError),
    ("propulsion.engine_offset_y_mm", lambda v: PropulsionParameters(engine_offset_y_mm=v), PropulsionParameterError),
]


@pytest.mark.parametrize("bad", [NAN, INF, -INF], ids=["nan", "inf", "-inf"])
@pytest.mark.parametrize(("label", "ctor", "err"), _CASES, ids=[c[0] for c in _CASES])
def test_nonfinite_rejected(
    label: str, ctor: Callable[[float], object], err: type[Exception], bad: float
) -> None:
    with pytest.raises(err):
        ctor(bad)


def test_every_module_guarded() -> None:
    # Guard against silently dropping a module from coverage.
    errs = {c[2] for c in _CASES}
    assert errs == {HullParameterError, DeckParameterError, InteriorParameterError, PropulsionParameterError}


def test_finite_sentinel_still_accepted() -> None:
    # FR-006: the finite 0.0 "derive span" sentinel on portholes must remain valid.
    assert PortholeParameters(forward_x=0.0, aft_x=0.0).forward_x == 0.0


def test_valid_params_still_construct() -> None:
    # FR-003: valid (finite) inputs are unaffected.
    assert HullParameters().loa > 0
    assert DeckParameters().deck_plate_thickness > 0
    assert Position3D(x=0.5, y=0.0, z=0.6).z == 0.6
    assert PropellerParameters().diameter_mm > 0
