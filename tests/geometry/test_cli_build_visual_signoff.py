"""Geometry test: CLI visual signoff artifact (T027, T034).

Generates /tmp/storebro_v1_signoff.FCStd via the CLI for the v1.0.0 release
manual signoff per constitution principle V. The test asserts the file
exists; the human opens it in the FreeCAD GUI.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from storebro.cli import main

pytestmark = pytest.mark.requires_freecad


def test_cli_v1_signoff_artifact(capsys: pytest.CaptureFixture[str]) -> None:
    """Produce the v1.0.0 release-signoff .FCStd via the CLI."""
    out = Path(os.environ.get("STOREBRO_SIGNOFF_PATH", "/tmp/storebro_v1_signoff.FCStd"))
    rc = main(["build", "--out", str(out)])
    captured = capsys.readouterr()
    assert rc == 0, f"signoff build exited {rc}; stderr={captured.err!r}"
    assert out.is_file()
    print(
        f"\n MANUAL SIGNOFF REMINDER \nOpen {out} in FreeCAD GUI and verify hull + deck + Alternativ3 interior look correct against docs/references/Alternativ3.JPG.\n"
    )
