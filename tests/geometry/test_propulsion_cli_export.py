"""Geometry test: CLI build composes propulsion into all exports (T032, US3).

Covers spec 014 FR-011, SC-007.
"""

from __future__ import annotations

from pathlib import Path

from storebro.cli import main


def test_cli_build_fcstd_includes_propulsion(tmp_path: Path) -> None:
    out = tmp_path / "boat.FCStd"
    rc = main(["build", "--layout", "Alternativ3", "--out", str(out)])
    assert rc == 0
    assert out.is_file() and out.stat().st_size > 0

    import FreeCAD  # type: ignore[import-not-found]

    doc = FreeCAD.openDocument(str(out))
    try:
        labels = [obj.Label for obj in doc.Objects]
        assert any(label.startswith("Propulsion_Shaft") for label in labels), labels
        assert any(label.startswith("Propulsion_Propeller") for label in labels), labels
    finally:
        FreeCAD.closeDocument(doc.Name)


def test_cli_no_propulsion_omits_bodies(tmp_path: Path) -> None:
    out = tmp_path / "bare.FCStd"
    rc = main(["build", "--layout", "Alternativ3", "--out", str(out), "--no-propulsion"])
    assert rc == 0

    import FreeCAD  # type: ignore[import-not-found]

    doc = FreeCAD.openDocument(str(out))
    try:
        labels = [obj.Label for obj in doc.Objects]
        assert not any(label.startswith("Propulsion_") for label in labels), labels
    finally:
        FreeCAD.closeDocument(doc.Name)


def test_cli_single_screw_step_export(tmp_path: Path) -> None:
    out = tmp_path / "boat.step"
    rc = main(
        ["build", "--layout", "Alternativ3", "--format", "step", "--out", str(out),
         "--engine-count", "1"]
    )
    assert rc == 0
    assert out.is_file() and out.stat().st_size > 0
