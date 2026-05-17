# Data Model: Export Module (Phase 1)

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md) | **Date**: 2026-05-17

Defines the data structures of `storebro.export`: input value objects, the return aggregate, and the two public exception classes.

---

## Entity overview

```
TargetPath (input value)         TessellationTolerance (input value, STL only)
            │                              │
            └──────────┬───────────────────┘
                       ▼
   export_step(body, target_path, *, overwrite=True)
   export_stl(body, target_path, *, overwrite=True, tessellation_tolerance=0.001)
   export_brep(body, target_path, *, overwrite=True)
   export_fcstd(document, target_path, *, overwrite=True)
                       │
                       ├── invalid input ──▶ ExportInputError (raised before any FS / FreeCAD op)
                       │
                       ├── FreeCAD failure ──▶ ExportWriteError (wraps underlying)
                       │
                       ▼
                 ExportArtifact (returned)
```

---

## 1. `TargetPath` (value object — internal, derived from caller's `str | Path`)

Resolved at the entry of every writer from the caller's `str` or `pathlib.Path`. Not a public class — the API takes plain paths and constructs this internally.

| Field | Type | Description |
|---|---|---|
| `absolute_path` | `pathlib.Path` | Resolved absolute path (`path.resolve()`) |
| `extension` | `str` | Lower-cased extension including the dot (e.g. `".step"`, `".FCStd"` kept as-is for case-sensitive matching where format demands it) |
| `parent_dir` | `pathlib.Path` | `absolute_path.parent`, must exist for the writer to proceed |

### Validation (performed by `_resolve_target_path` helper, raises `ExportInputError`)

- `parent_dir` MUST exist on disk and be a directory (FR-006).
- `absolute_path` MUST NOT itself be a directory.
- `extension` MUST match the writer's expected set:
  - `export_step` → `.step` or `.stp`
  - `export_stl` → `.stl`
  - `export_brep` → `.brep` or `.brp`
  - `export_fcstd` → `.FCStd` (case-preserved) or `.fcstd`

---

## 2. `TessellationTolerance` (value object — STL only, internal)

Wraps the public `tessellation_tolerance: float` kwarg with validation.

| Field | Type | Description |
|---|---|---|
| `meters` | `float` | Absolute linear chord deviation, in meters. MUST be `> 0`. |

`_resolve_tessellation_tolerance` raises `ExportInputError("tessellation_tolerance", value, "> 0")` for `value <= 0` or NaN.

---

## 3. `ExportArtifact` (public — return value of every writer)

```python
@dataclass(frozen=True)
class ExportArtifact:
    target_path: pathlib.Path     # Resolved absolute path of the written file
    format: str                   # One of "fcstd", "step", "stl", "brep"
    byte_count: int               # Size of the written file in bytes
    sha256: str                   # SHA-256 hex digest of the written file's bytes
    build_duration_seconds: float # Wall-clock seconds for the write
```

### Contract guarantees

1. `byte_count > 0` (a successful write is never empty).
2. `sha256` is the 64-character lower-case hex digest of `target_path`'s bytes (call `hashlib.sha256` after the rename).
3. `format` is one of the four lower-case strings above; matches the writer that produced the artifact.
4. `target_path` is absolute and exists on disk at the moment of return.
5. `build_duration_seconds` is the wall-clock time from writer entry to just-before-return (excludes Python interpreter teardown).

### Identity & lifecycle

Frozen, value-equal, hashable. Two artifacts with the same field values compare equal. Lifecycle: produced by a writer, returned to the caller, discarded.

---

## 4. `ExportInputError(ValueError)` — public exception

Raised before any FreeCAD or filesystem write operation when an input is invalid.

```python
class ExportInputError(ValueError):
    field: str                    # The offending input ("target_path", "body", "tessellation_tolerance", "document")
    reason: str                   # Human-readable reason
    offending_value: str | None   # Repr of the offending value, or None if multi-field

    def __init__(self, field: str, reason: str, offending_value: str | None = None): ...
```

### Message format

```
ExportInputError: <field> — <reason> (got: <offending_value>)
```

For multi-field (no single offender):

```
ExportInputError: <field> — <reason>
```

### Used by

- Path / extension validation (FR-006).
- `overwrite=False` with existing target file (FR-009).
- Empty Body or document (Edge Cases).
- Out-of-range `tessellation_tolerance` (FR-010).

---

## 5. `ExportWriteError(RuntimeError)` — public exception

Raised when a write fails mid-stream, when FreeCAD raises during the export call, or when the FreeCAD version is unsupported (FR-014).

```python
class ExportWriteError(RuntimeError):
    target_path: pathlib.Path | None       # The intended target, or None for version-check failures
    underlying_message: str                # str(underlying_exception) or "" if synthesized
    format: str | None                     # "fcstd"/"step"/"stl"/"brep" or None for version check
    detected_version: tuple[int, int] | None  # For version-check failures only
    supported_range: str | None            # For version-check failures only

    def __init__(self, message: str, *,
                 target_path: pathlib.Path | None = None,
                 underlying: BaseException | None = None,
                 format: str | None = None,
                 detected_version: tuple[int, int] | None = None,
                 supported_range: str | None = None): ...
```

### Message format

```
ExportWriteError: <message>
```

When wrapping an underlying exception:

```
ExportWriteError: writing <format> to <target_path> failed — <type(underlying)>: <message>
```

### Used by

- FreeCAD raises during `Part.export`, `Mesh.export`, `Shape.exportBrep`, or `Document.saveAs`.
- `os.replace` raises (typically cross-filesystem) — per OQ2 resolution, no copy+delete fallback.
- `_FreeCADCheck.ensure_supported_freecad()` rejects an unsupported version.

---

## 6. Module-private types (NOT public)

Documented for plan completeness; not exported.

### `_SubshapeCentroidKey`

Internal tuple `(float, float, float, int)` used by `_sorted_subshapes()` (research R5). Lexicographic sort key for canonical subshape ordering. Not a class — a plain tuple is sufficient.

### `_ScrubbedFCStdBytes`

Internal `bytes` buffer holding the post-processed `.FCStd` zip content. Produced by `_scrub_fcstd_zip(raw_bytes)`; consumed by `_atomic_write(target_path, scrubbed_bytes)`. Not a class — a bytes alias for documentation only.

---

## State transitions

Every writer is a pure function from `(source, target_path, kwargs)` to `ExportArtifact | raise`. No persistent state between calls except the FreeCAD version-check cache reused from spec 001's `_freecad_check.py`.

Internal state machine of one writer invocation:

```
START
  │
  ├── version_check: unknown ──┐
  │                            ▼
  │                       in_range OR raise ExportWriteError (version)
  │                            │
  │                            ▼
  ├── input_validation: not_started
  │                            │
  │                            ├─ valid ──┐
  │                            └─ invalid ──▶ raise ExportInputError (END)
  │                                   │
  │                                   ▼
  ├── source_recompute (FCStd only): document.recompute()
  │                                   │
  │                                   ▼
  ├── subshape_canonicalization: shape sorted by centroid lex order recursively
  │                                   │
  │                                   ▼
  ├── freecad_export_to_tmp: tempfile.mkstemp(dir=parent)
  │                                   │
  │                            ├─ success ──┐
  │                            └─ freecad_raised ──▶ cleanup tmp, raise ExportWriteError (END)
  │                                   │
  │                                   ▼
  ├── post_process_scrub: format-specific (STEP header / .FCStd zip / BREP originator)
  │                                   │
  │                                   ▼
  ├── atomic_rename: os.replace(tmp, target)
  │                            ├─ success ──┐
  │                            └─ os_error ──▶ cleanup tmp, raise ExportWriteError (END)
  │                                   │
  │                                   ▼
  ├── hash_compute: SHA-256 over target's bytes
  │                                   │
  │                                   ▼
  └── RETURN ExportArtifact(target_path, format, byte_count, sha256, build_duration_seconds)
```

This state machine is the model for the `/tla` verification step (post-implementation). Note: this is a longer pipeline than spec 001's hull builder, which means the triviality gate may or may not apply for spec 002 depending on how many user-observable states the caller cares about. The TLA+ phase will decide.

---

## Cross-references

- Public API contract → [contracts/python-api.md](./contracts/python-api.md)
- Usage example → [quickstart.md](./quickstart.md)
- Formal invariants → [spec.allium](./spec.allium)
- Acceptance criteria → [spec.md](./spec.md) §Success Criteria
