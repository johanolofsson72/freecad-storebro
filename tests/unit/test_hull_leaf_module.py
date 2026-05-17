"""Unit test: hull module's source has no sibling imports (T044 — analyze remediation A2).

Covers FR-011. Verifies via AST that `src/storebro/hull.py` itself does not
import `storebro.deck`, `storebro.interior`, `storebro.export`, or
`storebro.cli`. Package-level re-exports in `storebro/__init__.py` are NOT
hull-module imports and are out of scope for this check.
"""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_SIBLINGS = ["deck", "interior", "export", "cli"]

HULL_SOURCE = Path(__file__).parent.parent.parent / "src" / "storebro" / "hull.py"


def test_hull_source_has_no_sibling_imports() -> None:
    assert HULL_SOURCE.is_file(), f"hull.py not found at {HULL_SOURCE}"
    tree = ast.parse(HULL_SOURCE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for sibling in FORBIDDEN_SIBLINGS:
                forbidden = f"storebro.{sibling}"
                assert not module.startswith(forbidden), (
                    f"FR-011 violation: hull.py:{node.lineno} imports from {module!r}"
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                for sibling in FORBIDDEN_SIBLINGS:
                    forbidden = f"storebro.{sibling}"
                    assert not alias.name.startswith(forbidden), (
                        f"FR-011 violation: hull.py:{node.lineno} imports "
                        f"{alias.name!r}"
                    )
