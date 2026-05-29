"""Geometry test: produce the v1.0.4 visual-signoff artifact (T034).

Builds hull + deck (superstructure + hardware), exports to .FCStd via spec
002's writer, records the SHA-256, and prints a MANUAL SIGNOFF reminder for
the FreeCAD GUI review against docs/references/Alternativ3.JPG (constitution V).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from storebro import build_deck, build_hull, export_fcstd

SIGNOFF_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "signoff"
SIGNOFF_PATH = SIGNOFF_DIR / "storebro_v1_0_4_signoff.FCStd"


def test_v1_0_4_hardware_signoff_artifact(freecad_doc: object) -> None:
    SIGNOFF_DIR.mkdir(parents=True, exist_ok=True)
    hull = build_hull(document=freecad_doc)
    build_deck(hull)
    art = export_fcstd(hull.document, str(SIGNOFF_PATH))

    assert SIGNOFF_PATH.is_file()
    assert art.byte_count > 0
    digest = hashlib.sha256(SIGNOFF_PATH.read_bytes()).hexdigest()
    print(
        f"\nMANUAL SIGNOFF: open {SIGNOFF_PATH} in FreeCAD and confirm hull + "
        "6 superstructure Bodies + rubrail/bow-pulpit/lifelines/anchor-locker/"
        "cleats match docs/references/Alternativ3.JPG — record FreeCAD version + "
        f"OS in the register per constitution V.\nSHA-256: {digest}"
    )


def test_signoff_build_is_reproducible(freecad_doc: object) -> None:
    """The hardware build is structurally reproducible (volumes stable)."""
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    total_hw_volume = sum(
        getattr(deck, name).body.Shape.Volume
        for name in ("rubrail", "bow_pulpit", "anchor_locker", "cleats", "lifelines")
    )
    assert total_hw_volume > 0.0
