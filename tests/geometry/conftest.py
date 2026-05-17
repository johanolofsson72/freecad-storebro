"""Geometry-tier conftest.

Tests in this directory require a running FreeCAD installation. When FreeCAD
is not importable, every collected test is skipped at module-load time so
the suite stays green on hosts without FreeCAD (per CLAUDE.md and research.md R8).
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest

try:
    import FreeCAD  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - exercised on hosts without FreeCAD
    pytest.skip(
        "FreeCAD is not importable on this host; "
        "skipping the entire geometry test tier. "
        "Install FreeCAD 1.1+ and re-run to execute these tests.",
        allow_module_level=True,
    )


@pytest.fixture
def freecad_doc() -> Generator[Any, None, None]:
    """Create a fresh in-memory FreeCAD document per test; close it on teardown."""
    doc = FreeCAD.newDocument("storebro_test_doc")
    try:
        yield doc
    finally:
        FreeCAD.closeDocument(doc.Name)
