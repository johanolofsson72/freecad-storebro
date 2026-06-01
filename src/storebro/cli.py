"""Command-line interface for freecad-storebro.

Public API:
    main(argv: list[str] | None = None) -> int

The CLI is the dependency-arrow apex (FR-014): it imports all four prior public
modules (hull, deck, interior, export) and composes them into the three
subcommands `build`, `list-layouts`, and `info`. Returning an int from
``main`` (instead of calling ``sys.exit``) keeps the CLI testable via direct
function calls — see :mod:`storebro.__main__` for the process entry point.

Example:
    >>> from storebro.cli import main
    >>> # exit_code = main(["info"])
    >>> # sys.exit(exit_code)
"""

from __future__ import annotations

import argparse
import os
import platform
import sys

import yaml

from storebro._freecad_check import _read_supported_range_from_pyproject
from storebro.deck import (
    DeckConstructionError,
    DeckParameterError,
    build_deck,
)
from storebro.export import (
    ExportArtifact,
    ExportInputError,
    ExportWriteError,
    export_brep,
    export_fcstd,
    export_step,
    export_stl,
)
from storebro.hull import (
    HullConstructionError,
    HullParameterError,
    build_hull,
)
from storebro.interior import (
    InteriorConstructionError,
    InteriorParameterError,
    build_interior,
)
from storebro.propulsion import (
    PropulsionConstructionError,
    PropulsionParameterError,
    PropulsionParameters,
    build_propulsion,
)

__all__ = ["main"]


# ---------------------------------------------------------------------------
# Exit-code dispatch (data-model §2; FR-005 + FR-011)
# ---------------------------------------------------------------------------

_INPUT_ERROR_TYPES: tuple[type[BaseException], ...] = (
    HullParameterError,
    DeckParameterError,
    InteriorParameterError,
    PropulsionParameterError,
    ExportInputError,
)

_SYSTEM_ERROR_TYPES: tuple[type[BaseException], ...] = (
    HullConstructionError,
    DeckConstructionError,
    InteriorConstructionError,
    PropulsionConstructionError,
    ExportWriteError,
)

_CANONICAL_LAYOUT_ORDER: tuple[str, ...] = (
    "Alternativ1",
    "Alternativ2",
    "Alternativ3",
    "Alternativ4",
    "Alternativ5",
)

_VALID_FORMATS: tuple[str, ...] = ("fcstd", "step", "stl", "brep")


def _exit_code_for(exc: BaseException) -> int:
    """Map an exception to its CLI exit code per FR-011."""
    if isinstance(exc, _INPUT_ERROR_TYPES):
        return 1
    if isinstance(exc, _SYSTEM_ERROR_TYPES):
        return 2
    return 2


# ---------------------------------------------------------------------------
# Argument parsing (FR-002 + FR-003 + FR-010)
# ---------------------------------------------------------------------------


def _build_top_parser() -> argparse.ArgumentParser:
    """Construct the argparse top-level parser with three subcommands."""
    parser = argparse.ArgumentParser(
        prog="storebro",
        description=("Build a parametric Storebro Royal Cruiser 34 1972 model in FreeCAD."),
    )
    subparsers = parser.add_subparsers(
        dest="subcommand",
        required=True,
        metavar="{build,list-layouts,info}",
    )

    build_p = subparsers.add_parser(
        "build",
        help="Compose hull + deck + interior and write to the chosen format.",
    )
    build_p.add_argument(
        "--layout",
        default="Alternativ3",
        help=(
            "Layout name (Alternativ1-Alternativ5) or path to a custom YAML. Default: Alternativ3."
        ),
    )
    build_p.add_argument(
        "--out",
        required=True,
        help="Destination file path.",
    )
    build_p.add_argument(
        "--format",
        choices=_VALID_FORMATS,
        default="fcstd",
        help="Output format. Default: fcstd.",
    )
    build_p.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Refuse to overwrite an existing target file (default: overwrite).",
    )
    build_p.add_argument(
        "--tessellation",
        type=float,
        default=0.001,
        help="STL tessellation tolerance in meters (only meaningful for --format stl). Default: 0.001.",
    )
    build_p.add_argument(
        "--engine-count",
        type=int,
        choices=(1, 2),
        default=2,
        help="Propulsion layout: 1 (single screw) or 2 (twin screws). Default: 2.",
    )
    build_p.add_argument(
        "--no-propulsion",
        action="store_true",
        help="Skip the propulsion step (hull + deck + interior only).",
    )

    subparsers.add_parser(
        "list-layouts",
        help="List the five canonical interior layouts shipped with the package.",
    )
    subparsers.add_parser(
        "info",
        help="Print package, Python, FreeCAD, and platform metadata.",
    )

    return parser


def _strip_debug_flag(argv: list[str]) -> tuple[bool, list[str]]:
    """Detect the global --debug flag and remove it from argv before argparse sees it.

    Honors STOREBRO_DEBUG=1 as an equivalent activation.
    """
    debug = "--debug" in argv or os.environ.get("STOREBRO_DEBUG") == "1"
    cleaned = [a for a in argv if a != "--debug"]
    return debug, cleaned


# ---------------------------------------------------------------------------
# Subcommand handlers (FR-006, FR-007, FR-009)
# ---------------------------------------------------------------------------


def _run_info() -> int:
    """Print key-value metadata lines per FR-009 + data-model §5."""
    from storebro import __version__

    print(f"freecad-storebro version: {__version__}")
    print(f"Python version: {platform.python_version()}")
    print(f"Platform: {platform.system()} {platform.machine()}")

    try:
        import FreeCAD

        raw = FreeCAD.Version()
        major, minor, patch = int(raw[0]), int(raw[1]), int(raw[2])
        print(f"FreeCAD detected: {major}.{minor}.{patch}")
    except (ImportError, IndexError, ValueError, TypeError):
        print("FreeCAD detected: not detected")

    range_literal, _, _ = _read_supported_range_from_pyproject()
    print(f"FreeCAD supported range: {range_literal}")
    return 0


def _layout_description(raw: dict[str, object]) -> str:
    """Build a one-line description from a parsed layout YAML."""
    source = str(raw.get("source", "(no source)"))
    compartments = raw.get("compartments", [])
    count = len(compartments) if isinstance(compartments, list) else 0
    return f"{count} compartments\t{source}"


def _run_list_layouts() -> int:
    """List the five canonical layouts per FR-007 + research.md R4."""
    import importlib.resources

    for name in _CANONICAL_LAYOUT_ORDER:
        fixture_path = importlib.resources.files("storebro.fixtures") / f"{name}.yaml"
        text = fixture_path.read_text(encoding="utf-8")
        raw = yaml.safe_load(text) or {}
        print(f"{name}\t{_layout_description(raw)}")
    return 0


def _run_build(args: argparse.Namespace) -> int:
    """Compose hull + deck + interior + export per FR-004 + FR-006."""
    overwrite = not args.no_overwrite

    # Always build in a fresh FreeCAD document so two consecutive CLI
    # invocations produce byte-identical output (SC-005 / constitution II).
    # Without this the second `storebro build` reuses the first's active
    # document and ends up emitting both hulls in the same FCStd.
    import FreeCAD

    fresh_doc = FreeCAD.newDocument("storebro_build")
    hull = build_hull(document=fresh_doc)
    deck = build_deck(hull)
    build_interior(hull, deck, layout=args.layout)
    if not args.no_propulsion:
        # A single-screw layout is centred (offset 0); twin uses the default offset.
        propulsion_params = (
            PropulsionParameters(engine_count=1, engine_offset_y_mm=0.0)
            if args.engine_count == 1
            else PropulsionParameters(engine_count=2)
        )
        build_propulsion(hull, deck, parameters=propulsion_params)

    artifact: ExportArtifact
    fmt = args.format
    if fmt == "fcstd":
        artifact = export_fcstd(hull.document, args.out, overwrite=overwrite)
    elif fmt == "step":
        artifact = export_step(hull.body, args.out, overwrite=overwrite)
    elif fmt == "brep":
        artifact = export_brep(hull.body, args.out, overwrite=overwrite)
    else:
        assert fmt == "stl"
        artifact = export_stl(
            hull.body,
            args.out,
            overwrite=overwrite,
            tessellation_tolerance=args.tessellation,
        )

    print(
        f"wrote {artifact.format} to {artifact.target_path} "
        f"({artifact.byte_count} bytes, SHA-256 {artifact.sha256})"
    )
    return 0


# ---------------------------------------------------------------------------
# Entry point (FR-015)
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run the storebro CLI and return its exit code.

    Args:
        argv: Argument list (without program name). When None, uses ``sys.argv[1:]``.

    Returns:
        0 on success; 1 for input errors; 2 for system / FreeCAD failures.

    Example:
        >>> # from storebro.cli import main
        >>> # sys.exit(main(["info"]))
    """
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    debug, cleaned = _strip_debug_flag(raw_argv)

    parser = _build_top_parser()
    try:
        args = parser.parse_args(cleaned)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    try:
        if args.subcommand == "build":
            return _run_build(args)
        if args.subcommand == "list-layouts":
            return _run_list_layouts()
        assert args.subcommand == "info"
        return _run_info()
    except BaseException as exc:
        if debug:
            raise
        if isinstance(exc, SystemExit):
            return int(exc.code) if isinstance(exc.code, int) else 2
        sys.stderr.write(f"error: {exc}\n")
        return _exit_code_for(exc)
