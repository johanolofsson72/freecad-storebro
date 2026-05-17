"""Unit test: every public hull name has a docstring with example (T045 — A5).

Covers FR-014. Introspects `storebro.hull.__all__` and asserts each callable
or class has a non-empty `__doc__` containing at least one `>>>` example.
"""

from __future__ import annotations

import inspect

import storebro.hull as hull_mod

NAMES_REQUIRING_DOCSTRINGS = [
    name for name in hull_mod.__all__
    if not name.startswith("_") and name in vars(hull_mod)
]


def _docstring_has_example(doc: str | None) -> bool:
    return bool(doc) and ">>>" in (doc or "")


def test_every_public_name_has_docstring() -> None:
    missing: list[str] = []
    for name in NAMES_REQUIRING_DOCSTRINGS:
        obj = getattr(hull_mod, name)
        if not getattr(obj, "__doc__", None):
            missing.append(name)
    assert not missing, f"FR-014 violation: missing docstrings on {missing}"


def test_every_public_name_has_docstring_example() -> None:
    missing_example: list[str] = []
    for name in NAMES_REQUIRING_DOCSTRINGS:
        obj = getattr(hull_mod, name)
        doc = inspect.getdoc(obj)
        if not _docstring_has_example(doc):
            missing_example.append(name)
    assert not missing_example, (
        f"FR-014 violation: missing >>> example block on {missing_example}"
    )
