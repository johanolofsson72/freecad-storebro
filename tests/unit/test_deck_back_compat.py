"""Unit tests for spec 008 back-compat shim: DeckParameters.to_superstructure_parameters() (FR-024, R4)."""

from __future__ import annotations

import pytest

from storebro.deck import (
    DeckParameters,
    DeckSuperstructureParameters,
)


def test_legacy_defaults_produce_valid_composite() -> None:
    legacy = DeckParameters()
    sp = legacy.to_superstructure_parameters()
    assert isinstance(sp, DeckSuperstructureParameters)
    # All sub-components present.
    assert sp.cabin_trunk is not None
    assert sp.windshield is not None
    assert sp.hardtop is not None
    assert sp.pillars is not None
    assert sp.railings is not None


def test_meter_to_mm_conversion_for_cabin_trunk() -> None:
    """Legacy cabin_trunk_length (spec 033: 5.2 m) maps to CabinTrunkParameters.length in mm."""
    legacy = DeckParameters()  # cabin_trunk_length=5.20
    sp = legacy.to_superstructure_parameters()
    assert sp.cabin_trunk.length == pytest.approx(5200.0)


def test_meter_to_mm_conversion_for_railing_height() -> None:
    legacy = DeckParameters(railing_height=0.80)
    sp = legacy.to_superstructure_parameters()
    assert sp.railings.height_above_deck == pytest.approx(800.0)


def test_legacy_rectangular_cabin_becomes_equal_widths() -> None:
    """Legacy cabin_trunk_width is a single value — shim sets forward_width == aft_width."""
    legacy = DeckParameters(cabin_trunk_width=2.40)
    sp = legacy.to_superstructure_parameters()
    assert sp.cabin_trunk.forward_width == sp.cabin_trunk.aft_width
    assert sp.cabin_trunk.forward_width == pytest.approx(2400.0)


def test_legacy_windshield_rake_duplicates_to_base_and_top() -> None:
    legacy = DeckParameters(windshield_rake=20.0)
    sp = legacy.to_superstructure_parameters()
    assert sp.windshield.rake_angle_base == 20.0
    assert sp.windshield.rake_angle_top == 20.0


def test_legacy_hardtop_pillar_diameter_maps_to_pillar_diameter() -> None:
    legacy = DeckParameters(hardtop_pillar_diameter=0.045)
    sp = legacy.to_superstructure_parameters()
    assert sp.pillars.diameter == pytest.approx(45.0)


def test_legacy_deck_side_walkway_maps_to_inboard_offsets() -> None:
    legacy = DeckParameters(deck_side_walkway=0.50)
    sp = legacy.to_superstructure_parameters()
    assert sp.pillars.inboard_offset_from_sheer == pytest.approx(500.0)
    assert sp.railings.inboard_offset_from_sheer == pytest.approx(500.0)
    # And the cabin trunk wall inset.
    assert sp.cabin_trunk.wall_inset == pytest.approx(500.0)


def test_shim_is_deterministic() -> None:
    """Same input → same output. No I/O, no time."""
    legacy = DeckParameters()
    sp1 = legacy.to_superstructure_parameters()
    sp2 = legacy.to_superstructure_parameters()
    assert sp1 == sp2


def test_shim_output_passes_validation() -> None:
    """Shim must not produce invalid composites."""
    legacy = DeckParameters()
    sp = legacy.to_superstructure_parameters()
    # Cross-component invariants hold.
    assert sp.railings.height_above_deck < sp.hardtop.height_above_deck


def test_shim_silently_drops_unmappable_fields() -> None:
    """cabin_trunk_corner_radius has no analogue in the new dataclasses; shim drops it silently."""
    legacy = DeckParameters(cabin_trunk_corner_radius=0.20)
    sp = legacy.to_superstructure_parameters()
    # No exception. The new dataclasses don't store corner radius.
    assert sp.cabin_trunk.length > 0


def test_legacy_deck_parameters_remains_frozen_and_compatible() -> None:
    """v1.0.1 callers using DeckParameters fields directly continue to work."""
    p = DeckParameters()
    # All 14 legacy fields are accessible with their v1.0.1 names.
    assert p.deck_plate_thickness == 0.025
    assert p.cabin_trunk_length == 5.20  # spec 033
    assert p.cabin_trunk_fwd_offset == 1.60  # spec 033
    assert p.cabin_trunk_width == 2.20
    assert p.cabin_trunk_height == 1.45  # spec 033
    assert p.cabin_trunk_corner_radius == 0.075
    assert p.windshield_rake == 25.0
    assert p.hardtop_length == 3.50
    assert p.hardtop_height == 0.10
    assert p.hardtop_overhang_fwd == 0.20
    assert p.hardtop_overhang_aft == 0.40
    assert p.hardtop_pillar_diameter == 0.04
    assert p.railing_height == 0.65
    assert p.deck_side_walkway == 0.40
