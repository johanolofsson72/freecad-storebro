"""Unit test: interior module public docstrings + examples (T044).

Covers FR-014.
"""

from __future__ import annotations

import inspect

import storebro.interior as interior_mod


def test_every_public_name_has_docstring_with_example() -> None:
    missing: list[str] = []
    for name in interior_mod.__all__:
        obj = getattr(interior_mod, name)
        doc = inspect.getdoc(obj)
        if not doc or ">>>" not in doc:
            missing.append(name)
    assert not missing, f"FR-014 violation on {missing}"
