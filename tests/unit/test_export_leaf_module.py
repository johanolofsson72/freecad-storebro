"""Unit test: export module's source has no public-sibling imports (T042).

Covers FR-013. Verifies via AST that `src/storebro/export.py` itself does not
import `storebro.hull`, `storebro.deck`, `storebro.interior`, or
`storebro.cli`. Shared internal helpers (underscore-prefixed, e.g.
`storebro._freecad_check`) ARE permitted per the FR-013 amendment.
Package-level re-exports in `storebro/__init__.py` are out of scope.
"""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_PUBLIC_SIBLINGS = ["hull", "deck", "interior", "cli"]

EXPORT_SOURCE = (
    Path(__file__).parent.parent.parent / "src" / "storebro" / "export.py"
)


def test_export_source_has_no_public_sibling_imports() -> None:
    assert EXPORT_SOURCE.is_file(), f"export.py not found at {EXPORT_SOURCE}"
    tree = ast.parse(EXPORT_SOURCE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for sibling in FORBIDDEN_PUBLIC_SIBLINGS:
                forbidden = f"storebro.{sibling}"
                assert not module.startswith(forbidden), (
                    f"FR-013 violation: export.py:{node.lineno} imports from {module!r}"
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                for sibling in FORBIDDEN_PUBLIC_SIBLINGS:
                    forbidden = f"storebro.{sibling}"
                    assert not alias.name.startswith(forbidden), (
                        f"FR-013 violation: export.py:{node.lineno} imports "
                        f"{alias.name!r}"
                    )
