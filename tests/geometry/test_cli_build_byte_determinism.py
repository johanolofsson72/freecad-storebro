"""Geometry test: storebro build is byte-deterministic (T021, SC-005).

Two back-to-back `storebro build` invocations with identical args must
produce identical SHA-256 digests. The CLI itself delegates the guarantee
to spec 002's writer (constitution principle II).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from storebro.cli import main

pytestmark = pytest.mark.requires_freecad


SUMMARY_PATTERN = re.compile(r"SHA-256 (?P<hash>[0-9a-f]{64})")


def _extract_hash(stdout: str) -> str:
    match = SUMMARY_PATTERN.search(stdout)
    assert match is not None, f"no SHA-256 in stdout: {stdout!r}"
    return match.group("hash")


def test_storebro_build_byte_deterministic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """SC-005: same args → identical hash on two consecutive invocations."""
    out_a = tmp_path / "a.FCStd"
    out_b = tmp_path / "b.FCStd"

    rc_a = main(["build", "--out", str(out_a)])
    captured_a = capsys.readouterr()
    assert rc_a == 0, captured_a.err
    hash_a = _extract_hash(captured_a.out)

    rc_b = main(["build", "--out", str(out_b)])
    captured_b = capsys.readouterr()
    assert rc_b == 0, captured_b.err
    hash_b = _extract_hash(captured_b.out)

    assert hash_a == hash_b, (
        f"SC-005 violation: hashes differ between identical builds — a={hash_a!r}, b={hash_b!r}"
    )
    assert out_a.read_bytes() == out_b.read_bytes(), (
        "SC-005 violation: byte contents differ between identical builds"
    )
