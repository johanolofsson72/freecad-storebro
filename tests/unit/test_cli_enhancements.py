"""Unit tests: spec 027 CLI --json output + hull overrides (FR-001..FR-006).

No FreeCAD: the build chain is monkeypatched so _run_build is exercised
end-to-end without a geometry runtime.
"""

from __future__ import annotations

import json
import sys
import types
from typing import Any

import pytest

from storebro import cli


def _parse_build(argv: list[str]) -> Any:
    return cli._build_top_parser().parse_args(argv)


def test_json_flag_defaults_false() -> None:
    assert _parse_build(["build", "--out", "x.FCStd"]).json is False


def test_overrides_default_none() -> None:
    ns = _parse_build(["build", "--out", "x.FCStd"])
    assert ns.loa is None and ns.beam is None and ns.draft is None and ns.station_count is None


def test_overrides_parse() -> None:
    ns = _parse_build(
        ["build", "--out", "x.FCStd", "--loa", "11.0", "--beam", "3.4",
         "--draft", "1.1", "--station-count", "51"]
    )
    assert ns.loa == 11.0 and ns.beam == 3.4 and ns.draft == 1.1 and ns.station_count == 51


def _install_fake_chain(monkeypatch: pytest.MonkeyPatch, calls: dict[str, Any]) -> None:
    fake_freecad = types.ModuleType("FreeCAD")
    fake_freecad.newDocument = lambda name: types.SimpleNamespace(Name=name)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "FreeCAD", fake_freecad)

    def _fake_hull(document: Any = None, parameters: Any = None, apply_render_attributes: bool = True) -> Any:
        calls["hull_params"] = parameters
        return types.SimpleNamespace(document="doc", body="body")

    monkeypatch.setattr(cli, "build_hull", _fake_hull)
    monkeypatch.setattr(
        cli,
        "build_deck",
        lambda h, superstructure_variant="standard", apply_render_attributes=True: types.SimpleNamespace(),
    )
    monkeypatch.setattr(
        cli, "build_interior", lambda h, d, layout=None, apply_render_attributes=True: None
    )
    monkeypatch.setattr(
        cli,
        "build_propulsion",
        lambda h, d, parameters=None, apply_render_attributes=True: types.SimpleNamespace(),
    )
    artifact = types.SimpleNamespace(
        format="fcstd", target_path="x.FCStd", byte_count=42, sha256="deadbeef"
    )
    monkeypatch.setattr(cli, "export_fcstd", lambda *a, **k: artifact)


def test_json_output_is_single_object(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _install_fake_chain(monkeypatch, {})
    rc = cli.main(["build", "--out", "x.FCStd", "--no-propulsion", "--json"])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    obj = json.loads(out)  # exactly one parseable object
    assert set(obj) == {"format", "target_path", "byte_count", "sha256", "version"}
    assert obj["byte_count"] == 42 and obj["format"] == "fcstd"


def test_human_line_without_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _install_fake_chain(monkeypatch, {})
    rc = cli.main(["build", "--out", "x.FCStd", "--no-propulsion"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "wrote fcstd" in out
    with pytest.raises(json.JSONDecodeError):
        json.loads(out.strip())


def test_overrides_thread_into_hull_params(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}
    _install_fake_chain(monkeypatch, calls)
    rc = cli.main(
        ["build", "--out", "x.FCStd", "--no-propulsion", "--station-count", "51", "--loa", "11.0"]
    )
    assert rc == 0
    hp = calls["hull_params"]
    assert hp is not None and hp.station_count == 51 and hp.loa == 11.0


def test_no_overrides_passes_none(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}
    _install_fake_chain(monkeypatch, calls)
    cli.main(["build", "--out", "x.FCStd", "--no-propulsion"])
    assert calls["hull_params"] is None  # defaults path (back-compat)


def test_out_of_range_override_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_chain(monkeypatch, {})
    rc = cli.main(["build", "--out", "x.FCStd", "--no-propulsion", "--station-count", "999"])
    assert rc != 0  # HullParameters validation → non-zero exit, no artifact
