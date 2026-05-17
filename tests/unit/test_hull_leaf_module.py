"""Unit test: hull module is a leaf (T044 — analyze remediation A2).

Covers FR-011. Asserts that importing `storebro.hull` does not transitively
import any of the sibling modules `deck`, `interior`, `export`, `cli`.
Also AST-walks `src/storebro/hull.py` to forbid `from storebro.deck/...`
imports at the source level.
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

FORBIDDEN_SIBLINGS = ["deck", "interior", "export", "cli"]

HULL_SOURCE = Path(__file__).parent.parent.parent / "src" / "storebro" / "hull.py"


def _purge_storebro_from_sys_modules() -> None:
    for name in list(sys.modules):
        if name == "storebro" or name.startswith("storebro."):
            del sys.modules[name]


def test_hull_import_does_not_pull_in_siblings() -> None:
    _purge_storebro_from_sys_modules()
    importlib.import_module("storebro.hull")
    for sibling in FORBIDDEN_SIBLINGS:
        full = f"storebro.{sibling}"
        assert full not in sys.modules, (
            f"FR-011 violation: importing storebro.hull also loaded {full}"
        )


def test_hull_source_has_no_sibling_imports() -> None:
    assert HULL_SOURCE.is_file(), f"hull.py not found at {HULL_SOURCE}"
    tree = ast.parse(HULL_SOURCE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for sibling in FORBIDDEN_SIBLINGS:
                forbidden = f"storebro.{sibling}"
                assert not module.startswith(forbidden), (
                    f"FR-011 violation: hull.py:line {node.lineno} imports "
                    f"from {module!r}"
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                for sibling in FORBIDDEN_SIBLINGS:
                    forbidden = f"storebro.{sibling}"
                    assert not alias.name.startswith(forbidden), (
                        f"FR-011 violation: hull.py:line {node.lineno} "
                        f"imports {alias.name!r}"
                    )
