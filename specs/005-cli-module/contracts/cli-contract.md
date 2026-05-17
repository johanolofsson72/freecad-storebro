# Contract: `storebro` CLI

**Spec**: [../spec.md](../spec.md) | **Plan**: [../plan.md](../plan.md) | **Date**: 2026-05-17

Public contract for the `storebro` command-line interface. Governed by semver — breaking changes (renaming a subcommand, changing exit-code meanings, removing an option) require a MAJOR bump.

---

## Invocation forms

Both forms are equivalent and call the same `main(argv)` function:

```bash
storebro <subcommand> [options]
python -m storebro <subcommand> [options]
```

The Python module form is documented for environments where the console script isn't on PATH.

---

## Subcommand: `storebro build`

```
storebro build --out PATH [--layout NAME] [--format FORMAT] [--no-overwrite] [--tessellation METERS]
```

### Required options

- `--out PATH`: destination file path.

### Optional options

- `--layout NAME`: layout name or YAML file path (default `Alternativ3`).
- `--format FORMAT`: one of `fcstd`, `step`, `stl`, `brep` (default `fcstd`).
- `--no-overwrite`: refuse to overwrite an existing target file (default: overwrite allowed).
- `--tessellation METERS`: STL tessellation tolerance in meters (default `0.001`, only meaningful for `--format stl`).

### Behavior

Composes `build_hull → build_deck → build_interior → export_<format>` per FR-004.

### Output

**Success** (exit code 0):

```
wrote <format> to <abs_path> (<byte_count> bytes, SHA-256 <hash>)
```

**Failure** (exit code 1 for input errors, 2 for system errors): single `error: <message>` line on stderr.

---

## Subcommand: `storebro list-layouts`

```
storebro list-layouts
```

No options. Prints five tab-separated lines:

```
<layout_name>\t<source>\t<description>
```

Exits with code 0. Does NOT require FreeCAD.

---

## Subcommand: `storebro info`

```
storebro info
```

No options. Prints key-value lines:

```
freecad-storebro version: <version>
Python version: <python_version>
Platform: <system> <machine>
FreeCAD detected: <freecad_version or "not detected">
FreeCAD supported range: <range_from_pyproject>
```

Exits with code 0. Does NOT require FreeCAD (the `FreeCAD detected` line reads `not detected` if absent).

---

## Global options

- `--help` / `-h`: prints usage for the top-level CLI or the current subcommand. Exit code 0.
- `--debug`: preserves the full Python traceback on stderr instead of the one-line `error:` message. Works in any position (`storebro --debug build ...`, `storebro build --debug ...`).
- `STOREBRO_DEBUG=1` environment variable: equivalent to `--debug` globally.

---

## Exit codes

| Code | Meaning | Examples |
|---|---|---|
| 0 | Success | Successful build, list-layouts, info |
| 1 | Input error | Invalid layout, missing required arg's domain value (e.g., out-of-envelope compartment), bad YAML schema, target path issues |
| 2 | System error | Unsupported FreeCAD version, FreeCAD-side construction failure, filesystem write failure, unexpected exception, argparse argument-parsing error |

---

## Public Python API

```python
from storebro.cli import main

# main(argv: list[str] | None = None) -> int
exit_code = main(["build", "--out", "/tmp/boat.FCStd"])
sys.exit(exit_code)
```

`storebro.cli.__all__` exactly:

```python
__all__ = ["main"]
```

No other public name. The argparse builder, exit-code mapper, subcommand handlers, etc. are private.

---

## Versioning

- **PATCH**: bug fixes, internal refactor, improved error messages (same exit codes).
- **MINOR**: new optional flags (additive), new subcommands (additive), new fields in stdout summary (additive at end of line so grep-by-prefix tools still work).
- **MAJOR**: removing a subcommand, renaming a flag, changing the exit-code-1-vs-2 split, removing a key from `info` output, changing the tab-separated `list-layouts` format.

---

## Out of scope (v1.0)

- `storebro import`, `storebro validate`, `storebro serve`, `storebro repl`, `storebro gui`
- `--format all` / comma-separated formats
- `~/.config/storebro.toml` configuration file
- Hull / deck parameter overrides (`--loa`, `--beam`, etc.)
- `--custom-layout-dir` for `list-layouts`
- `--json` output for any subcommand
- A `--gui` flag to open the resulting file in FreeCAD GUI
- Color codes / progress bars / spinners
