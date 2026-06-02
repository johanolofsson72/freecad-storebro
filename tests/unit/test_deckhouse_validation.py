"""Unit tests for spec 016 DS-variant deckhouse validation (no FreeCAD).

Covers DeckhouseParameters + DsWindowParameters invariants, the cross-hull
deckhouse fit helper, and the build_deck variant-selector guards (which run
before any FreeCAD call, so they are exercisable on a host without FreeCAD).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from storebro import DeckhouseParameters, DeckParameterError, DsWindowParameters
from storebro.deck import _validate_cross_hull_deckhouse, build_deck

# --------------------------------------------------------------------------
# DsWindowParameters
# --------------------------------------------------------------------------


def test_dswindow_defaults() -> None:
    w = DsWindowParameters()
    assert (w.count_per_side, w.length, w.height, w.recess_depth) == (3, 1000.0, 500.0, 15.0)


def test_dswindow_negative_count_rejected() -> None:
    with pytest.raises(DeckParameterError) as exc:
        DsWindowParameters(count_per_side=-1)
    assert exc.value.parameter_name == "ds_window_count_per_side"


@pytest.mark.parametrize(
    "kwargs,field",
    [
        ({"length": 0.0}, "ds_window_length"),
        ({"height": -5.0}, "ds_window_height"),
        ({"recess_depth": 0.0}, "ds_window_recess_depth"),
    ],
)
def test_dswindow_nonpositive_rejected(kwargs: dict[str, float], field: str) -> None:
    with pytest.raises(DeckParameterError) as exc:
        DsWindowParameters(**kwargs)
    assert exc.value.parameter_name == field


# --------------------------------------------------------------------------
# DeckhouseParameters
# --------------------------------------------------------------------------


def test_deckhouse_defaults_match_reference_register() -> None:
    p = DeckhouseParameters()
    ref = DeckhouseParameters.REFERENCE_STOREBRO_DECKHOUSE_DS
    assert p.length == ref["length"]
    assert p.forward_width == ref["forward_width"]
    assert p.aft_width == ref["aft_width"]
    assert p.height_above_deck == ref["height_above_deck"]
    assert p.front_rake_angle == ref["front_rake_angle"]


@pytest.mark.parametrize(
    "kwargs,field",
    [
        ({"length": 0.0}, "deckhouse_length"),
        ({"forward_width": -1.0}, "deckhouse_forward_width"),
        ({"aft_width": 0.0}, "deckhouse_aft_width"),
        ({"height_above_deck": 0.0}, "deckhouse_height_above_deck"),
        ({"roof_thickness": 0.0}, "deckhouse_roof_thickness"),
    ],
)
def test_deckhouse_nonpositive_rejected(kwargs: dict[str, float], field: str) -> None:
    with pytest.raises(DeckParameterError) as exc:
        DeckhouseParameters(**kwargs)
    assert exc.value.parameter_name == field


@pytest.mark.parametrize(
    "kwargs,field",
    [
        ({"wall_inset": -1.0}, "deckhouse_wall_inset"),
        ({"fwd_offset": -1.0}, "deckhouse_fwd_offset"),
    ],
)
def test_deckhouse_negative_rejected(kwargs: dict[str, float], field: str) -> None:
    with pytest.raises(DeckParameterError) as exc:
        DeckhouseParameters(**kwargs)
    assert exc.value.parameter_name == field


def test_deckhouse_tapered_silhouette_invariant() -> None:
    # forward_width must be <= aft_width.
    with pytest.raises(DeckParameterError) as exc:
        DeckhouseParameters(forward_width=2400.0, aft_width=2200.0)
    assert "forward_width" in exc.value.parameter_name


@pytest.mark.parametrize("angle", [-1.0, 61.0])
def test_deckhouse_front_rake_band(angle: float) -> None:
    with pytest.raises(DeckParameterError) as exc:
        DeckhouseParameters(front_rake_angle=angle)
    assert exc.value.parameter_name == "deckhouse_front_rake_angle"


def test_deckhouse_recess_must_be_shallower_than_wall() -> None:
    # recess_depth >= wall_inset would split the solid (spec 009 guard).
    with pytest.raises(DeckParameterError) as exc:
        DeckhouseParameters(wall_inset=15.0, windows=DsWindowParameters(recess_depth=15.0))
    assert "recess_depth" in exc.value.parameter_name


def test_deckhouse_zero_wall_inset_rejects_positive_recess() -> None:
    with pytest.raises(DeckParameterError):
        DeckhouseParameters(wall_inset=0.0)  # default recess 15 >= 0 wall


# --------------------------------------------------------------------------
# _validate_cross_hull_deckhouse (mm params vs meter hull)
# --------------------------------------------------------------------------


def _stub_hull(loa_m: float, beam_max_m: float) -> SimpleNamespace:
    return SimpleNamespace(parameters=SimpleNamespace(loa=loa_m, beam_max=beam_max_m))


def test_cross_hull_default_deckhouse_fits_default_hull() -> None:
    # Default deckhouse (fwd_offset 2200 + length 6200 = 8400 mm) fits LOA 10.36 m.
    _validate_cross_hull_deckhouse(_stub_hull(10.36, 3.30), DeckhouseParameters())


def test_cross_hull_deckhouse_longer_than_loa_rejected() -> None:
    with pytest.raises(DeckParameterError) as exc:
        _validate_cross_hull_deckhouse(
            _stub_hull(8.0, 3.30), DeckhouseParameters(fwd_offset=2200.0, length=6200.0)
        )
    assert "fwd_offset+length" in exc.value.parameter_name


def test_cross_hull_deckhouse_wider_than_beam_rejected() -> None:
    with pytest.raises(DeckParameterError) as exc:
        _validate_cross_hull_deckhouse(
            _stub_hull(10.36, 2.50),
            DeckhouseParameters(aft_width=2200.0, wall_inset=250.0),  # 2200 + 500 = 2700 > 2500
        )
    assert "aft_width+walls" in exc.value.parameter_name


# --------------------------------------------------------------------------
# build_deck variant-selector guards (pre-FreeCAD)
# --------------------------------------------------------------------------


def test_build_deck_rejects_unknown_variant() -> None:
    with pytest.raises(DeckParameterError) as exc:
        build_deck(SimpleNamespace(), superstructure_variant="bogus")  # type: ignore[arg-type]
    assert exc.value.parameter_name == "superstructure_variant"


def test_build_deck_rejects_ds_with_superstructure_params() -> None:
    from storebro import DeckSuperstructureParameters

    with pytest.raises(DeckParameterError) as exc:
        build_deck(
            SimpleNamespace(),
            superstructure_variant="ds",
            parameters_superstructure=DeckSuperstructureParameters(),
        )
    assert exc.value.parameter_name == "superstructure_variant<>parameters_superstructure"
