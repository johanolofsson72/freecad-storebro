"""Geometry test: produce visual-signoff artifact (T029).

Builds hull + deck, exports to .FCStd via spec 002's writer, prints a
MANUAL SIGNOFF reminder for the FreeCAD GUI review (constitution V).
"""

from __future__ import annotations

from pathlib import Path

from storebro import build_deck, build_hull, export_fcstd

SIGNOFF_PATH = Path("/tmp/storebro_deck_signoff_003.FCStd")


def test_default_deck_signoff_artifact(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    build_deck(hull)
    art = export_fcstd(hull.document, str(SIGNOFF_PATH))

    print(
        f"\nMANUAL SIGNOFF: open {SIGNOFF_PATH} in FreeCAD and confirm hull + "
        "6 deck Bodies match docs/references/ — record FreeCAD version + OS "
        "in PR description per constitution V"
    )
    assert SIGNOFF_PATH.is_file()
    assert art.byte_count > 0
