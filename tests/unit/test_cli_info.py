"""Unit test: storebro info subcommand (T016).

Covers FR-009 (output keys), FR-012 (no ANSI escapes — C2 remediation),
and SC-004 (< 1 s budget — C3 remediation).
"""

from __future__ import annotations

import builtins
import re
import time

import pytest

from storebro.cli import main

REQUIRED_KEYS = (
    "freecad-storebro version",
    "Python version",
    "Platform",
    "FreeCAD detected",
    "FreeCAD supported range",
)


def test_info_prints_all_required_keys(capsys: pytest.CaptureFixture[str]) -> None:
    """FR-009: every key from data-model §5 appears on stdout."""
    rc = main(["info"])
    captured = capsys.readouterr()
    assert rc == 0
    for key in REQUIRED_KEYS:
        assert key in captured.out, f"missing key on stdout: {key!r}"


def test_info_no_ansi_escape_codes(capsys: pytest.CaptureFixture[str]) -> None:
    """FR-012 + spec.allium NoColorCodesInDefaultOutput: no ANSI escapes."""
    rc = main(["info"])
    captured = capsys.readouterr()
    assert rc == 0
    assert re.search(r"\x1b\[", captured.out) is None, (
        f"FR-012 violation: ANSI escape found in stdout: {captured.out!r}"
    )


def test_info_completes_under_one_second(capsys: pytest.CaptureFixture[str]) -> None:
    """SC-004: info completes in under 1 s."""
    start = time.perf_counter()
    rc = main(["info"])
    elapsed = time.perf_counter() - start
    capsys.readouterr()
    assert rc == 0
    assert elapsed < 1.0, f"SC-004 violation: info took {elapsed:.3f} s"


def test_info_reports_not_detected_when_freecad_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """When FreeCAD import fails, the line reads `FreeCAD detected: not detected`."""
    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "FreeCAD":
            raise ImportError("simulated missing FreeCAD")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    rc = main(["info"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "FreeCAD detected: not detected" in captured.out


def test_info_version_matches_package(capsys: pytest.CaptureFixture[str]) -> None:
    """The version line agrees with storebro.__version__."""
    from storebro import __version__

    rc = main(["info"])
    captured = capsys.readouterr()
    assert rc == 0
    assert f"freecad-storebro version: {__version__}" in captured.out
