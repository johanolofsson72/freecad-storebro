"""Unit test: list-layouts column format (T023, US2 polish).

Covers FR-007's three-column tab-separated structure: layout name, source,
description. Every row must have exactly 2 tab separators and a non-empty
third column.
"""

from __future__ import annotations

import pytest

from storebro.cli import main


def test_list_layouts_has_three_columns(capsys: pytest.CaptureFixture[str]) -> None:
    """FR-007: each row is `<name>\\t<source>\\t<description>`."""
    rc = main(["list-layouts"])
    captured = capsys.readouterr()
    assert rc == 0
    for line in captured.out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        assert len(parts) == 3, (
            f"FR-007: expected 3 tab-separated columns, got {len(parts)} in {line!r}"
        )
        name, source, description = parts
        assert name.startswith("Alternativ")
        assert source, "second column (source) must be non-empty"
        assert description, "third column (description) must be non-empty"
