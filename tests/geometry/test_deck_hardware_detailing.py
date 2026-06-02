"""Geometry tests: spec 022 deck-hardware detailing.

Covers the refined rubrail (chrome insert), bow pulpit (radiused bends + weld
beads), lifeline catenary, contoured cleats, and the recessed anchor-locker
cavity + lid. Asserts manifold validity (FR-009), the NOBOOL invariant (FR-007),
fallbacks (FR-008), and the new render bodies.
"""

from __future__ import annotations

from pathlib import Path

import FreeCAD  # type: ignore[import-not-found]
import pytest

from storebro import build_deck, build_hull, export_stl
from storebro.deck import (
    AnchorLockerParameters,
    BowPulpitParameters,
    CleatParameters,
    DeckHardwareParameters,
    LifelineParameters,
    RubrailParameters,
)


def _all_solids_valid_closed(shape: object) -> bool:
    return (
        not shape.isNull()  # type: ignore[attr-defined]
        and shape.isValid()  # type: ignore[attr-defined]
        and len(shape.Solids) >= 1  # type: ignore[attr-defined]
        and all(s.isClosed() for s in shape.Solids)  # type: ignore[attr-defined]
    )


# --- US1: moulded rubrail + chrome insert (T020) ---------------------------


@pytest.mark.requires_freecad
def test_rubrail_chrome_insert_present_and_valid(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    rb = deck.rubrail
    assert rb.has_chrome_insert is True
    assert rb.insert_body is not None
    # Teak sides (2) + chrome insert (2) bodies all valid closed solids.
    assert _all_solids_valid_closed(rb.body.Shape)
    assert _all_solids_valid_closed(rb.insert_body.Shape)
    labels = [o.Label for o in deck.document.Objects]
    assert any(label.startswith("Deck_RubrailChromeInsert") for label in labels)


@pytest.mark.requires_freecad
def test_rubrail_chrome_insert_omitted_when_disabled(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    hw = DeckHardwareParameters(rubrail=RubrailParameters(chrome_insert=False))
    deck = build_deck(hull, parameters_hardware=hw)
    assert deck.rubrail.has_chrome_insert is False
    assert deck.rubrail.insert_body is None
    labels = [o.Label for o in deck.document.Objects]
    assert not any(label.startswith("Deck_RubrailChromeInsert") for label in labels)


# --- US2: bent bow pulpit + weld beads (T021) ------------------------------


@pytest.mark.requires_freecad
def test_bow_pulpit_radiused_and_valid(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    bp = deck.bow_pulpit
    assert bp.has_radiused_bends is True
    assert bp.has_weld_beads is True
    assert _all_solids_valid_closed(bp.body.Shape)


@pytest.mark.requires_freecad
def test_bow_pulpit_zero_stanchions_empty(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    hw = DeckHardwareParameters(bow_pulpit=BowPulpitParameters(stanchion_count=0))
    deck = build_deck(hull, parameters_hardware=hw)
    # FR-016: empty footprint; no bends/beads claimed.
    assert deck.bow_pulpit.has_radiused_bends is False
    assert deck.bow_pulpit.has_weld_beads is False


# --- US3: lifeline catenary (T022) -----------------------------------------


@pytest.mark.requires_freecad
def test_lifeline_catenary_sags(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    hw = DeckHardwareParameters(lifelines=LifelineParameters(sag_depth=60.0))
    deck = build_deck(hull, parameters_hardware=hw)
    line_bodies = [
        o
        for o in deck.document.Objects
        if o.Label.startswith("Deck_Lifeline_") and hasattr(o, "Shape")
    ]
    assert line_bodies, "expected lifeline bodies on default railing"
    for body in line_bodies:
        bb = body.Shape.BoundBox
        # The tube spans X; its mid-span Z dips below the end Z by ~sag.
        # Sampling the shape's Z extent: the lowest point sits ~sag below the top.
        assert _all_solids_valid_closed(body.Shape)
        assert (bb.ZMax - bb.ZMin) >= 40.0, "catenary should add vertical extent (sag)"


@pytest.mark.requires_freecad
def test_lifeline_straight_when_zero_sag(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    hw = DeckHardwareParameters(lifelines=LifelineParameters(sag_depth=0.0))
    deck = build_deck(hull, parameters_hardware=hw)
    line_bodies = [
        o
        for o in deck.document.Objects
        if o.Label.startswith("Deck_Lifeline_") and hasattr(o, "Shape")
    ]
    assert line_bodies
    for body in line_bodies:
        bb = body.Shape.BoundBox
        # A straight tube has only the tube-diameter vertical extent (~12 mm).
        assert (bb.ZMax - bb.ZMin) < 30.0
        assert _all_solids_valid_closed(body.Shape)


# --- US4: contoured cleats (T023) ------------------------------------------


@pytest.mark.requires_freecad
def test_cleats_contoured_single_solids(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    cleat_bodies = [
        o for o in deck.document.Objects if o.Label.startswith("Deck_Cleat_")
    ]
    assert cleat_bodies
    for body in cleat_bodies:
        shape = body.Shape
        assert len(shape.Solids) == 1, "each cleat is a single fused casting"
        assert shape.isValid()


@pytest.mark.requires_freecad
def test_cleat_count_matches_spec010(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    cp = CleatParameters()
    assert deck.cleats.count == cp.count_per_station * cp.station_count * 2


# --- US5: recessed anchor-locker cavity + lid (T024) -----------------------


@pytest.mark.requires_freecad
def test_anchor_locker_cavity_and_lid(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    al = deck.anchor_locker
    assert al.has_cavity is True
    assert al.lid_body is not None
    assert len(al.body.Shape.Solids) == 1
    assert al.body.Shape.isValid()
    assert _all_solids_valid_closed(al.lid_body.Shape)
    labels = [o.Label for o in deck.document.Objects]
    assert any(label.startswith("Deck_AnchorLockerLid") for label in labels)


@pytest.mark.requires_freecad
def test_anchor_locker_solid_box_when_no_cavity(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    hw = DeckHardwareParameters(anchor_locker=AnchorLockerParameters(cavity_depth=0.0))
    deck = build_deck(hull, parameters_hardware=hw)
    assert deck.anchor_locker.has_cavity is False
    assert deck.anchor_locker.lid_body is None
    assert len(deck.anchor_locker.body.Shape.Solids) == 1
    labels = [o.Label for o in deck.document.Objects]
    assert not any(label.startswith("Deck_AnchorLockerLid") for label in labels)


# --- NOBOOL invariant (T025, FR-007) ---------------------------------------


@pytest.mark.requires_freecad
def test_hull_and_deck_plate_unchanged_by_hardware() -> None:
    doc_with = FreeCAD.newDocument("HwWith")
    doc_without = FreeCAD.newDocument("HwWithout")
    try:
        hull_w = build_hull(document=doc_with)
        deck_w = build_deck(hull_w)
        # No way to disable hardware wholesale, but zeroing every hardware item
        # yields a deck whose hull + deck plate must match the full-hardware build.
        hull_n = build_hull(document=doc_without)
        hw = DeckHardwareParameters(
            rubrail=RubrailParameters(),
            bow_pulpit=BowPulpitParameters(stanchion_count=0),
            lifelines=LifelineParameters(line_count=0),
            anchor_locker=AnchorLockerParameters(cavity_depth=0.0),
            cleats=CleatParameters(count_per_station=0, station_count=0),
        )
        deck_n = build_deck(hull_n, parameters_hardware=hw)

        assert abs(hull_w.body.Shape.Volume - hull_n.body.Shape.Volume) < 1.0
        assert len(hull_w.body.Shape.Vertexes) == len(hull_n.body.Shape.Vertexes)
        assert abs(
            deck_w.deck_plate.body.Shape.Volume - deck_n.deck_plate.body.Shape.Volume
        ) < 1.0
    finally:
        FreeCAD.closeDocument(doc_with.Name)
        FreeCAD.closeDocument(doc_without.Name)


# --- STL watertightness (T026, SC-003) -------------------------------------


@pytest.mark.requires_freecad
def test_hardware_bodies_export_watertight_stl(freecad_doc: object, tmp_path: Path) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    for name in ("rubrail", "bow_pulpit", "lifelines", "anchor_locker", "cleats"):
        body = getattr(deck, name).body
        out = tmp_path / f"{name}.stl"
        artifact = export_stl(body, str(out))
        assert out.is_file()
        assert artifact.byte_count > 0
        assert _all_solids_valid_closed(body.Shape)
    # The new bodies too.
    for extra in (deck.rubrail.insert_body, deck.anchor_locker.lid_body):
        assert extra is not None
        assert _all_solids_valid_closed(extra.Shape)
