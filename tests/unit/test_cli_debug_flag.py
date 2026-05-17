"""Unit test: --debug / STOREBRO_DEBUG=1 behavior (T015).

Covers FR-013a: the debug flag preserves Python tracebacks; without it,
exceptions surface as single-line `error: <msg>` on stderr per FR-011.
"""

from __future__ import annotations

import pytest

from storebro import cli
from storebro.cli import _strip_debug_flag, main


def test_strip_debug_flag_detects_flag_in_any_position() -> None:
    debug, rest = _strip_debug_flag(["--debug", "info"])
    assert debug is True
    assert rest == ["info"]


def test_strip_debug_flag_works_after_subcommand() -> None:
    debug, rest = _strip_debug_flag(["info", "--debug"])
    assert debug is True
    assert rest == ["info"]


def test_strip_debug_flag_absent_returns_false() -> None:
    debug, rest = _strip_debug_flag(["info"])
    assert debug is False
    assert rest == ["info"]


def test_strip_debug_flag_honors_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STOREBRO_DEBUG", "1")
    debug, rest = _strip_debug_flag(["info"])
    assert debug is True
    assert rest == ["info"]


def test_debug_flag_preserves_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """With --debug, an exception propagates instead of being swallowed."""

    def boom() -> int:
        raise RuntimeError("ka-boom")

    monkeypatch.setattr(cli, "_run_info", boom)
    with pytest.raises(RuntimeError, match="ka-boom"):
        main(["--debug", "info"])


def test_no_debug_flag_writes_error_line_and_returns_two(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without --debug, the exception is swallowed into a stderr error line."""

    def boom() -> int:
        raise RuntimeError("ka-boom")

    monkeypatch.setattr(cli, "_run_info", boom)
    rc = main(["info"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "error:" in captured.err
    assert "ka-boom" in captured.err
