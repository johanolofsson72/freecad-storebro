"""Lazy FreeCAD version probe (per spec FR-013 + research.md R6).

Reads the supported range from `pyproject.toml`'s `[tool.freecad-storebro]`
table at first call, caches the result in a module-level flag, and raises
`HullConstructionError` when the running FreeCAD version is outside the range.

Importing this module does NOT trigger the check — only the first call to
`ensure_supported_freecad()` does. Subsequent calls in the same process are
no-ops.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

_FREECAD_VERSION_OK: bool | None = None
_SUPPORTED_RANGE_LITERAL: str | None = None
_SUPPORTED_MIN: tuple[int, int] | None = None
_SUPPORTED_MAX_EXCLUSIVE: tuple[int, int] | None = None


def _find_pyproject() -> Path:
    """Walk up from this file until a pyproject.toml is found."""
    here = Path(__file__).resolve()
    for parent in (here.parent, *here.parents):
        candidate = parent / "pyproject.toml"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "Could not locate pyproject.toml when probing for supported FreeCAD range."
    )


def _read_supported_range_from_pyproject() -> tuple[str, tuple[int, int], tuple[int, int]]:
    """Read `[tool.freecad-storebro]` from pyproject.toml.

    Returns:
        (literal_range, min_version, max_exclusive_version) as
        (e.g. ">=1.1,<2.0", (1, 1), (2, 0)).
    """
    pyproject_path = _find_pyproject()
    with pyproject_path.open("rb") as fp:
        data = tomllib.load(fp)
    table = data.get("tool", {}).get("freecad-storebro", {})

    literal = str(table.get("supported_freecad", ">=1.1,<2.0"))
    min_pair = table.get("supported_freecad_min", [1, 1])
    max_pair = table.get("supported_freecad_max_exclusive", [2, 0])

    return (
        literal,
        (int(min_pair[0]), int(min_pair[1])),
        (int(max_pair[0]), int(max_pair[1])),
    )


def _load_supported_range() -> None:
    global _SUPPORTED_RANGE_LITERAL, _SUPPORTED_MIN, _SUPPORTED_MAX_EXCLUSIVE
    if _SUPPORTED_RANGE_LITERAL is None:
        literal, min_v, max_v = _read_supported_range_from_pyproject()
        _SUPPORTED_RANGE_LITERAL = literal
        _SUPPORTED_MIN = min_v
        _SUPPORTED_MAX_EXCLUSIVE = max_v


def _read_freecad_version() -> tuple[int, int]:
    """Probe the running FreeCAD's Version() and return (major, minor).

    Raises:
        ImportError: if FreeCAD itself is not importable.
        RuntimeError: if FreeCAD.Version() returns something we can't parse.
    """
    import FreeCAD

    raw: Any = FreeCAD.Version()
    if not raw or len(raw) < 2:
        raise RuntimeError(f"FreeCAD.Version() returned unparseable value: {raw!r}")
    return (int(raw[0]), int(raw[1]))


def ensure_supported_freecad() -> None:
    """Raise HullConstructionError if the running FreeCAD version is unsupported.

    Idempotent — caches the result of the first call in this process and
    becomes a no-op on subsequent calls.
    """
    global _FREECAD_VERSION_OK
    if _FREECAD_VERSION_OK is True:
        return

    # Import locally to avoid circular import (hull.py imports this module
    # and defines HullConstructionError).
    from storebro.hull import HullConstructionError

    _load_supported_range()
    assert _SUPPORTED_MIN is not None
    assert _SUPPORTED_MAX_EXCLUSIVE is not None
    assert _SUPPORTED_RANGE_LITERAL is not None

    try:
        detected = _read_freecad_version()
    except ImportError:
        _FREECAD_VERSION_OK = False
        raise HullConstructionError(
            "FreeCAD is not importable on this host. Install FreeCAD 1.1+ "
            "and ensure its Python bindings are on sys.path.",
            detected_version=None,
            supported_range=_SUPPORTED_RANGE_LITERAL,
        ) from None

    if detected < _SUPPORTED_MIN or detected >= _SUPPORTED_MAX_EXCLUSIVE:
        _FREECAD_VERSION_OK = False
        raise HullConstructionError(
            f"unsupported FreeCAD version: {detected[0]}.{detected[1]} — "
            f"supported range is {_SUPPORTED_RANGE_LITERAL}",
            detected_version=detected,
            supported_range=_SUPPORTED_RANGE_LITERAL,
        )

    _FREECAD_VERSION_OK = True


def _reset_cache_for_tests() -> None:
    """Test-only helper: clear the cached version-check result.

    NOT part of the public API. Used by tests/unit/test_freecad_check.py to
    exercise the lazy-check behavior independently per test.
    """
    global _FREECAD_VERSION_OK, _SUPPORTED_RANGE_LITERAL
    global _SUPPORTED_MIN, _SUPPORTED_MAX_EXCLUSIVE
    _FREECAD_VERSION_OK = None
    _SUPPORTED_RANGE_LITERAL = None
    _SUPPORTED_MIN = None
    _SUPPORTED_MAX_EXCLUSIVE = None
