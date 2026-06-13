"""Unit tests: spec 031 CLI --hull-variant flag + wiring (FR-009).

Parser-level tests (no FreeCAD) plus a wiring test that monkeypatches the build chain so
`_run_build` threads the variant into build_hull without a FreeCAD runtime."""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from storebro import cli


def _parse_build(argv: list[str]) -> Any:
    parser = cli._build_top_parser()
    return parser.parse_args(argv)


def test_hull_variant_defaults_to_standard() -> None:
    ns = _parse_build(["build", "--out", "x.FCStd"])
    assert ns.hull_variant == "standard"


@pytest.mark.parametrize("value", ["standard", "hard_chine"])
def test_hull_variant_accepts_canonical_values(value: str) -> None:
    ns = _parse_build(["build", "--out", "x.FCStd", "--hull-variant", value])
    assert ns.hull_variant == value


def test_hull_variant_rejects_unknown(capsys: pytest.CaptureFixture[str]) -> None:
    rc = cli.main(["build", "--out", "x.FCStd", "--hull-variant", "deep_vee"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "invalid choice" in captured.err.lower() or "hull-variant" in captured.err.lower()


def _install_fake_build_chain(
    monkeypatch: pytest.MonkeyPatch, calls: dict[str, Any]
) -> None:
    fake_freecad = types.ModuleType("FreeCAD")
    fake_freecad.newDocument = lambda name: types.SimpleNamespace(Name=name)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "FreeCAD", fake_freecad)

    def _fake_hull(
        document: Any = None,
        parameters: Any = None,
        hull_variant: str = "standard",
        apply_render_attributes: bool = True,
    ) -> Any:
        calls["hull_variant"] = hull_variant
        return types.SimpleNamespace(
            document="doc", body="body", hull_variant=hull_variant, variant_applied=True
        )

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
        format="fcstd", target_path="x.FCStd", byte_count=1, sha256="deadbeef"
    )
    monkeypatch.setattr(cli, "export_fcstd", lambda *a, **k: artifact)


def test_run_build_threads_hard_chine_variant(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}
    _install_fake_build_chain(monkeypatch, calls)
    rc = cli.main(
        ["build", "--out", "x.FCStd", "--hull-variant", "hard_chine", "--no-propulsion"]
    )
    assert rc == 0
    assert calls["hull_variant"] == "hard_chine"


def test_run_build_defaults_hull_variant_to_standard(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}
    _install_fake_build_chain(monkeypatch, calls)
    rc = cli.main(["build", "--out", "x.FCStd", "--no-propulsion"])
    assert rc == 0
    assert calls["hull_variant"] == "standard"
