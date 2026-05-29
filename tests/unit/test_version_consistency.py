"""Unit test: storebro.__version__ matches pyproject.toml (spec 010 T002, FR-019).

Spec 009 bumped pyproject to 1.0.3 but left the dunder at 1.0.2; spec 010
corrects the drift and this test guards against it recurring.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import storebro


def _pyproject_version() -> str:
    root = Path(__file__).resolve().parents[2]
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    version = data["project"]["version"]
    assert isinstance(version, str)
    return version


def test_dunder_matches_pyproject() -> None:
    assert storebro.__version__ == _pyproject_version()


def test_version_is_current() -> None:
    assert storebro.__version__ == "1.0.7"
