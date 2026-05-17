"""Unit test: deck module imports only hull + _freecad_check from storebro (T015).

Covers FR-011. The deck module is the project's first non-leaf module; it
imports `storebro.hull` (consumes the `Hull` type) and may import the shared
internal helper `storebro._freecad_check`. It MUST NOT import
`storebro.interior`, `storebro.export`, or `storebro.cli`.
"""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_PUBLIC_SIBLINGS = ["interior", "export", "cli"]

DECK_SOURCE = Path(__file__).parent.parent.parent / "src" / "storebro" / "deck.py"


def test_deck_imports_hull() -> None:
    """The deck module must import storebro.hull (it consumes the Hull type)."""
    assert DECK_SOURCE.is_file(), f"deck.py not found at {DECK_SOURCE}"
    tree = ast.parse(DECK_SOURCE.read_text(encoding="utf-8"))
    found_hull_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith("storebro.hull"):
                found_hull_import = True
                break
    assert found_hull_import, "FR-011 expectation: deck.py must import storebro.hull"


def test_deck_does_not_import_forbidden_siblings() -> None:
    """The deck module must NOT import interior/export/cli (FR-011)."""
    tree = ast.parse(DECK_SOURCE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for sibling in FORBIDDEN_PUBLIC_SIBLINGS:
                forbidden = f"storebro.{sibling}"
                assert not module.startswith(forbidden), (
                    f"FR-011 violation: deck.py:{node.lineno} imports from {module!r}"
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                for sibling in FORBIDDEN_PUBLIC_SIBLINGS:
                    forbidden = f"storebro.{sibling}"
                    assert not alias.name.startswith(forbidden), (
                        f"FR-011 violation: deck.py:{node.lineno} imports {alias.name!r}"
                    )
