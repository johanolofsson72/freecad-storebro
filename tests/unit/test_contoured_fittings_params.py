"""Unit tests for spec 024 contour + fabric fields on the furniture dataclasses."""

from __future__ import annotations

import pytest

from storebro.interior import (
    BerthParameters,
    BulkheadParameters,
    GalleyParameters,
    HeadParameters,
    InteriorParameterError,
    SalonParameters,
)


def test_berth_spec024_defaults() -> None:
    p = BerthParameters()
    assert p.contoured is True
    assert p.cushion_segments == 2
    assert p.seam_gap == 15.0
    assert p.cushion_fillet == 25.0
    assert (p.buttons_per_row, p.button_rows, p.button_radius) == (4, 2, 35.0)
    assert p.piping is True
    assert p.piping_radius == 12.0
    assert p.fold_creases == 2


def test_berth_segments_must_be_positive() -> None:
    with pytest.raises(InteriorParameterError):
        BerthParameters(cushion_segments=0)


@pytest.mark.parametrize("field", ["cushion_fillet", "button_radius", "piping_radius"])
def test_berth_positive_fields(field: str) -> None:
    with pytest.raises(InteriorParameterError):
        BerthParameters(**{field: 0.0})


@pytest.mark.parametrize("field", ["seam_gap", "buttons_per_row", "button_rows", "fold_creases"])
def test_berth_nonneg_fields(field: str) -> None:
    with pytest.raises(InteriorParameterError):
        BerthParameters(**{field: -1})


def test_salon_spec024_defaults() -> None:
    p = SalonParameters()
    assert p.contoured is True
    assert p.seat_fillet == 25.0
    assert p.piping is True


@pytest.mark.parametrize("field", ["seat_fillet", "button_radius", "piping_radius"])
def test_salon_positive_fields(field: str) -> None:
    with pytest.raises(InteriorParameterError):
        SalonParameters(**{field: 0.0})


def test_head_spec024_defaults() -> None:
    p = HeadParameters()
    assert p.contoured is True
    assert p.toilet_fillet == 30.0
    assert p.bowl_radius == 170.0
    assert p.faucet is True
    assert p.faucet_height == 200.0


@pytest.mark.parametrize("field", ["toilet_fillet", "bowl_radius", "faucet_height"])
def test_head_positive_fields(field: str) -> None:
    with pytest.raises(InteriorParameterError):
        HeadParameters(**{field: 0.0})


def test_galley_spec024_defaults() -> None:
    p = GalleyParameters()
    assert p.contoured is True
    assert p.edge_fillet == 12.0
    assert p.fascia is True
    assert p.fascia_thickness == 18.0


@pytest.mark.parametrize("field", ["edge_fillet", "fascia_thickness"])
def test_galley_positive_fields(field: str) -> None:
    with pytest.raises(InteriorParameterError):
        GalleyParameters(**{field: 0.0})


def test_bulkhead_spec024_defaults() -> None:
    p = BulkheadParameters()
    assert p.contoured is True
    assert p.corner_fillet == 40.0
    assert p.doorway is True
    assert (p.doorway_width, p.doorway_height) == (600.0, 1500.0)


@pytest.mark.parametrize("field", ["corner_fillet", "doorway_width", "doorway_height"])
def test_bulkhead_positive_fields(field: str) -> None:
    with pytest.raises(InteriorParameterError):
        BulkheadParameters(**{field: 0.0})


def test_contoured_can_be_disabled() -> None:
    # contoured=False is the spec 012/013 back-compat path (FR-008).
    assert BerthParameters(contoured=False).contoured is False
    assert SalonParameters(contoured=False).contoured is False
    assert HeadParameters(contoured=False).contoured is False
    assert GalleyParameters(contoured=False).contoured is False
    assert BulkheadParameters(contoured=False).contoured is False
