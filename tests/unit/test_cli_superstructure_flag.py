"""Unit tests: spec 016 CLI --superstructure flag + composition wiring (FR-015).

Parser-level tests (no FreeCAD) plus a wiring test that monkeypatches the build
chain so `_run_build` can be exercised without a FreeCAD runtime.
"""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from storebro import cli


def _parse_build(argv: list[str]) -> Any:
    parser = cli._build_top_parser()
    return parser.parse_args(argv)


def test_superstructure_defaults_to_standard() -> None:
    ns = _parse_build(["build", "--out", "x.FCStd"])
    assert ns.superstructure == "standard"


@pytest.mark.parametrize("value", ["standard", "ds"])
def test_superstructure_accepts_canonical_values(value: str) -> None:
    ns = _parse_build(["build", "--out", "x.FCStd", "--superstructure", value])
    assert ns.superstructure == value


def test_superstructure_rejects_unknown(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.main(["build", "--out", "x.FCStd", "--superstructure", "flybridge"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "invalid choice" in captured.err.lower() or "superstructure" in captured.err.lower()


def _install_fake_build_chain(
    monkeypatch: pytest.MonkeyPatch, calls: dict[str, Any]
) -> None:
    """Replace FreeCAD + the build/export chain with no-op fakes."""
    fake_freecad = types.ModuleType("FreeCAD")
    fake_freecad.newDocument = lambda name: types.SimpleNamespace(Name=name)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "FreeCAD", fake_freecad)

    hull = types.SimpleNamespace(document="doc", body="body")
    monkeypatch.setattr(cli, "build_hull", lambda document=None, apply_render_attributes=True: hull)

    def _fake_deck(
        h: Any, superstructure_variant: str = "standard", apply_render_attributes: bool = True
    ) -> Any:
        calls["superstructure_variant"] = superstructure_variant
        return types.SimpleNamespace()

    monkeypatch.setattr(cli, "build_deck", _fake_deck)
    monkeypatch.setattr(
        cli, "build_interior", lambda h, d, layout=None, apply_render_attributes=True: None
    )
    monkeypatch.setattr(
        cli,
        "build_propulsion",
        lambda h, d, parameters=None, apply_render_attributes=True: types.SimpleNamespace(),
    )
    artifact = types.SimpleNamespace(
        format="fcstd", target_path="x.FCStd", byte_count=1, sha256="deadbeef"
    )
    monkeypatch.setattr(cli, "export_fcstd", lambda *a, **k: artifact)


def test_run_build_threads_ds_variant(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}
    _install_fake_build_chain(monkeypatch, calls)
    rc = cli.main(["build", "--out", "x.FCStd", "--superstructure", "ds", "--no-propulsion"])
    assert rc == 0
    assert calls["superstructure_variant"] == "ds"


def test_run_build_defaults_to_standard_variant(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}
    _install_fake_build_chain(monkeypatch, calls)
    rc = cli.main(["build", "--out", "x.FCStd", "--no-propulsion"])
    assert rc == 0
    assert calls["superstructure_variant"] == "standard"
