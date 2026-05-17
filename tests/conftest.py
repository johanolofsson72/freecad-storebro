"""Repo-root pytest conftest.

Registers project-wide markers and auto-tags geometry-tier tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_GEOMETRY_DIR = Path(__file__).parent / "geometry"


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers so --strict-markers does not reject them."""
    config.addinivalue_line(
        "markers",
        "requires_freecad: marks tests requiring a running FreeCAD installation "
        "(auto-skipped when FreeCAD is not importable)",
    )
    config.addinivalue_line(
        "markers",
        "unit: marks pure-Python unit tests that do not require FreeCAD",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Auto-tag every test under tests/geometry/ with requires_freecad."""
    for item in items:
        try:
            item_path = Path(item.path).resolve()
        except (AttributeError, ValueError):
            continue
        try:
            item_path.relative_to(_GEOMETRY_DIR.resolve())
        except ValueError:
            continue
        item.add_marker(pytest.mark.requires_freecad)
