"""Unit test: storebro list-layouts subcommand (T017).

Covers FR-007 (all five canonical layouts, ordered), FR-008 (no FreeCAD needed),
FR-012 (no ANSI escapes — C2 remediation), and SC-003 (< 1 s — C3 remediation).
"""

from __future__ import annotations

import re
import time

import pytest

from storebro.cli import main

CANONICAL_ORDER = (
    "Alternativ1",
    "Alternativ2",
    "Alternativ3",
    "Alternativ4",
    "Alternativ5",
)


def test_list_layouts_exits_zero_and_prints_five_lines(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """FR-007: exactly five canonical layouts on stdout, in order."""
    rc = main(["list-layouts"])
    captured = capsys.readouterr()
    assert rc == 0
    lines = [line for line in captured.out.splitlines() if line.strip()]
    assert len(lines) == 5, f"expected 5 lines, got {len(lines)}: {lines}"
    for expected, line in zip(CANONICAL_ORDER, lines, strict=True):
        first_col = line.split("\t", 1)[0]
        assert first_col == expected, (
            f"FR-007 order violation: expected {expected}, got {first_col!r}"
        )


def test_list_layouts_uses_tab_separator(capsys: pytest.CaptureFixture[str]) -> None:
    """Each line is tab-separated (machine-parseable)."""
    rc = main(["list-layouts"])
    captured = capsys.readouterr()
    assert rc == 0
    for line in captured.out.splitlines():
        if not line.strip():
            continue
        assert "\t" in line, f"missing tab in list-layouts output line: {line!r}"


def test_list_layouts_no_ansi_escape_codes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """FR-012 + spec.allium NoColorCodesInDefaultOutput: no ANSI escapes."""
    rc = main(["list-layouts"])
    captured = capsys.readouterr()
    assert rc == 0
    assert re.search(r"\x1b\[", captured.out) is None, (
        f"FR-012 violation: ANSI escape found in stdout: {captured.out!r}"
    )


def test_list_layouts_completes_under_one_second(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """SC-003: list-layouts completes in under 1 s."""
    start = time.perf_counter()
    rc = main(["list-layouts"])
    elapsed = time.perf_counter() - start
    capsys.readouterr()
    assert rc == 0
    assert elapsed < 1.0, f"SC-003 violation: list-layouts took {elapsed:.3f} s"
