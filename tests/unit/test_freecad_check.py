"""Unit tests for the lazy FreeCAD version-check helper (T016).

Covers FR-013 + research.md R6. Uses monkeypatched FreeCAD.Version values
to exercise the cached lazy-check logic without an actual FreeCAD install.
"""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

import pytest

from storebro import HullConstructionError, _freecad_check


@pytest.fixture(autouse=True)
def _reset_check_cache() -> None:
    """Clear the module-level cache before every test."""
    _freecad_check._reset_cache_for_tests()


def _install_fake_freecad(version: tuple[int, int]) -> ModuleType:
    """Install a fake `FreeCAD` module exposing the given Version() result.

    Returns the installed module so callers can later uninstall it if needed.
    """
    fake = ModuleType("FreeCAD")

    def _version() -> list[Any]:
        return [version[0], version[1], 0, "fake", "fake-build"]

    fake.Version = _version  # type: ignore[attr-defined]
    sys.modules["FreeCAD"] = fake
    return fake


def _remove_fake_freecad() -> None:
    sys.modules.pop("FreeCAD", None)


class TestSupportedVersion:
    def test_freecad_1_1_passes(self) -> None:
        _install_fake_freecad((1, 1))
        try:
            _freecad_check.ensure_supported_freecad()
        finally:
            _remove_fake_freecad()

    def test_freecad_1_2_passes(self) -> None:
        _install_fake_freecad((1, 2))
        try:
            _freecad_check.ensure_supported_freecad()
        finally:
            _remove_fake_freecad()

    def test_freecad_1_9_passes(self) -> None:
        _install_fake_freecad((1, 9))
        try:
            _freecad_check.ensure_supported_freecad()
        finally:
            _remove_fake_freecad()


class TestUnsupportedVersion:
    def test_freecad_0_20_rejected(self) -> None:
        _install_fake_freecad((0, 20))
        try:
            with pytest.raises(HullConstructionError) as exc_info:
                _freecad_check.ensure_supported_freecad()
        finally:
            _remove_fake_freecad()
        assert exc_info.value.detected_version == (0, 20)
        assert exc_info.value.supported_range is not None
        assert "1.1" in exc_info.value.supported_range

    def test_freecad_2_0_rejected_as_above_exclusive_max(self) -> None:
        _install_fake_freecad((2, 0))
        try:
            with pytest.raises(HullConstructionError) as exc_info:
                _freecad_check.ensure_supported_freecad()
        finally:
            _remove_fake_freecad()
        assert exc_info.value.detected_version == (2, 0)

    def test_freecad_1_0_rejected(self) -> None:
        _install_fake_freecad((1, 0))
        try:
            with pytest.raises(HullConstructionError):
                _freecad_check.ensure_supported_freecad()
        finally:
            _remove_fake_freecad()


class TestCaching:
    def test_second_call_after_success_is_noop(self) -> None:
        _install_fake_freecad((1, 1))
        try:
            _freecad_check.ensure_supported_freecad()
            # Replace FreeCAD with one that would fail, and verify the cache
            # returns success without re-probing.
            _install_fake_freecad((0, 20))
            _freecad_check.ensure_supported_freecad()  # no raise
        finally:
            _remove_fake_freecad()


class TestImportFailure:
    def test_missing_freecad_raises_construction_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When FreeCAD cannot be imported, ensure_supported_freecad raises
        HullConstructionError with detected_version=None.

        Tests the import-failure path explicitly via monkeypatch — works whether
        or not a real FreeCAD is on the host's PYTHONPATH.
        """
        _remove_fake_freecad()
        _freecad_check._reset_cache_for_tests()
        import builtins

        real_import = builtins.__import__

        def fake_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "FreeCAD":
                raise ImportError("simulated missing FreeCAD for test")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        with pytest.raises(HullConstructionError) as exc_info:
            _freecad_check.ensure_supported_freecad()
        assert exc_info.value.detected_version is None
        assert exc_info.value.supported_range is not None
