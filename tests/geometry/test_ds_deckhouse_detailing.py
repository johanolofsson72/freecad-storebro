"""Geometry tests: spec 023 DS deckhouse detailing + DS interior.

Front-window recess (rotated datum), side-window mullions, helm-door recess —
all keeping the deckhouse a single valid solid (FR-005), never touching the hull
or deck plate (FR-006). Plus the full DS enclosed-saloon interior (FR-004).
"""

from __future__ import annotations

from pathlib import Path

import FreeCAD  # type: ignore[import-not-found]
import pytest

from storebro import build_deck, build_hull, export_stl
from storebro.deck import DeckhouseParameters, DsWindowParameters
from storebro.interior import build_interior


def _ds(doc: object, win: DsWindowParameters | None = None) -> object:
    hull = build_hull(document=doc)
    dh = DeckhouseParameters(windows=win) if win is not None else None
    return build_deck(hull, superstructure_variant="ds", parameters_deckhouse=dh)


# --- US1: front-window recess (T015, T016) ---------------------------------


@pytest.mark.requires_freecad
def test_front_window_recess_and_glass(freecad_doc: object) -> None:
    deck = _ds(freecad_doc)
    dh = deck.deckhouse
    assert dh.has_front_window is True
    assert dh.front_window_skipped is False
    assert len(dh.body.Shape.Solids) == 1
    assert dh.body.Shape.isValid()
    labels = [o.Label for o in deck.document.Objects]
    assert any(label.startswith("Deck_DeckhouseWindowGlassFront") for label in labels)


@pytest.mark.requires_freecad
def test_front_window_disabled(freecad_doc: object) -> None:
    deck = _ds(freecad_doc, DsWindowParameters(front_window=False))
    dh = deck.deckhouse
    assert dh.has_front_window is False
    assert dh.front_window_skipped is False
    assert len(dh.body.Shape.Solids) == 1
    labels = [o.Label for o in deck.document.Objects]
    assert not any(label.startswith("Deck_DeckhouseWindowGlassFront") for label in labels)


# --- US2: mullions (T017) --------------------------------------------------


@pytest.mark.requires_freecad
def test_mullions_present(freecad_doc: object) -> None:
    deck = _ds(freecad_doc)
    dh = deck.deckhouse
    assert dh.mullion_count > 0
    assert len(dh.body.Shape.Solids) == 1
    mbodies = [o for o in deck.document.Objects if o.Label.startswith("Deck_DeckhouseMullion")]
    assert mbodies
    # spec 033 regression guard: mullions sit ON the deckhouse walls, inside its
    # X/Z envelope — not doubled off the hull (the sketch-coord bug that placed
    # them at 2*x, floating above and aft of the boat).
    hb = deck.deckhouse.body.Shape.BoundBox
    for m in mbodies:
        assert len(m.Shape.Solids) == 1 and m.Shape.isValid()
        mb = m.Shape.BoundBox
        assert hb.XMin - 100.0 <= mb.XMin and mb.XMax <= hb.XMax + 100.0, (
            f"mullion {m.Label} X[{mb.XMin:.0f},{mb.XMax:.0f}] outside deckhouse "
            f"X[{hb.XMin:.0f},{hb.XMax:.0f}]"
        )
        assert hb.ZMin - 100.0 <= mb.ZMin and mb.ZMax <= hb.ZMax + 100.0, (
            f"mullion {m.Label} Z[{mb.ZMin:.0f},{mb.ZMax:.0f}] outside deckhouse "
            f"Z[{hb.ZMin:.0f},{hb.ZMax:.0f}]"
        )


@pytest.mark.requires_freecad
def test_mullions_disabled(freecad_doc: object) -> None:
    deck = _ds(freecad_doc, DsWindowParameters(mullions_per_window=0))
    assert deck.deckhouse.mullion_count == 0
    mbodies = [o for o in deck.document.Objects if o.Label.startswith("Deck_DeckhouseMullion")]
    assert not mbodies


# --- US3: helm door (T018) -------------------------------------------------


@pytest.mark.requires_freecad
def test_helm_door_present(freecad_doc: object) -> None:
    deck = _ds(freecad_doc)
    dh = deck.deckhouse
    assert dh.has_helm_door is True
    assert len(dh.body.Shape.Solids) == 1
    assert dh.body.Shape.isValid()


@pytest.mark.requires_freecad
def test_helm_door_disabled(freecad_doc: object) -> None:
    deck = _ds(freecad_doc, DsWindowParameters(helm_door=False))
    assert deck.deckhouse.has_helm_door is False
    assert len(deck.deckhouse.body.Shape.Solids) == 1


# --- NOBOOL (T019, FR-006) -------------------------------------------------


@pytest.mark.requires_freecad
def test_hull_deck_plate_unchanged_by_detailing() -> None:
    doc_full = FreeCAD.newDocument("DsFull")
    doc_bare = FreeCAD.newDocument("DsBare")
    try:
        h1 = build_hull(document=doc_full)
        d1 = build_deck(h1, superstructure_variant="ds")
        # Disable every detailing feature → hull + deck plate must match.
        bare_win = DsWindowParameters(
            front_window=False, mullions_per_window=0, helm_door=False
        )
        h2 = build_hull(document=doc_bare)
        d2 = build_deck(
            h2,
            superstructure_variant="ds",
            parameters_deckhouse=DeckhouseParameters(windows=bare_win),
        )
        assert abs(h1.body.Shape.Volume - h2.body.Shape.Volume) < 1.0
        assert len(h1.body.Shape.Vertexes) == len(h2.body.Shape.Vertexes)
        assert abs(d1.deck_plate.body.Shape.Volume - d2.deck_plate.body.Shape.Volume) < 1.0
    finally:
        FreeCAD.closeDocument(doc_full.Name)
        FreeCAD.closeDocument(doc_bare.Name)


# --- STL (T020, SC-002) ----------------------------------------------------


@pytest.mark.requires_freecad
def test_ds_deckhouse_stl_watertight(freecad_doc: object, tmp_path: Path) -> None:
    deck = _ds(freecad_doc)
    out = tmp_path / "ds_deckhouse.stl"
    artifact = export_stl(deck.deckhouse.body, str(out))
    assert out.is_file() and artifact.byte_count > 0
    sh = deck.deckhouse.body.Shape
    assert len(sh.Solids) == 1 and sh.isValid()
    assert all(s.isClosed() for s in sh.Solids)


# --- US4: DS interior (T021) -----------------------------------------------


@pytest.mark.requires_freecad
def test_ds_interior_furnished_with_helm(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull, superstructure_variant="ds")
    interior = build_interior(hull, deck, superstructure_variant="ds")
    assert interior.layout.layout_name == "DsSaloon"
    helm = [c for c in interior.compartments if c.spec.compartment_type == "helm"]
    assert helm, "DS layout has a helm compartment"
    assert helm[0].is_furnished
    # Console + seat + bulkhead pieces, each a valid solid.
    for piece in helm[0].furniture:
        assert piece.Shape.isValid()
    for c in interior.compartments:
        assert c.body.Shape.isValid()


@pytest.mark.requires_freecad
def test_standard_interior_unchanged(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    interior = build_interior(hull, deck)
    assert interior.layout.layout_name == "Alternativ3"
    assert not any(c.spec.compartment_type == "helm" for c in interior.compartments)
