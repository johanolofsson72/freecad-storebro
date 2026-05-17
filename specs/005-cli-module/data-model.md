# Data Model: CLI Module (Phase 1)

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md) | **Date**: 2026-05-17

The CLI module has minimal internal data structures: argparse `Namespace` objects (stdlib), an exit-code dispatch table, and a one-line summary record per build. Most of the spec's "entities" are processes (invocation flow) rather than typed data.

---

## 1. `_ParsedArgs` — internal argparse Namespace

Argparse returns a `Namespace` whose attributes match the documented options:

| Attribute | Type | Source FR |
|---|---|---|
| `subcommand` | `str` (one of `"build"`, `"list-layouts"`, `"info"`) | FR-002 |
| `layout` | `str` | FR-003 |
| `out` | `str` (path) | FR-003 |
| `format` | `str` (one of `"fcstd"`, `"step"`, `"stl"`, `"brep"`) | FR-003 |
| `no_overwrite` | `bool` | FR-003 |
| `tessellation` | `float` | FR-003 |

The Namespace is internal — never exported. Subcommand handlers receive it as a positional argument.

---

## 2. Exit-code dispatch table

```python
_INPUT_ERROR_TYPES: tuple[type[Exception], ...] = (
    HullParameterError,
    DeckParameterError,
    InteriorParameterError,
    ExportInputError,
)

_SYSTEM_ERROR_TYPES: tuple[type[Exception], ...] = (
    HullConstructionError,
    DeckConstructionError,
    InteriorConstructionError,
    ExportWriteError,
)

def _exit_code_for(exc: BaseException) -> int:
    if isinstance(exc, _INPUT_ERROR_TYPES):
        return 1
    if isinstance(exc, _SYSTEM_ERROR_TYPES):
        return 2
    return 2  # KeyboardInterrupt, OSError, etc. → system error category
```

---

## 3. Build summary record (one line on stdout)

```
wrote <format> to <abs_path> (<byte_count> bytes, SHA-256 <hash>)
```

Example:

```
wrote fcstd to /tmp/boat.FCStd (192884 bytes, SHA-256 4a1e9b2c8d3f1234567890abcdef1234567890abcdef1234567890abcdef1234)
```

Fields:
- `<format>`: lowercase string from `art.format`
- `<abs_path>`: `str(art.target_path)` (already absolute per spec 002 contract)
- `<byte_count>`: `art.byte_count` (int)
- `<hash>`: `art.sha256` (lower-case 64-char hex string)

---

## 4. `list-layouts` output line format

Tab-separated:

```
<canonical_name>\t<source>\t<one_line_description>
```

Example:

```
Alternativ3	docs/references/Alternativ3.JPG	4 compartments — canonical RC34
```

Fields harvested from the YAML's `layout_name`, `source`, and a hand-curated description string built by joining the compartment count + the first compartment's `description` (or a fixed string if absent).

---

## 5. `info` output line format

Key-value lines, colon-separated:

```
freecad-storebro version: 1.0.0
Python version: 3.11.11
Platform: Darwin arm64
FreeCAD detected: 1.1.0
FreeCAD supported range: >=1.1,<2.0
```

When FreeCAD is not importable:

```
FreeCAD detected: not detected
```

The other lines populate unconditionally.

---

## 6. State transitions

CLI is stateless. One `main(argv)` invocation maps to one of three subcommand handlers, each of which is a pure function with side effects on stdout / stderr / the filesystem (for `build`).

```
START
  │
  ├── Parse argv (with --debug strip)
  │       │
  │       └── argparse error → ProcessExit(2)
  │
  ├── Dispatch on subcommand:
  │     ├── build       → _run_build(args)
  │     ├── list-layouts → _run_list_layouts()
  │     └── info        → _run_info()
  │
  ├── Subcommand handler:
  │       │
  │       ├── success → write stdout, return 0
  │       │
  │       └── exception caught:
  │             │
  │             ├── if --debug → re-raise (preserve traceback)
  │             │
  │             └── else → write "error: <msg>" to stderr, return _exit_code_for(exc)
  │
  └── main() returns exit code (or sys.exit(code) from __main__.py)
```

State machine depth: trivial. 3 transitions per subcommand, 1 caller. The `/tla` step will hit the triviality gate.

---

## Cross-references

- Public API contract → [contracts/cli-contract.md](./contracts/cli-contract.md)
- Usage example → [quickstart.md](./quickstart.md)
- Formal invariants → [spec.allium](./spec.allium)
- Acceptance criteria → [spec.md](./spec.md) §Success Criteria
- All four upstream modules' contracts → spec 001-004's `contracts/python-api.md`
