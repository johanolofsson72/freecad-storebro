"""Geometry test: storebro build is byte-deterministic (T021, SC-005).

Two back-to-back `storebro build` invocations with identical args must
produce identical SHA-256 digests. The CLI itself delegates the guarantee
to spec 002's writer (constitution principle II).

**v1.0.0 limitation**: marked xfail for FCStd format. FreeCAD maintains
process-global counters (Object IDs, UUIDs, timestamp, Topological-Naming
hex tag base) that advance across `main(["build", ...])` invocations even
when each builds in a fresh `FreeCAD.newDocument()`. Within-document
byte-determinism works (see `test_export_fcstd_determinism`). Cross-
invocation FCStd determinism is deferred to v1.1+ — spec.allium marker
`Fcstd.cross_invocation_byte_determinism`. STEP / STL / BREP exports are
unaffected and remain fully byte-deterministic.
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


@pytest.mark.xfail(
    reason=(
        "v1.0.0: cross-invocation FCStd byte determinism deferred. FreeCAD's "
        "process-global counters (Object IDs, UUIDs, save-timestamp) advance "
        "between two main() calls and the FCStd diff cannot be scrubbed "
        "without breaking the cross-reference graph (loader fails with "
        "'shape is invalid' or SIGABRT). Within-document and same-process "
        "STEP/STL/BREP determinism are unaffected. Tracked as "
        "Fcstd.cross_invocation_byte_determinism for v1.1+."
    ),
    strict=False,
)
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
