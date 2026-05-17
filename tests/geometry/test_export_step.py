"""Geometry test: STEP writer end-to-end (T018).

Covers FR-001, FR-002, FR-016 (LF endings), FR-018 (creator sentinel),
SC-001, SC-002 (5s budget), SC-005.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

import FreeCAD  # type: ignore[import-not-found]
import pytest

from storebro import HullParameters, build_hull, export_step

HASH_FIXTURE = (
    Path(__file__).parent / "fixtures" / "expected_hashes.toml"
)


def _short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _baseline_key(fmt: str, kwargs: dict[str, object]) -> str:
    v = FreeCAD.Version()
    fc_key = f"{v[0]}_{v[1]}_{v[2]}"
    source_key = _short_hash(repr(HullParameters()))
    kwargs_key = _short_hash(json.dumps(kwargs, sort_keys=True))
    return f"{fmt}__{fc_key}__{source_key}__{kwargs_key}"


def _lookup_baseline(fmt: str, kwargs: dict[str, object]) -> str | None:
    if not HASH_FIXTURE.is_file():
        return None
    with HASH_FIXTURE.open("rb") as f:
        data = tomllib.load(f)
    return data.get(_baseline_key(fmt, kwargs), {}).get("sha256")


def test_export_step_round_trip(tmp_path: Path) -> None:
    hull = build_hull()
    out = tmp_path / "out.step"
    art = export_step(hull.body, out)

    assert art.format == "step"
    assert art.byte_count > 0
    assert 0.0 < art.build_duration_seconds < 5.0  # SC-002 STEP budget (A1)
    assert out.is_file()
    assert out.stat().st_size == art.byte_count


def test_export_step_lf_endings_only(tmp_path: Path) -> None:
    hull = build_hull()
    out = tmp_path / "lf.step"
    export_step(hull.body, out)
    payload = out.read_bytes()
    assert b"\r\n" not in payload, "FR-016: STEP MUST have LF endings only (A2)"


def test_export_step_creator_sentinel(tmp_path: Path) -> None:
    hull = build_hull()
    out = tmp_path / "sentinel.step"
    export_step(hull.body, out)
    payload = out.read_text(encoding="utf-8")
    assert "freecad-storebro" in payload, "FR-018: creator sentinel missing"
    # No user/hostname leak (best-effort heuristic).
    import getpass
    import socket

    user = getpass.getuser()
    host = socket.gethostname()
    assert user not in payload, "FR-004: STEP must not contain local user"
    assert host not in payload, "FR-004: STEP must not contain local hostname"


def test_export_step_iso_10303_magic(tmp_path: Path) -> None:
    hull = build_hull()
    out = tmp_path / "magic.step"
    export_step(hull.body, out)
    payload = out.read_bytes()
    assert payload.startswith(b"ISO-10303-21;"), "STEP magic header missing"


def test_export_step_matches_baseline(tmp_path: Path) -> None:
    expected = _lookup_baseline("step", {})
    if expected is None:
        pytest.skip(
            "no STEP baseline in expected_hashes.toml for this FreeCAD version; "
            "run tests/geometry/fixtures/refresh_hashes.py to seed"
        )

    hull = build_hull()
    out = tmp_path / "regression.step"
    art = export_step(hull.body, out)
    assert art.sha256 == expected, (
        f"STEP SHA-256 drift — got {art.sha256}, expected {expected}"
    )
