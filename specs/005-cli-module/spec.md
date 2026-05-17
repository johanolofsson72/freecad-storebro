# Feature Specification: CLI Module

**Feature Branch**: `005-cli-module`

**Created**: 2026-05-17

**Status**: Draft

**Input**: User description: "the CLI module — storebro build/list-layouts/info commands composing hull + deck + interior + export"

## Clarifications

### Session 2026-05-17

- Q: Should the CLI also be invokable via `python -m storebro`? → A: **Yes**. Ship a `src/storebro/__main__.py` that imports `main` from `storebro.cli` and runs it. Both the `storebro` console-script entry point (per FR-001) and `python -m storebro` invoke the same `main(argv)` function. Useful for environments where the console script isn't on PATH but Python is.
- Q: Should `storebro info` include operating system and architecture lines? → A: **Yes**. Add `Platform` (from `platform.system()` + `platform.machine()`) to the key-value output. Free metadata; useful for bug reports.
- Q: Should the CLI accept a `--debug` / `--traceback` flag that surfaces Python tracebacks instead of one-line `error: <message>`? → A: **Yes, opt-in `--debug` flag**. Default is the clean `error: <message>` line on stderr per FR-011. `--debug` (or `STOREBRO_DEBUG=1` env var) preserves the original Python traceback for bug reports. The flag is global (works on every subcommand).
- Q: Should `storebro build --out` auto-create the parent directory if it doesn't exist? → A: **No**. Maintains the existing Edge Cases behavior — missing parent directory is an `ExportInputError` from spec 002 surfacing as exit code 1. The shell convention is `mkdir -p` first; auto-creating silently surprises users with deeply-nested typos.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Boat restorer generates a complete model with one command (Priority: P1)

A boat restorer who knows their way around a terminal but not around Python wants to generate a full Storebro Royal Cruiser 34 1972 model — hull, deck, and one of the canonical interiors — and save it as a `.FCStd` file they can open in FreeCAD. They run a single command (`storebro build --layout Alternativ3 --out boat.FCStd`) and get back a working file. No Python REPL, no `import` statements, no docstrings to parse.

**Why this priority**: This is the project's most-accessible entrypoint. The four prior specs are libraries — they require Python to use. This spec is the only path for users who want output without writing code. It is also the path the project's README will point to first; without it, the README's "Quickstart" section is a Python script and the audience narrows to programmers.

**Independent Test**: From a shell with FreeCAD on PATH and `freecad-storebro` installed, run `storebro build --layout Alternativ3 --out /tmp/boat.FCStd`. Verify the command exits with code 0, the file exists, and opening it in the FreeCAD GUI shows the hull + deck + 4-compartment interior. Re-running the same command produces a byte-identical file (constitution II via spec 002's writer).

**Acceptance Scenarios**:

1. **Given** a shell with FreeCAD on PATH and the package installed, **When** the user runs `storebro build --out /tmp/boat.FCStd`, **Then** the command exits with code 0 and `/tmp/boat.FCStd` is a valid FreeCAD document containing the default hull, default deck, and the canonical (Alternativ3) interior.
2. **Given** the same setup, **When** the user runs `storebro build --layout Alternativ1 --out /tmp/boat1.FCStd`, **Then** the resulting document uses the Alternativ1 interior instead.
3. **Given** an invalid layout name, **When** the user runs `storebro build --layout BogusLayout --out /tmp/x.FCStd`, **Then** the command exits with a non-zero code and prints a clear error message naming the offending argument and listing the valid layout names.

---

### User Story 2 - User discovers what layouts ship with the project (Priority: P2)

A user installs the package and wants to know what layouts are available without reading the source or the documentation. They run `storebro list-layouts` and get a clean, scannable list of the five canonical layout names with one-line descriptions of each.

**Why this priority**: Discoverability for a data-driven feature. Without this, users have to guess layout names or open YAML files to read them. This makes the `--layout` argument's help text concretely useful instead of "pass one of five canonical names".

**Independent Test**: Run `storebro list-layouts`. Verify exit code 0 and that stdout contains all five canonical names (`Alternativ1` through `Alternativ5`) with a one-line description per layout.

**Acceptance Scenarios**:

1. **Given** the package installed, **When** the user runs `storebro list-layouts`, **Then** the command prints all five canonical layout names with their source citation, each on its own line, in the documented order (Alternativ1 through Alternativ5), and exits with code 0.

---

### User Story 3 - Diagnostic info for support and scripts (Priority: P3)

A user reporting a bug — or a CI script logging what produced an artifact — wants to print the installed package version, the FreeCAD version detected on the system, and the supported FreeCAD version range. They run `storebro info` and get one or two lines per fact, parseable enough for `grep`.

**Why this priority**: Standard hygiene for any CLI tool. Without it, users embed library-version assumptions in their scripts or open support tickets that don't include the version they ran. With it, "what version are you on?" becomes self-serve.

**Independent Test**: Run `storebro info`. Verify exit code 0 and that stdout contains the package version, the detected FreeCAD version (or a clear "not installed" message), and the supported FreeCAD range from `pyproject.toml`.

**Acceptance Scenarios**:

1. **Given** the package installed with FreeCAD on PATH, **When** the user runs `storebro info`, **Then** stdout contains lines naming `freecad-storebro` version, the detected FreeCAD version, and the supported FreeCAD range, in a fixed key-value format. Exit code is 0.
2. **Given** the package installed WITHOUT FreeCAD on PATH, **When** the user runs `storebro info`, **Then** the FreeCAD line reads `FreeCAD: not detected` and the command still exits with code 0 (info is allowed to report partial state).

---

### Edge Cases

- **No arguments at all** (`storebro`): print usage / help, exit code 0 (standard `argparse` behavior).
- **Unknown subcommand** (`storebro frobnicate`): print error + usage, exit code 2 (the standard argparse exit code for arg errors).
- **`build` without `--out`**: print error and exit code 2 — `--out` is required because the command's whole purpose is to write a file. No silent default to `./boat.FCStd`.
- **`build --out` points at an existing file**: by default the writer overwrites (matches spec 002's `overwrite=True` default). User can pass `--no-overwrite` to refuse, in which case the command exits with a non-zero code citing the existing path.
- **`build --out` parent directory does not exist**: command exits with non-zero code naming the missing parent (spec 002's `ExportInputError` is surfaced). The CLI does NOT auto-create parent directories (clarify Q4) — users run `mkdir -p` first.
- **`build --out` extension does not match the chosen format**: command exits with non-zero code citing the mismatch (spec 002's validation).
- **`build --format` value is unknown**: argparse rejects with exit code 2 listing the accepted formats.
- **`build --layout` points at a YAML file that fails schema validation**: command exits with non-zero code and prints the `InteriorParameterError` from spec 004, citing the YAML source and offending compartment / field.
- **FreeCAD is not installed**: any `build` invocation exits with a non-zero code citing the missing FreeCAD; `list-layouts` and `info` work fine (they don't need FreeCAD).
- **Unsupported FreeCAD version**: `build` exits with a non-zero code citing the detected version and the supported range.
- **`Ctrl-C` mid-build**: standard Python `KeyboardInterrupt` propagates; the underlying module's rollback discipline (spec 003 + 004) leaves any FreeCAD document in a clean state if the user interrupts before the writer succeeds.
- **Stdout piped to a non-terminal**: the CLI MUST NOT use color codes, progress spinners, or other terminal-only output by default. Output is plain text suitable for piping into other tools.
- **`--help` / `-h` on any subcommand**: print usage for that subcommand and exit code 0. Standard argparse behavior.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The package MUST install a console script named `storebro` (the canonical project name) that becomes available on the user's PATH after `pip install freecad-storebro` (or equivalent). The CLI MUST also be invokable via `python -m storebro` (clarify Q1) — both forms call the same `main(argv)` function with the same argument schema.
- **FR-002**: The `storebro` console script MUST support exactly three subcommands in v1.0: `build`, `list-layouts`, and `info`. Other subcommands MUST cause argparse to exit with code 2 and a usage message.
- **FR-003**: `storebro build` MUST accept the following options:
    - `--layout NAME` (default `Alternativ3`): one of the five canonical names or a path to a user-supplied YAML layout file. Passed through to `build_interior` from spec 004.
    - `--out PATH` (required): destination file for the exported artifact.
    - `--format FORMAT` (default `fcstd`): one of `fcstd`, `step`, `stl`, `brep`. Selects which spec 002 writer to call.
    - `--no-overwrite` (flag, default off): refuse to overwrite an existing target file (delegates to spec 002's `overwrite=False`).
    - `--tessellation METERS` (default `0.001`): only meaningful for `--format stl`; passes through to spec 002's `tessellation_tolerance`.
- **FR-004**: `storebro build` MUST compose the four prior modules in this order: (a) `build_hull()` with default parameters, (b) `build_deck(hull)` with default parameters, (c) `build_interior(hull, deck, layout=<arg>)`, (d) export with the writer matching `--format`:
    - `--format fcstd` → `export_fcstd(hull.document, target_path, ...)` — the document contains hull + deck + interior bodies, so the `.FCStd` is the full assembly.
    - `--format step` / `--format brep` / `--format stl` → `export_<format>(hull.body, target_path, ...)` — single-body B-rep export of the hull only. Deck and interior are still built (so spec 003/004 errors still surface) but NOT included in the exported solid; CAD-interchange formats consume the canonical hull surface. Documented limitation: exporting the full assembly to STEP/BREP/STL is deferred to v1.1+ (compound assembly export — see deferred markers in `spec.allium`).
    The composition order matters because each module's output is the next module's input, and because the build pipeline catches deck/interior errors regardless of the chosen export format.
- **FR-005**: `storebro build` MUST exit with code 0 on success and a non-zero code on any failure. The error message MUST go to stderr; the success summary (path, sha256, bytes) goes to stdout.
- **FR-006**: `storebro build` MUST print a one-line success summary to stdout on exit code 0: `wrote <format> to <abs_path> (<byte_count> bytes, SHA-256 <hash>)`.
- **FR-007**: `storebro list-layouts` MUST print all five canonical layout names from spec 004's `_CANONICAL_LAYOUT_NAMES`, in the documented order (`Alternativ1` through `Alternativ5`), each on its own line, with a tab-separated one-line description from the layout's YAML `source` or a hand-curated short description.
- **FR-008**: `storebro list-layouts` MUST exit with code 0 and write to stdout. It MUST NOT require FreeCAD (it only reads the YAML fixtures).
- **FR-009**: `storebro info` MUST print key-value lines for `freecad-storebro version` (from `__version__`), `Python version` (`platform.python_version()`), `Platform` (`platform.system()` + space + `platform.machine()`, per clarify Q2), `FreeCAD detected` (either the major.minor.patch from `FreeCAD.Version()` or `not detected`), and `FreeCAD supported range` (from `pyproject.toml`'s `[tool.freecad-storebro]` table). It MUST exit with code 0 even when FreeCAD is not detected.
- **FR-010**: All three subcommands MUST honor `--help`/`-h` per argparse conventions (exit code 0, print usage).
- **FR-011**: The CLI MUST surface module-level exceptions cleanly: `HullParameterError`, `DeckParameterError`, `InteriorParameterError`, `ExportInputError` cause exit code 1 with `error: <message>` on stderr; `HullConstructionError`, `DeckConstructionError`, `InteriorConstructionError`, `ExportWriteError` cause exit code 2 with `error: <message>` on stderr. The distinction between exit codes is: code 1 = user supplied bad input, code 2 = system / FreeCAD / filesystem failure.
- **FR-012**: The CLI MUST NOT print color codes, progress spinners, or terminal-only output by default. Pipelining `storebro build ... | tee log.txt` MUST work cleanly.
- **FR-013**: The CLI MUST NOT prompt for user input. All inputs are command-line arguments. The CLI is non-interactive (suitable for CI / scripting use).
- **FR-013a**: The CLI MUST support a global `--debug` flag (also activatable via the `STOREBRO_DEBUG=1` environment variable, per clarify Q3) that preserves the original Python traceback on stderr when any exception escapes. Without `--debug`, errors are surfaced as a single `error: <message>` line per FR-011. The flag is parsed before the subcommand so it works as `storebro --debug build ...`.
- **FR-014**: The CLI module MAY import `storebro.hull`, `storebro.deck`, `storebro.interior`, and `storebro.export` (it composes all four). It MAY import `storebro._freecad_check`. It MUST be the only public module to import all of them — this is the explicit dependency-arrow apex per PROJECT-BRIEF.md.
- **FR-015**: The CLI's top-level Python function (suitable for direct invocation via `python -m storebro.cli` AND via the console script entry point) MUST be `main(argv: list[str] | None = None) -> int`. Returning an int (the exit code) rather than calling `sys.exit` makes the CLI testable via direct function calls.
- **FR-016**: For `--format all`: future v1.1+ scope. v1.0 supports exactly one format per `build` invocation (the user runs the command four times if they want all four formats).
- **FR-017**: The CLI MUST be documented in `README.md` with at least one example per subcommand. The README's Quickstart section becomes the CLI's `storebro build --layout Alternativ3 --out boat.FCStd` invocation.

### Key Entities

- **CLI Invocation**: A single command-line invocation with subcommand + arguments. Maps to one `main(argv)` call. Stateless from invocation to invocation.
- **Subcommand**: One of `build`, `list-layouts`, `info`. Each has its own argument schema, exit-code semantics, and output format.
- **Build Pipeline**: The composition `hull → deck → interior → export` invoked once per successful `build`. Each stage is a pure-Python call into the four prior modules.
- **Error Translation**: A mapping from exception type to exit code (1 for input errors, 2 for system errors) and message format (`error: <message>` to stderr).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time user (one who has installed the package and FreeCAD but has never written Python against the library) can produce a valid `.FCStd` file in under 1 minute from a shell prompt by running `storebro build --out boat.FCStd`.
- **SC-002**: `storebro build --out <path>` with defaults completes end-to-end in under 3 minutes on a developer laptop (combining the 30s hull + 45s deck + 60s interior + 3s `.FCStd` write budgets from prior specs, with overhead margin).
- **SC-003**: `storebro list-layouts` completes in under 1 second (it only reads 5 YAML files).
- **SC-004**: `storebro info` completes in under 1 second.
- **SC-005**: Two back-to-back invocations of `storebro build --out path.FCStd` with identical arguments produce byte-identical files (delegates to spec 002 SC-001).
- **SC-006**: Every subcommand has a `--help` / `-h` flag that prints usage and exits with code 0. Verified across all three subcommands.
- **SC-007**: Invalid inputs (unknown layout name, missing required arg, wrong extension, etc.) produce error messages naming the offending argument and exit with the documented non-zero code — verified across at least 8 distinct invalid-input cases.
- **SC-008**: The CLI module's public API surface is exactly one function (`main(argv)`); the rest of the module is private. Verified by introspection of `storebro.cli.__all__`.

## Assumptions

- **Scope of "CLI"**: exactly three subcommands. No `import`, no `export` standalone, no `validate`, no `serve`, no `repl`, no `gui`. Those are out of scope for v1.0.
- **One format per build invocation**: `--format` takes a single value. `--format all` (and "build to all four formats in one call") is out of scope for v1.0.
- **No configuration file**: every input is a command-line argument. No `~/.config/storebro.toml`, no `STOREBRO_*` environment variables. Future scope.
- **Defaults are the canonical Storebro**: a no-argument `storebro build --out boat.FCStd` produces the canonical RC34 1972 boat — default hull, default deck, Alternativ3 interior, `.FCStd` format. This is the project's identity in one line of shell.
- **No GUI**: the CLI is text-only. No FreeCAD GUI is launched; no `--gui` flag exists. The CLI produces files for opening in the FreeCAD GUI separately.
- **Non-interactive**: no prompts, no confirmations. Scripting-friendly by default.
- **Console script entry point**: standard Python packaging convention — `[project.scripts] storebro = "storebro.cli:main"` in `pyproject.toml`.
- **Test environment**: pytest with the same two markers (`unit`, `requires_freecad`). The `build` subcommand requires FreeCAD; `list-layouts` and `info` do not.
- **No logging / no telemetry in v1.0**: matches the prior four specs. Errors go to stderr; success info goes to stdout; no log files.
