"""Unit test: info key:value line format (T024, US3 polish).

Covers FR-009 + data-model §5: every line is `Key: Value`. The first line
matches the semver pattern for the package version.
"""

from __future__ import annotations

import re

import pytest

from storebro.cli import main

KEY_VALUE_LINE = re.compile(r"^[A-Za-z][\w\- ]+: .+$")
VERSION_LINE = re.compile(r"^freecad-storebro version: \d+\.\d+\.\d+$")


def test_info_lines_are_key_value(capsys: pytest.CaptureFixture[str]) -> None:
    """FR-009: every line follows `Key: Value`."""
    rc = main(["info"])
    captured = capsys.readouterr()
    assert rc == 0
    for line in captured.out.splitlines():
        if not line.strip():
            continue
        assert KEY_VALUE_LINE.match(line), (
            f"FR-009: line does not match Key: Value pattern: {line!r}"
        )


def test_info_version_is_semver(capsys: pytest.CaptureFixture[str]) -> None:
    """The package version line is `<name>: MAJOR.MINOR.PATCH`."""
    rc = main(["info"])
    captured = capsys.readouterr()
    assert rc == 0
    matched = [line for line in captured.out.splitlines() if VERSION_LINE.match(line)]
    assert len(matched) == 1, (
        f"expected exactly one semver version line, got {len(matched)}: {captured.out!r}"
    )
