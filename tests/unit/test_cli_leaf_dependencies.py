"""Unit test: CLI is the dependency-arrow apex (T019).

Covers FR-014: storebro.cli MUST import storebro.hull, storebro.deck,
storebro.interior, and storebro.export. It is the only public module allowed
to do so.
"""

from __future__ import annotations

import ast
from pathlib import Path

CLI_SOURCE = Path(__file__).parent.parent.parent / "src" / "storebro" / "cli.py"

EXPECTED_IMPORTS = {
    "storebro.hull",
    "storebro.deck",
    "storebro.interior",
    "storebro.export",
}


def test_cli_imports_all_four_prior_modules() -> None:
    """FR-014: CLI is the apex — composes all four public modules."""
    assert CLI_SOURCE.is_file(), f"missing source: {CLI_SOURCE}"
    tree = ast.parse(CLI_SOURCE.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for expected in EXPECTED_IMPORTS:
                if module == expected or module.startswith(expected + "."):
                    found.add(expected)
    missing = EXPECTED_IMPORTS - found
    assert not missing, f"FR-014: cli.py must import {EXPECTED_IMPORTS}, missing: {missing}"
