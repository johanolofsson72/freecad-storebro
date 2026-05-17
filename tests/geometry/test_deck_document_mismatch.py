"""Geometry test: cross-document deck building is rejected (T026).

Covers FR-016.
"""

from __future__ import annotations

import FreeCAD  # type: ignore[import-not-found]
import pytest

from storebro import DeckParameterError, build_deck, build_hull


def test_cross_document_rejected(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    other = FreeCAD.newDocument("AlternativeDoc")
    try:
        with pytest.raises(DeckParameterError) as exc_info:
            build_deck(hull, document=other)
        assert exc_info.value.parameter_name == "document"
    finally:
        FreeCAD.closeDocument(other.Name)


def test_same_document_accepted(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull, document=freecad_doc)
    assert deck.document is freecad_doc
