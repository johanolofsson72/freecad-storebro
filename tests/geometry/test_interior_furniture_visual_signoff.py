"""Geometry test: produce the v1.0.6 visual-signoff artifact (T026)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from storebro import build_deck, build_hull, build_interior, export_fcstd

SIGNOFF_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "signoff"
SIGNOFF_PATH = SIGNOFF_DIR / "storebro_v1_0_6_signoff.FCStd"


def test_v1_0_6_interior_signoff_artifact(freecad_doc: object) -> None:
    SIGNOFF_DIR.mkdir(parents=True, exist_ok=True)
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    build_interior(hull, deck, layout="Alternativ1")
    art = export_fcstd(hull.document, str(SIGNOFF_PATH))
    assert SIGNOFF_PATH.is_file()
    assert art.byte_count > 0
    digest = hashlib.sha256(SIGNOFF_PATH.read_bytes()).hexdigest()
    print(
        f"\nMANUAL SIGNOFF: open {SIGNOFF_PATH} in FreeCAD and confirm the Alt1 "
        "interior furniture (berth+cushion, galley counter with recesses, "
        "toilet+sink, settee+table, bulkheads) reads correctly against "
        f"docs/references/Alternativ1.JPG.\nSHA-256: {digest}"
    )
