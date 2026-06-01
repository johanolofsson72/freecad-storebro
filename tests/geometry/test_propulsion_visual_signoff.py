"""Geometry test: produce the v1.1.0 visual-signoff artifact (T038).

Builds hull + deck + interior + propulsion, exports to .FCStd, records the
SHA-256, and prints a MANUAL SIGNOFF reminder for the FreeCAD GUI review
(constitution V).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from storebro import build_deck, build_hull, build_interior, build_propulsion, export_fcstd

SIGNOFF_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "signoff"
SIGNOFF_PATH = SIGNOFF_DIR / "storebro_v1_1_0_signoff.FCStd"


def test_v1_1_0_propulsion_signoff_artifact(freecad_doc: object) -> None:
    SIGNOFF_DIR.mkdir(parents=True, exist_ok=True)
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    build_interior(hull, deck, layout="Alternativ3")
    build_propulsion(hull, deck)
    art = export_fcstd(hull.document, str(SIGNOFF_PATH))

    assert SIGNOFF_PATH.is_file()
    assert art.byte_count > 0
    digest = hashlib.sha256(SIGNOFF_PATH.read_bytes()).hexdigest()
    print(
        f"\nMANUAL SIGNOFF: open {SIGNOFF_PATH} in FreeCAD and confirm hull + deck "
        "+ interior + propulsion (engine bed, engine, twin shafts, props, rudders) "
        f"read as an RC34 inboard installation.\nSHA-256: {digest}"
    )


def test_signoff_build_has_expected_component_counts(freecad_doc: object) -> None:
    hull = build_hull(document=freecad_doc)
    deck = build_deck(hull)
    prop = build_propulsion(hull, deck)
    assert len(prop.shafts) == 2
    assert len(prop.propellers) == 2
    total_volume = sum(w.body.Shape.Volume for w in prop.shafts)
    assert total_volume > 0.0
