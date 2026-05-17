# Research: CLI Module (Phase 0)

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-05-17

---

## R1. CLI framework — argparse (stdlib)

### Decision

Use `argparse` from the Python standard library. No third-party CLI framework (Click, Typer, fire) for v1.0.

### Rationale

- 3 subcommands + ~5 options total — well within argparse's comfort zone.
- Stdlib means zero new dependencies. The project already added PyYAML in spec 004; another dep is unwarranted for a small CLI.
- `argparse` has predictable exit-code-2 behavior on argument errors, matching FR-011's distinction.
- Subcommand support via `add_subparsers(dest="subcommand")` is straightforward.

### Alternatives considered

- **Click**: more ergonomic but adds a dependency and brings its own help-text formatting conventions. Overkill at this CLI surface size.
- **Typer**: thin wrapper around Click + type hints. Same dependency objection.
- **Fire**: too magical (turns every function into a CLI). Hard to predict help text + exit codes.

---

## R2. Entry-point shape — `main(argv: list[str] | None = None) -> int`

### Decision

Top-level `main(argv: list[str] | None = None) -> int`. When `argv` is `None`, defaults to `sys.argv[1:]`. Returns the exit code instead of calling `sys.exit`. The console-script entry point and `__main__.py` both call `sys.exit(main())`.

### Rationale

- Returning an int is testable: `assert main(["info"]) == 0` works from a unit test without subprocess overhead.
- Default `argv=None` keeps the production invocation simple (`sys.exit(main())`).
- Matches how Python's own stdlib CLIs (`unittest.main`, `pytest.main`) work.

### Alternatives considered

- **`main()` calls `sys.exit` internally**: rejected — makes unit testing require `pytest.raises(SystemExit)` boilerplate.
- **`main()` returns nothing, separate `_dispatch()` returns int**: rejected — split adds indirection without benefit at this size.

---

## R3. Exit-code taxonomy (FR-011)

### Decision

```
0 = success
1 = input error (HullParameterError, DeckParameterError, InteriorParameterError, ExportInputError)
2 = system / FreeCAD / filesystem error (HullConstructionError, DeckConstructionError, InteriorConstructionError, ExportWriteError, KeyboardInterrupt)
2 = argparse argument error (argparse default — matches "bad input from user")
```

The overlap of code 2 between "argparse rejected" and "FreeCAD failed" is intentional. From the user's POV, both mean "your command can't run as written" — the message on stderr distinguishes the cause.

Implementation: a small dispatch table in `cli.py`:

```python
_INPUT_ERRORS = (
    HullParameterError, DeckParameterError, InteriorParameterError, ExportInputError,
)
_SYSTEM_ERRORS = (
    HullConstructionError, DeckConstructionError, InteriorConstructionError, ExportWriteError,
)

def _exit_code_for(exc: BaseException) -> int:
    if isinstance(exc, _INPUT_ERRORS):
        return 1
    if isinstance(exc, _SYSTEM_ERRORS):
        return 2
    return 2  # default for unexpected exceptions
```

### Rationale

- Code 1 vs code 2 lets shell scripts differentiate `if [ $? -eq 1 ]; then echo "fix your args"`. The convention follows POSIX-ish norms where 1 is generic failure and 2 is misuse.
- Argparse's default-2-for-arg-errors meshes with FR-005 + FR-011 without special handling.

### Alternatives considered

- **Distinct exit codes per exception class** (e.g., 10 for hull, 20 for deck, 30 for interior, 40 for export): rejected — exit-code namespace is small (0-255 effective); shell scripts rarely branch on >3 values. Aggregating into input vs system is more useful.

---

## R4. `list-layouts` description source

### Decision

`list-layouts` reads each canonical fixture via spec 004's `_load_layout(name)` (which uses `importlib.resources`), pulls `layout_name` and `source` fields from the YAML, and prints one tab-separated line per layout in fixed order:

```
Alternativ1	docs/references/Alternativ1.JPG	4 compartments — live-aboard
Alternativ2	docs/references/Alternativ2.JPG	4 compartments — fly-bridge access
Alternativ3	docs/references/Alternativ3.JPG	4 compartments — canonical RC34
Alternativ4	docs/references/Alternativ4.JPG	4 compartments — extended salon
Alternativ5	docs/references/Alternativ5.JPG	3 compartments — day-cruiser
```

The third column is a hand-curated one-line description harvested from the YAML's `compartments[*].description` fields plus the first compartment count. Built deterministically; no localization.

### Rationale

- Single source of truth — the YAML files. Editing a YAML to change the description automatically flows to `list-layouts`.
- Tab-separated output is parseable by `awk -F'\t' '{print $1}'` for scripting users.

### Alternatives considered

- **Hard-code descriptions in `cli.py`**: rejected — duplicates info that lives in the YAML.
- **Pretty-printed multi-line per layout**: rejected — harder to parse in shell scripts (FR-012's "no terminal-only output" implies machine-friendly default).

---

## R5. `--debug` flag handling (clarify Q3)

### Decision

```python
def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    debug = "--debug" in argv or os.environ.get("STOREBRO_DEBUG") == "1"
    if "--debug" in argv:
        argv.remove("--debug")  # strip before passing to argparse subparsers
    try:
        return _dispatch(argv)
    except BaseException as exc:
        if debug:
            raise  # preserve full Python traceback
        sys.stderr.write(f"error: {exc}\n")
        return _exit_code_for(exc)
```

The `--debug` flag is stripped before reaching argparse's subcommand parser (it's a global flag, not subcommand-specific). The env var works identically.

### Rationale

- Pre-argparse stripping keeps `--debug` valid in any position (`storebro --debug build ...` and `storebro build --debug ...` both work).
- Environment-variable activation makes "always debug in this shell" a one-liner: `export STOREBRO_DEBUG=1`.
- Re-raising preserves the FULL traceback including any chained `__cause__` exceptions — useful for bug reports.

### Alternatives considered

- **Argparse-handled `--debug`**: rejected — argparse parses subcommand-first by default, so a `--debug` after the subcommand is treated as a subcommand flag. Pre-stripping avoids needing to add the flag to every subparser.
- **Verbosity-level flag (`-v`, `-vv`)**: rejected — no intermediate level between "clean error" and "full traceback" makes sense for this surface size.

---

## R6. Testing strategy

### Decision

- **Unit tier** (`tests/unit/test_cli_*.py`): direct `main(argv)` calls, `capsys` for stdout/stderr capture, no subprocess. Covers argparse structure, list-layouts (reads fixtures — needs only stdlib), info (no FreeCAD branch), exit-code mapping, --debug flag behaviour, leaf-dependencies (AST scan).
- **Geometry tier** (`tests/geometry/test_cli_*.py`): direct `main(argv)` calls but use the `requires_freecad` marker because the underlying `build_hull/build_deck/build_interior/export_*` need FreeCAD. Cover `build` smoke (default), `--format` exhaustively, `--layout` exhaustively for canonical names, visual signoff.

No subprocess-based tests — direct `main(argv)` is faster and gives better stack traces on failure. The `__main__.py` shim is tested by a separate unit test that imports `storebro.__main__` and asserts it has the expected attributes.

### Rationale

- Direct `main()` calls are ~100x faster than subprocess and give nicer error messages.
- The FR-015 contract (returning int) makes this style possible.

### Alternatives considered

- **Subprocess tests for everything**: rejected — slow, opaque on failure, hides the call-site stack trace.
- **Mix of subprocess + direct**: rejected — keep the suite uniform.

---

## R7. `__main__.py` shim

### Decision

```python
# src/storebro/__main__.py
"""`python -m storebro` entry point — delegates to storebro.cli:main."""
import sys
from storebro.cli import main

if __name__ == "__main__":
    sys.exit(main())
```

### Rationale

Standard Python convention. Identical behavior to the console script.

### Alternatives considered

- **No `__main__.py` (only console script)**: rejected — clarify Q1 chose to support `python -m storebro`.
- **`__main__.py` containing the full CLI logic**: rejected — keep the logic in `cli.py` for testability; `__main__.py` is a tiny redirector.

---

## R8. README / docs updates (FR-017)

### Decision

`README.md`'s Quickstart section becomes the CLI invocation:

```bash
pip install freecad-storebro

# Build the canonical Storebro:
storebro build --out boat.FCStd

# Then open boat.FCStd in FreeCAD.
```

The current Python-only quickstart becomes a secondary "Python API" section.

### Rationale

CLI is the most-accessible entry point for non-Python users. Putting it first in the README matches the project's stated audience (restorers, scale modelers, students).

### Alternatives considered

- **Keep Python quickstart first**: rejected — the project's audience per PROJECT-BRIEF skews to non-developers.

---

## Summary of decisions

| ID | Decision | Resolves |
|---|---|---|
| R1 | stdlib `argparse` (no Click/Typer) | FR-002 / scope simplicity |
| R2 | `main(argv) -> int`, defaults to `sys.argv[1:]` | FR-015 |
| R3 | Exit-code dispatch table (1=input, 2=system) | FR-011 |
| R4 | `list-layouts` reads fixture YAML for description text | FR-007 |
| R5 | `--debug` stripped pre-argparse; STOREBRO_DEBUG=1 also activates | FR-013a |
| R6 | Direct `main(argv)` calls in tests (no subprocess) | SC-006/007/008 |
| R7 | 4-line `__main__.py` redirector to `cli.main` | FR-001 / clarify Q1 |
| R8 | README Quickstart leads with CLI | FR-017 |

All NEEDS CLARIFICATION resolved.
