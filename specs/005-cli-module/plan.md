# Implementation Plan: CLI Module

**Branch**: `005-cli-module` | **Date**: 2026-05-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-cli-module/spec.md`

## Summary

Build `storebro.cli`. A single `main(argv)` function dispatches three subcommands via `argparse`: `build` (composes `build_hull → build_deck → build_interior → export_<format>`), `list-layouts` (reads the five canonical YAML fixtures), `info` (prints package + Python + FreeCAD + platform metadata). The CLI is the dependency-arrow apex — the only public module that imports all four prior modules. Errors translate to exit codes per FR-011 (1 = input error, 2 = system / FreeCAD error). The `--debug` flag (or `STOREBRO_DEBUG=1` env var) preserves the full Python traceback for bug reports. Both `storebro` (console script) and `python -m storebro` invoke the same entry point.

Technical approach: a single `src/storebro/cli.py` module plus a `src/storebro/__main__.py` shim. The console-script entry point lives in `pyproject.toml`'s `[project.scripts] storebro = "storebro.cli:main"`. `main(argv: list[str] | None = None) -> int` returns the exit code rather than calling `sys.exit`, making the CLI directly callable from unit tests without subprocess overhead.

## Technical Context

**Language/Version**: Python 3.11+.

**Primary Dependencies**: stdlib `argparse`, `platform`, `sys`, `os`. From storebro: `hull`, `deck`, `interior`, `export`, `_freecad_check`. No new third-party Python packages.

**Storage**: N/A. CLI is stateless.

**Testing**: pytest with the existing `unit` / `requires_freecad` markers. Unit tests call `main(argv)` directly and capture stdout/stderr via `capsys`. The `build` subcommand requires FreeCAD (it eventually loads spec 001-004 modules); `list-layouts` and `info` do not.

**Target Platform**: Same as prior specs.

**Project Type**: Python library + console script. Adds entry point + `__main__.py` shim.

**Performance Goals**: `list-layouts` < 1 s, `info` < 1 s, `build` < 3 minutes (SC-001 to SC-004).

**Constraints**:
- Non-interactive (FR-013). No prompts, no spinners.
- Plain text stdout / stderr (FR-012). No color codes.
- Imports all four prior public modules (FR-014). This is the dependency-arrow apex.
- Exit codes: 0 success, 1 input error, 2 system error (FR-005 + FR-011).
- Single public function `main(argv)` (FR-015). Rest is private.

**Scale/Scope**: Single Python module `src/storebro/cli.py` (~200-400 lines) + 5-line `src/storebro/__main__.py`. Public API: 1 function. Private helpers: ~10-15 (argparse builders, exit-code mapper, info-line formatter, error wrapping decorator, etc.). Test surface: ~30-50 tests focused on argparse behavior, error translation, output format.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|---|---|---|
| **I. Parametric Everything** | PASS | Every CLI option is a named argparse argument. No hidden defaults beyond the documented `--layout Alternativ3`, `--format fcstd`, `--tessellation 0.001`. |
| **II. Reproducibility (NON-NEGOTIABLE)** | PASS | `build` delegates byte determinism to spec 002. SC-005 verifies cross-invocation equality. |
| **III. FreeCAD-Idiomatic** | PASS | CLI does not directly call FreeCAD APIs — composes the four prior modules which handle FreeCAD. Zero `Mesh.Mesh` in the CLI module. |
| **IV. Reference Fidelity** | PASS | CLI defaults invoke the canonical RC34 1972 build (default hull + deck + Alternativ3 interior). |
| **V. Test-Gated Releases** | PASS | SC-006 (--help on each subcommand), SC-007 (≥8 invalid-input cases), SC-008 (single public function). Ruff + mypy CI-enforced. |
| **VI. Public OSS by Default** | PASS | MIT. Public API: 1 function. The `storebro` console script is the public-facing entry point. |
| **VII. FreeCAD Version Discipline** | PASS | `info` surfaces the supported range. `build` delegates the lazy version check to spec 001-004's shared `_freecad_check`. |

**Gates pass.**

## Project Structure

### Documentation (this feature)

```text
specs/005-cli-module/
├── plan.md
├── spec.md
├── spec.allium
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cli-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code

```text
src/storebro/
├── __init__.py             # Adds CLI re-export (main) to __all__
├── __main__.py             # NEW: `python -m storebro` shim → calls cli.main(sys.argv[1:])
├── hull.py                 # (spec 001)
├── _freecad_check.py       # (spec 001)
├── export.py               # (spec 002)
├── deck.py                 # (spec 003)
├── interior.py             # (spec 004)
├── fixtures/               # (spec 004 YAML fixtures)
└── cli.py                  # NEW: main() + argparse builders + subcommand handlers

tests/
├── unit/
│   ├── test_cli_argparse.py            # argparse structure, --help, exit code 2 for unknown
│   ├── test_cli_list_layouts.py        # list-layouts works without FreeCAD
│   ├── test_cli_info.py                # info works without FreeCAD
│   ├── test_cli_exit_codes.py          # exception → exit code mapping (FR-011)
│   ├── test_cli_debug_flag.py          # --debug + STOREBRO_DEBUG=1 behaviour
│   ├── test_cli_python_m_entry.py      # __main__.py exists + importable
│   └── test_cli_leaf_dependencies.py   # FR-014 imports all four prior modules
└── geometry/
    ├── test_cli_build_default.py       # storebro build --out /tmp/x.FCStd
    ├── test_cli_build_all_formats.py   # exhaustive --format coverage
    ├── test_cli_build_all_layouts.py   # exhaustive --layout coverage
    └── test_cli_build_visual_signoff.py # produces /tmp/storebro_v1_signoff.FCStd

docs/examples/
└── cli_quickstart.sh       # Shell script with the three subcommand invocations
```

**Structure Decision**: **single src-layout Python module + `__main__.py` shim + console-script entry point in pyproject.toml**. The `__main__.py` is 4 lines: import main from cli, call with sys.argv[1:], exit with its return code.

## Complexity Tracking

> No Constitution Check violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| — | — | — |
