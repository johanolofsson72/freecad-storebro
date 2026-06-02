"""Spec 009 T034 — CLI flag set must match v1.0.2 (no new flags).

Spec 009 FR-017 + clarification 3: ``station_count`` and ``bilge_radius`` are
NOT exposed as CLI flags in v1.0.3. They are advanced ``HullParameters`` knobs
only. This test guards against silent CLI surface growth in future PRs.
"""

from __future__ import annotations

from storebro.cli import _build_top_parser as build_parser

# Frozen v1.0.2 flag baseline. Captured from the parser as it stood at the
# spec 008 closure tag (v1.0.2). Update this set ONLY when a CLI flag change
# is explicitly approved via a new spec — and cite the spec ID in the change.
V1_0_2_FLAG_SET: frozenset[str] = frozenset(
    {
        "--help",
        "--version",
        "--debug",
        "--quiet",
        "--verbose",
        "--layout",
        "--output",
        "--out",
        "--name",
        "--no-recompute",
        "--format",
        "--no-overwrite",
        "--tessellation",
        # spec 014 (propulsion) FR-011: the build command composes propulsion
        # and exposes the one meaningful layout choice + an opt-out.
        "--engine-count",
        "--no-propulsion",
        # spec 015 (render-attributes) FR-008: global opt-out of cosmetic colours.
        "--no-colors",
    }
)


def _collect_flags(parser_or_subparser: object) -> set[str]:
    """Walk an argparse parser and collect every long-form option string."""
    flags: set[str] = set()
    actions = getattr(parser_or_subparser, "_actions", [])
    for action in actions:
        for opt in getattr(action, "option_strings", []):
            if opt.startswith("--"):
                flags.add(opt)
        # Recurse into subparsers (the storebro CLI exposes "build" etc.)
        if hasattr(action, "choices") and isinstance(action.choices, dict):
            for sub in action.choices.values():
                flags |= _collect_flags(sub)
    return flags


def test_cli_flag_set_does_not_introduce_station_count_flag() -> None:
    parser = build_parser()
    flags = _collect_flags(parser)
    assert "--station-count" not in flags
    assert "--stations" not in flags


def test_cli_flag_set_does_not_introduce_bilge_radius_flag() -> None:
    parser = build_parser()
    flags = _collect_flags(parser)
    assert "--bilge-radius" not in flags
    assert "--bilge" not in flags


def test_cli_flag_set_is_subset_of_v102_baseline() -> None:
    """Every flag in v1.0.3 must have existed in v1.0.2 — no silent additions.

    If this test fails, either (a) a spec authorized the new flag and this
    baseline list should be updated, or (b) a CLI flag was added by mistake
    and should be removed.
    """
    parser = build_parser()
    flags = _collect_flags(parser)
    surplus = flags - V1_0_2_FLAG_SET
    assert not surplus, (
        f"CLI exposes flags not in the v1.0.2 baseline: {sorted(surplus)}. "
        "Either update V1_0_2_FLAG_SET (with a spec citation) or remove the flags."
    )
