# Tasks: FCStd Cross-Invocation Byte Determinism

**Feature**: 028-fcstd-byte-determinism | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

**Scope**: `src/storebro/export.py` FCStd scrub helpers only (+ version). Tests in `tests/geometry/`. Spec-only track (hardening; no new API/entities/state). Destructive-test analog: cross-process byte-equality + reload-validity.

---

**OUTCOME (FR-012, FreeCAD-internal limit):** within-process determinism + reload-validity ACHIEVED; full cross-invocation parity BLOCKED by FreeCAD `StringHasher` nondeterminism (different topological-map entry count between processes). Landed per user decision: ship the within-process + reload-safe win, document the FreeCAD limit, keep the cross-invocation xfail.

## Phase 1: Implementation

- [x] T001 Extend `_scrub_document_xml`: XML-parse, renumber every `<Object id="N">` by appearance, scrub `<Uuid>` → fixed UUID + ISO-timestamp `<String>` → fixed date; re-serialize canonically. **Spike-proven reload-valid.**
- [x] T002 Replace `_scrub_hex_tags` with a GLOBAL cross-entry pass: collect every per-session token (`:H`, `;D`, `#`, `:G#`, dotted/single `:`, `;gNvN.`) across `StringHasher.Table.txt` + all `*.Map.txt`; assign each a COUNT/order-independent canonical value = a hash of its (entry, masked-line) context multiset (a sequential index drifts when the per-session hash-collision count differs); zero `PostfixCount` + the StringHasher counter column.
- [x] T003 `*.Map.txt` order canonicalization (FR-006): two-pass sort (coarse by hex-masked structural key, then fine by the canonical line) — proven reload-safe (the maps are rebuilt from geometry).
- [x] T004 Wire the two-pass scrub into `_scrub_fcstd_zip` (Document.xml, then the global hash-tag pass across StringHasher + Map.txt); `.brp` geometry untouched (FR-005).

## Phase 2: Tests + verification

- [x] T005 `tests/geometry/test_fcstd_reload_valid.py`: scrubbed FCStd re-opens; every body's shape `isValid()` + volume unchanged (FR-004/FR-011). **PASSES.**
- [x] T006 `tests/geometry/test_fcstd_cross_process_determinism.py`: two subprocess builds, equal SHA-256 across Alt1/3/5 + DS + propulsion on/off. **Marked `xfail` (FR-012)** — characterizes the FreeCAD wall.
- [x] T007 Removed the TWO within-process xfails (`test_export_determinism.py` fcstd, `test_export_fcstd.py::test_export_fcstd_determinism`) — now real passing assertions; kept `test_cli_build_byte_determinism.py` xfail with the precise FreeCAD-limitation reason (FR-008/SC-004). STEP/STL/BREP unaffected (SC-005).
- [x] T008 Version 1.13.0 → 1.13.1 (`__init__.py` + `pyproject.toml` + version test).
- [x] T009 Gate: `uv run pytest` unit + full `requires_freecad` geometry suite + ruff + mypy. Signoff: two same-process FCStd byte-identical.

## Dependencies

- T001–T004 are the scrub (serialize edits to `export.py`). T004 wires T001–T003.
- T005 (reload gate) and T006 (cross-process) validate the scrub; T007 flips the xfails only after T006 is green.
- T008/T009 last.

## Implementation Strategy

The spike already proved the Document.xml renumber reloads valid. Implement T001 first and re-verify reload + cross-process Document.xml equality, then T002/T003 for the StringHasher/Map.txt tokens, re-verifying reload + full byte equality after each, then flip the xfails. The reload-validity gate (T005) is the safety net for every transform.
