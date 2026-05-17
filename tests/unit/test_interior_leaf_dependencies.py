"""Unit test: interior module dependencies (T023).

Covers FR-011. The interior module IS allowed to import storebro.hull and
storebro.deck (it consumes both types), and may import the shared internal
helper storebro._freecad_check. It MUST NOT import storebro.export or
storebro.cli.
"""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_PUBLIC_SIBLINGS = ["export", "cli"]
EXPECTED_IMPORTS = {"storebro.hull", "storebro.deck"}

INTERIOR_SOURCE = Path(__file__).parent.parent.parent / "src" / "storebro" / "interior.py"


def test_interior_imports_hull_and_deck() -> None:
    assert INTERIOR_SOURCE.is_file()
    tree = ast.parse(INTERIOR_SOURCE.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for expected in EXPECTED_IMPORTS:
                if module.startswith(expected):
                    found.add(expected)
    missing = EXPECTED_IMPORTS - found
    assert not missing, f"FR-011: interior.py must import {EXPECTED_IMPORTS}, missing: {missing}"


def test_interior_does_not_import_forbidden_siblings() -> None:
    tree = ast.parse(INTERIOR_SOURCE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for sibling in FORBIDDEN_PUBLIC_SIBLINGS:
                forbidden = f"storebro.{sibling}"
                assert not module.startswith(forbidden), (
                    f"FR-011 violation: interior.py:{node.lineno} imports {module!r}"
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                for sibling in FORBIDDEN_PUBLIC_SIBLINGS:
                    forbidden = f"storebro.{sibling}"
                    assert not alias.name.startswith(forbidden), (
                        f"FR-011 violation: interior.py:{node.lineno} imports {alias.name!r}"
                    )
