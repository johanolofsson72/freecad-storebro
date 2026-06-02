"""Geometry test: spec 016 DS deckhouse builds as a manifold solid (FR-003..006).

Requires FreeCAD. Covers SC-003 (single manifold solid, STL export succeeds),
SC-004 (principal dims within ±1% of defaults), FR-005 (seated on deck top),
and FR-006 (blind window recesses).
"""

from __future__ import annotations

from storebro import DeckhouseParameters, build_deck, build_hull
from storebro.export import export_stl

REF = DeckhouseParameters.REFERENCE_STOREBRO_DECKHOUSE_DS


def test_ds_deckhouse_is_single_manifold_solid(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull, superstructure_variant="ds")
    assert deck.deckhouse is not None
    shape = deck.deckhouse.body.Shape
    assert len(shape.Solids) == 1, f"deckhouse has {len(shape.Solids)} solids, expected 1"
    assert shape.isValid()


def test_ds_deckhouse_seated_on_deck_top(freecad_doc: object) -> None:
    from storebro.deck import _resolve_deck_top_z_at

    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull, superstructure_variant="ds")
    assert deck.deckhouse is not None
    house_bb = deck.deckhouse.body.Shape.BoundBox
    # FR-005: the deckhouse base sits on the *sampled* deck-plate top at the
    # deckhouse mid-station (the sheer dips below the global bow peak), not on
    # an analytical approximation and not floating above the highest sheer point.
    mid_x = (house_bb.XMin + house_bb.XMax) / 2.0
    expected_top = _resolve_deck_top_z_at(deck.deck_plate, mid_x)
    assert abs(house_bb.ZMin - expected_top) <= 5.0
    deck_bb = deck.deck_plate.body.Shape.BoundBox
    assert deck_bb.ZMin - 5.0 <= house_bb.ZMin <= deck_bb.ZMax + 5.0


def test_ds_deckhouse_principal_dims_within_one_percent(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull, superstructure_variant="ds")
    assert deck.deckhouse is not None
    dh = deck.deckhouse
    assert abs(dh.length - REF["length"] / 1000.0) <= (REF["length"] / 1000.0) * 0.01
    assert abs(dh.height - REF["height_above_deck"] / 1000.0) <= (
        REF["height_above_deck"] / 1000.0
    ) * 0.01
    assert abs(dh.forward_width - REF["forward_width"] / 1000.0) <= (
        REF["forward_width"] / 1000.0
    ) * 0.01
    assert abs(dh.aft_width - REF["aft_width"] / 1000.0) <= (REF["aft_width"] / 1000.0) * 0.01


def test_ds_deckhouse_window_recess_count(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull, superstructure_variant="ds")
    assert deck.deckhouse is not None
    # Default 3 per side, both sides → 6 blind recesses; still one solid.
    assert deck.deckhouse.window_count == 3 * 2
    assert len(deck.deckhouse.body.Shape.Solids) == 1


def test_ds_deckhouse_zero_windows(freecad_doc: object) -> None:
    from storebro import DsWindowParameters

    hull = build_hull(document=freecad_doc)
    deck = build_deck(
        hull,
        superstructure_variant="ds",
        parameters_deckhouse=DeckhouseParameters(windows=DsWindowParameters(count_per_side=0)),
    )
    assert deck.deckhouse is not None
    assert deck.deckhouse.window_count == 0
    assert len(deck.deckhouse.body.Shape.Solids) == 1


def test_ds_deckhouse_stl_export_succeeds(freecad_doc: object, tmp_path: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull, superstructure_variant="ds")
    assert deck.deckhouse is not None
    target = tmp_path / "deckhouse.stl"  # type: ignore[operator]
    artifact = export_stl(deck.deckhouse.body, target)
    assert artifact.byte_count > 0
