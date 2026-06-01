"""Unit test: propulsion module public docstrings + API contract (T036, FR-013)."""

from __future__ import annotations

import inspect

import storebro.propulsion as prop_mod


def test_every_public_name_has_docstring() -> None:
    missing: list[str] = []
    for name in prop_mod.__all__:
        obj = getattr(prop_mod, name)
        if not getattr(obj, "__doc__", None):
            missing.append(name)
    assert not missing, f"FR-013 violation: missing docstrings on {missing}"


def test_build_propulsion_has_example() -> None:
    doc = inspect.getdoc(prop_mod.build_propulsion)
    assert doc and ">>>" in doc


def test_all_matches_module_exports() -> None:
    for name in prop_mod.__all__:
        assert hasattr(prop_mod, name), f"__all__ lists {name} but it is not defined"


def test_build_propulsion_signature() -> None:
    sig = inspect.signature(prop_mod.build_propulsion)
    params = list(sig.parameters)
    assert params[:3] == ["hull", "deck", "parameters"]
    assert sig.parameters["deck"].default is None
    assert sig.parameters["parameters"].default is None
