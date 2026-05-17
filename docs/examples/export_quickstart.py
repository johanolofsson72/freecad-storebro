"""Runnable example: storebro.export quickstart.

Mirrors the first three sections of `specs/002-export-module/quickstart.md`.
Requires FreeCAD 1.1+ on PATH.

Run with:
    uv run python docs/examples/export_quickstart.py
"""

from __future__ import annotations

from storebro import (
    build_hull,
    export_brep,
    export_fcstd,
    export_step,
    export_stl,
)


def main() -> None:
    # 1) Build the default hull and export to all four formats.
    hull = build_hull()

    artifacts = [
        export_step(hull.body, "/tmp/storebro.step"),
        export_stl(hull.body, "/tmp/storebro.stl"),
        export_brep(hull.body, "/tmp/storebro.brep"),
        export_fcstd(hull.document, "/tmp/storebro.FCStd"),
    ]

    for art in artifacts:
        print(
            f"{art.format:6} {art.byte_count:>10} bytes  {art.sha256[:12]}... "
            f"({art.build_duration_seconds:.2f}s)"
        )

    # 2) Determinism check (constitution II checkpoint).
    a = export_step(hull.body, "/tmp/run_a.step")
    b = export_step(hull.body, "/tmp/run_b.step")
    assert a.sha256 == b.sha256, "byte determinism broken — FILE A BUG"
    print(f"\nSHA-256 stable across two STEP runs: {a.sha256[:12]}...")

    # 3) Custom tessellation — coarse vs default vs fine.
    coarse = export_stl(
        hull.body, "/tmp/coarse.stl", tessellation_tolerance=0.005
    )
    default = export_stl(hull.body, "/tmp/default.stl")
    fine = export_stl(
        hull.body, "/tmp/fine.stl", tessellation_tolerance=0.0001
    )
    print(
        f"\nSTL coarse {coarse.byte_count} bytes  <  "
        f"default {default.byte_count} bytes  <  "
        f"fine {fine.byte_count} bytes"
    )


if __name__ == "__main__":
    main()
