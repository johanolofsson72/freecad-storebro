"""Unit test: public docstrings + examples (T043).

Covers FR-015.
"""

from __future__ import annotations

import inspect

import storebro.export as export_mod


def _doc_has_example(doc: str | None) -> bool:
    return bool(doc) and ">>>" in (doc or "")


def test_every_public_name_has_docstring() -> None:
    missing: list[str] = []
    for name in export_mod.__all__:
        obj = getattr(export_mod, name)
        if not getattr(obj, "__doc__", None):
            missing.append(name)
    assert not missing, f"FR-015 violation: missing docstrings on {missing}"


def test_every_public_name_has_docstring_example() -> None:
    missing_example: list[str] = []
    for name in export_mod.__all__:
        obj = getattr(export_mod, name)
        doc = inspect.getdoc(obj)
        if not _doc_has_example(doc):
            missing_example.append(name)
    assert not missing_example, (
        f"FR-015 violation: missing >>> example block on {missing_example}"
    )
