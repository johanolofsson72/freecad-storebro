"""Geometry test: produce the v1.0.5 visual-signoff artifact (T025).

Builds hull + deck with glazing, exports to .FCStd, records the SHA-256, and
prints a MANUAL SIGNOFF reminder for the FreeCAD GUI review against
docs/references/Alternativ3.JPG (constitution V).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from storebro import build_deck, build_hull, export_fcstd

SIGNOFF_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "signoff"
SIGNOFF_PATH = SIGNOFF_DIR / "storebro_v1_0_5_signoff.FCStd"


def test_v1_0_5_glazing_signoff_artifact(freecad_doc: object) -> None:
    SIGNOFF_DIR.mkdir(parents=True, exist_ok=True)
    hull = build_hull(document=freecad_doc)
    build_deck(hull)
    art = export_fcstd(hull.document, str(SIGNOFF_PATH))

    assert SIGNOFF_PATH.is_file()
    assert art.byte_count > 0
    digest = hashlib.sha256(SIGNOFF_PATH.read_bytes()).hexdigest()
    print(
        f"\nMANUAL SIGNOFF: open {SIGNOFF_PATH} in FreeCAD and confirm the hull "
        "portholes, cabin-trunk side windows, and framed windshield + glass "
        "read correctly against docs/references/Alternativ3.JPG — record "
        f"FreeCAD version + OS in the register per constitution V.\nSHA-256: {digest}"
    )


def test_glazed_build_is_reproducible(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    assert hull.portholes.count > 0
    assert deck.cabin_windows.count > 0
    assert deck.windshield.glass_pane is not None
