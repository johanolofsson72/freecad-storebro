"""Unit test: argparse structure (T012, T013).

Covers FR-002 (unknown subcommand → exit 2), FR-010 (--help on every subcommand),
SC-006 (--help works for build, list-layouts, info), and edge-case exit codes
for missing required args and unknown formats.
"""

from __future__ import annotations

import pytest

from storebro.cli import main


@pytest.mark.parametrize(
    "argv",
    [
        ["--help"],
        ["build", "--help"],
        ["list-layouts", "--help"],
        ["info", "--help"],
    ],
)
def test_help_exits_zero_for_top_and_every_subcommand(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    """SC-006: --help is available on every subcommand and exits 0."""
    rc = main(argv)
    captured = capsys.readouterr()
    assert rc == 0, f"--help on {argv!r} should exit 0, got {rc}"
    assert "usage:" in captured.out


def test_unknown_subcommand_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    """FR-002: unknown subcommand → argparse exit 2."""
    rc = main(["frobnicate"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "usage" in captured.err.lower() or "invalid choice" in captured.err.lower()


def test_no_subcommand_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    """Missing subcommand → argparse exit 2 because subparsers is required=True."""
    rc = main([])
    captured = capsys.readouterr()
    assert rc == 2
    assert "usage" in captured.err.lower() or "required" in captured.err.lower()


def test_build_without_out_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    """FR-003: --out is required for build."""
    rc = main(["build"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "out" in captured.err.lower() or "required" in captured.err.lower()


def test_build_with_unknown_format_exits_two(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """FR-003: --format is restricted to {fcstd, step, stl, brep}."""
    rc = main(["build", "--out", "/tmp/x.fcstd", "--format", "txt"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "format" in captured.err.lower() or "invalid choice" in captured.err.lower()


def test_build_with_unknown_option_exits_two(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unknown option → argparse exit 2."""
    rc = main(["build", "--out", "/tmp/x.fcstd", "--bogus"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "unrecognized" in captured.err.lower() or "bogus" in captured.err.lower()
