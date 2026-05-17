"""Unit test: CLI is non-interactive (T019a).

Covers FR-013 + spec.allium `NoUserPrompts`. The CLI must not call `input()`
or `getpass.getpass()` — every input is a command-line argument.
"""

from __future__ import annotations

import ast
from pathlib import Path

CLI_SOURCE = Path(__file__).parent.parent.parent / "src" / "storebro" / "cli.py"


def test_cli_does_not_call_input() -> None:
    """No `input(...)` call anywhere in cli.py."""
    assert CLI_SOURCE.is_file()
    tree = ast.parse(CLI_SOURCE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id != "input", f"FR-013 violation: cli.py:{node.lineno} calls input()"


def test_cli_does_not_import_or_call_getpass() -> None:
    """No `import getpass` and no `getpass.getpass(...)` calls in cli.py."""
    tree = ast.parse(CLI_SOURCE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "getpass", (
                    f"FR-013 violation: cli.py:{node.lineno} imports getpass"
                )
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "") != "getpass", (
                f"FR-013 violation: cli.py:{node.lineno} from-imports getpass"
            )
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                assert not (func.value.id == "getpass" and func.attr == "getpass"), (
                    f"FR-013 violation: cli.py:{node.lineno} calls getpass.getpass()"
                )
