"""Unit test: python -m storebro entry shim (T018).

Covers FR-001 + clarify Q1: `python -m storebro` and the `storebro` console
script both call the same `main(argv)` function.
"""

from __future__ import annotations

import importlib


def test_main_module_importable_without_side_effects() -> None:
    """`import storebro.__main__` succeeds and the inner sys.exit is gated by __name__."""
    module = importlib.import_module("storebro.__main__")
    assert hasattr(module, "main"), "__main__.py must re-import storebro.cli.main"


def test_main_module_main_is_callable() -> None:
    """The re-exported main is the same callable as storebro.cli.main."""
    from storebro import __main__ as main_module
    from storebro import cli

    assert main_module.main is cli.main
