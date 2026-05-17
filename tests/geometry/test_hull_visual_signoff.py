"""Geometry test: produce visual-signoff artifact (T033).

Builds the default hull and saves the resulting .FCStd to /tmp so a human
can open it in the FreeCAD GUI and visually compare against
`docs/references/Alternativ*.JPG`. The mandatory PR description line
"Visually verified in FreeCAD: <version> on <OS>" is captured manually
in T040.
"""

from __future__ import annotations

from pathlib import Path

from storebro import build_hull

SIGNOFF_PATH = Path("/tmp/storebro_hull_signoff_001.FCStd")


def test_default_hull_saves_to_signoff_path() -> None:
    hull = build_hull()
    hull.document.saveAs(str(SIGNOFF_PATH))
    print(
        f"\nMANUAL SIGNOFF: open {SIGNOFF_PATH} in FreeCAD and confirm "
        "proportions match docs/references/Alternativ*.JPG — record "
        "FreeCAD version + OS in PR description per constitution V"
    )
    assert SIGNOFF_PATH.is_file()
    assert SIGNOFF_PATH.stat().st_size > 0
