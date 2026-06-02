"""Unit test: spec 014 CLI propulsion flags + composition wiring (T031, FR-011).

Parser-level tests (no FreeCAD) plus a wiring test that monkeypatches the whole
build chain so `_run_build` can be exercised without a FreeCAD runtime.
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


def test_engine_count_defaults_to_two() -> None:
    ns = _parse_build(["build", "--out", "x.FCStd"])
    assert ns.engine_count == 2
    assert ns.no_propulsion is False


@pytest.mark.parametrize("value", [1, 2])
def test_engine_count_accepts_one_and_two(value: int) -> None:
    ns = _parse_build(["build", "--out", "x.FCStd", "--engine-count", str(value)])
    assert ns.engine_count == value


def test_engine_count_rejects_three(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.main(["build", "--out", "x.FCStd", "--engine-count", "3"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "invalid choice" in captured.err.lower() or "engine-count" in captured.err.lower()


def test_no_propulsion_flag_parses() -> None:
    ns = _parse_build(["build", "--out", "x.FCStd", "--no-propulsion"])
    assert ns.no_propulsion is True


def _install_fake_build_chain(
    monkeypatch: pytest.MonkeyPatch, calls: dict[str, Any]
) -> None:
    """Replace FreeCAD + the build/export chain with no-op fakes."""
    fake_freecad = types.ModuleType("FreeCAD")
    fake_freecad.newDocument = lambda name: types.SimpleNamespace(Name=name)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "FreeCAD", fake_freecad)

    hull = types.SimpleNamespace(document="doc", body="body")
    monkeypatch.setattr(cli, "build_hull", lambda document=None, parameters=None, apply_render_attributes=True: hull)
    monkeypatch.setattr(
        cli,
        "build_deck",
        lambda h, superstructure_variant="standard", apply_render_attributes=True: (
            types.SimpleNamespace()
        ),
    )
    monkeypatch.setattr(
        cli, "build_interior", lambda h, d, layout=None, apply_render_attributes=True: None
    )

    def _fake_prop(
        h: Any, d: Any, parameters: Any = None, apply_render_attributes: bool = True
    ) -> Any:
        calls["propulsion"] = parameters
        return types.SimpleNamespace()

    monkeypatch.setattr(cli, "build_propulsion", _fake_prop)

    artifact = types.SimpleNamespace(
        format="fcstd", target_path="x.FCStd", byte_count=1, sha256="deadbeef"
    )
    monkeypatch.setattr(cli, "export_fcstd", lambda *a, **k: artifact)


def test_run_build_invokes_propulsion_with_engine_count(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: dict[str, Any] = {}
    _install_fake_build_chain(monkeypatch, calls)
    rc = cli.main(["build", "--out", "x.FCStd", "--engine-count", "1"])
    assert rc == 0
    assert "propulsion" in calls
    assert calls["propulsion"].engine_count == 1


def test_run_build_skips_propulsion_when_flag_set(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: dict[str, Any] = {}
    _install_fake_build_chain(monkeypatch, calls)
    rc = cli.main(["build", "--out", "x.FCStd", "--no-propulsion"])
    assert rc == 0
    assert "propulsion" not in calls
