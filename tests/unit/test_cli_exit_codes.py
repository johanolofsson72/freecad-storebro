"""Unit test: exception → exit code dispatch (T014).

Covers FR-005 + FR-011: input errors → exit 1, system errors → exit 2.
Contributes ≥8 distinct cases to SC-007's invalid-input bar.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from storebro.cli import _exit_code_for
from storebro.deck import DeckConstructionError, DeckParameterError
from storebro.export import ExportInputError, ExportWriteError
from storebro.hull import HullConstructionError, HullParameterError
from storebro.interior import InteriorConstructionError, InteriorParameterError


def _make_hull_param_error() -> HullParameterError:
    return HullParameterError("loa", 0.0, "must be positive")


def _make_deck_param_error() -> DeckParameterError:
    return DeckParameterError("freeboard_aft", 0.0, "must be positive")


def _make_interior_param_error() -> InteriorParameterError:
    return InteriorParameterError("source", None, "layout", "unknown layout")


def _make_export_input_error() -> ExportInputError:
    return ExportInputError("target_path", "missing parent directory", "/no/such/x.step")


def _make_hull_construction_error() -> HullConstructionError:
    return HullConstructionError("FreeCAD not available")


def _make_deck_construction_error() -> DeckConstructionError:
    return DeckConstructionError("Part.Mirroring failed")


def _make_interior_construction_error() -> InteriorConstructionError:
    return InteriorConstructionError("compartment body creation failed")


def _make_export_write_error() -> ExportWriteError:
    return ExportWriteError(
        "disk full",
        target_path=Path("/tmp/x.step"),
        format="step",
    )


INPUT_ERROR_FACTORIES: list[tuple[str, Any]] = [
    ("HullParameterError", _make_hull_param_error),
    ("DeckParameterError", _make_deck_param_error),
    ("InteriorParameterError", _make_interior_param_error),
    ("ExportInputError", _make_export_input_error),
]

SYSTEM_ERROR_FACTORIES: list[tuple[str, Any]] = [
    ("HullConstructionError", _make_hull_construction_error),
    ("DeckConstructionError", _make_deck_construction_error),
    ("InteriorConstructionError", _make_interior_construction_error),
    ("ExportWriteError", _make_export_write_error),
]


@pytest.mark.parametrize(("name", "factory"), INPUT_ERROR_FACTORIES, ids=lambda x: str(x))
def test_input_errors_map_to_exit_one(name: str, factory: Any) -> None:
    """FR-011: every input-error type → exit code 1."""
    exc = factory()
    assert _exit_code_for(exc) == 1, f"{name} should map to exit 1"


@pytest.mark.parametrize(("name", "factory"), SYSTEM_ERROR_FACTORIES, ids=lambda x: str(x))
def test_system_errors_map_to_exit_two(name: str, factory: Any) -> None:
    """FR-011: every system-error type → exit code 2."""
    exc = factory()
    assert _exit_code_for(exc) == 2, f"{name} should map to exit 2"


def test_unknown_exception_maps_to_exit_two() -> None:
    """FR-011 default: unexpected exception → exit code 2 (system category)."""
    assert _exit_code_for(RuntimeError("unexpected")) == 2
    assert _exit_code_for(KeyboardInterrupt()) == 2
