"""Unit test: public surface is exactly `main`, with a docstring (T028, SC-008).

Verifies the CLI module's __all__ is exactly ["main"], and that main has a
non-empty docstring containing a doctest-style example block.
"""

from __future__ import annotations

import storebro.cli as cli_module


def test_cli_all_is_only_main() -> None:
    """SC-008: cli's __all__ is exactly the one public function."""
    assert cli_module.__all__ == ["main"], (
        f"SC-008 violation: __all__={cli_module.__all__!r}, expected ['main']"
    )


def test_main_has_nontrivial_docstring_with_example() -> None:
    """`main.__doc__` is non-empty and contains a `>>>` example block."""
    doc = cli_module.main.__doc__ or ""
    assert doc.strip(), "main.__doc__ is empty"
    assert ">>>" in doc, "main.__doc__ must contain a `>>>` example block"
