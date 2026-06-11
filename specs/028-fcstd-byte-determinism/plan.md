# Implementation Plan: FCStd Cross-Invocation Byte Determinism

**Branch**: `028-fcstd-byte-determinism` | **Date**: 2026-06-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/028-fcstd-byte-determinism/spec.md`

## Summary

Make two `storebro build --format fcstd` runs (same process OR two separate process invocations) emit byte-identical FCStd, closing the v1.0.0 constitution-II P0 and removing the three standing `xfail`s. The fix extends `export.py`'s existing `_scrub_fcstd_zip` with a **consistent bijective renumbering** of every per-session identifier — proven in a spike to preserve FreeCAD's cross-references (the scrubbed document reloads with valid geometry). Spec-only track (hardening; no new entities/state; no `.allium`/`/tla`).

**Spike evidence (this host, FreeCAD 1.1.1):** cross-process FCStd differs only in (1) `Document.xml` — a document UUID, save-timestamp `<String>`, and sequential `<Object id="N">` attributes; (2) `StringHasher.Table.txt` + `*.Shape.Map.txt` — Topological-Naming hex tags (`:H<hex>`, `;D<hex>`, dotted `:N.N.N`, `#<hex>`) and a `PostfixCount`; the `.brp` geometry is byte-identical. Renumbering the `Document.xml` `id` attributes via XML parsing + scrubbing the UUID **reloads valid** (`HullBody` valid, 1 solid, full volume) — the wall the prior naive attempts hit is cleared by doing a precise, bijective, by-name-safe renumber.

## Technical Context

**Language/Version**: Python 3.11+ (FreeCAD 1.1 bundled Python).
**Primary Dependencies**: stdlib `zipfile`/`io`/`re`/`xml.etree`; FreeCAD only for the reload-validity test.
**Testing**: `pytest` (geometry: `requires_freecad`, incl. a cross-process subprocess test), `ruff`, `mypy --strict`.
**Target Platform**: FreeCAD 1.1+ console.
**Project Type**: Single library; the change is confined to `export.py`'s FCStd scrub helpers.
**Constraints**: byte-identical FCStd across invocations (constitution II); the scrubbed FCStd MUST reload with valid geometry (FR-004/FR-011, the hard constraint); geometry entries untouched (FR-005).
**Scale/Scope**: `export.py` scrub helpers only (`_scrub_document_xml`, `_scrub_hex_tags`, `_scrub_fcstd_zip` + new helpers). No public API change.

## Constitution Check

| Principle | Status | Compliance |
|---|---|---|
| I. Parametric | ✅ | No geometry/params touched. |
| II. Reproducibility (NON-NEGOTIABLE) | ✅ | THE point — this closes the FCStd cross-invocation gap; the cross-process test enforces it. |
| III. FreeCAD-Idiomatic | ✅ | Document stays a valid, GUI-loadable FCStd (FR-004 reload gate); no geometry touched. |
| IV. Reference Fidelity | ✅ | Geometry unchanged. |
| V. Test-Gated | ✅ | The three xfails become real assertions + a cross-process test + a reload-validity test. |
| VI. SemVer | ✅ | No public API change → PATCH bump 1.13.0 → 1.13.1. |
| VII. FreeCAD Version Discipline | ✅ | No version-specific API beyond the existing scrub. |

**Result: PASS.**

## Build Sequence (one task)

1. **Document.xml renumber** — extend `_scrub_document_xml`: XML-parse, renumber every `<Object id="N">` attribute to a canonical sequence by appearance, scrub the `<Uuid>` value to a fixed UUID, and the save-timestamp `<String>` to the fixed date. Re-serialize via the existing canonical serializer.
2. **Hash-tag renumber** — extend `_scrub_hex_tags` into a GLOBAL cross-entry pass over `StringHasher.Table.txt` + all `*.Map.txt`: collect every per-session hex token (`:H<hex>` incl. negative, `;D<hex>`, dotted `:N.N.N`, `#<hex>`) into one bijective map (first-appearance order across entries in a fixed entry order), normalize `PostfixCount` to a fixed value, and apply the map to every occurrence.
3. **Entry-order canonicalization** — if `*.Map.txt` entries reorder (FR-006), sort them on a hex-masked structural key before renumbering; gate each transform on the reload-validity check.
4. **Wire into `_scrub_fcstd_zip`** — drive the two-pass scrub (Document.xml, then the global hash-tag pass across the Map/StringHasher entries) within the existing re-pack.
5. **Reload-validity gate** — the test re-opens the scrubbed FCStd in FreeCAD and asserts every body's shape `isValid()` + volume unchanged (FR-004/FR-011).
6. **Remove the 3 xfails** + add the cross-process (two-subprocess) byte-equality test + the reload-validity test; cover Alt1–5 + DS + propulsion on/off (FR-010) at a representative subset for runtime.
7. **Version** 1.13.0 → 1.13.1 + version test.

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Renumbering breaks a cross-reference → loader fails | Spike-proven safe for Object IDs (reload valid); the reload-validity test (FR-004) gates every transform — a breaking normalization is reverted/surfaced, never shipped. |
| A hash token referenced across entries gets inconsistent IDs | One GLOBAL bijective map applied to ALL entries (StringHasher + every Map.txt), so cross-entry references stay consistent. |
| Map.txt reordering defeats renumbering | Sort on the hex-masked structural key before renumbering (FR-006). |
| An entry proves irreducible without breaking reload | FR-011: reload-validity wins; surface as a finding rather than ship broken. |

## Phase 2 note

`/speckit-tasks` expands this; `/speckit.analyze` runs before `/implement`. Spec-only track → no `/allium`, no `/tla`; the constraint is the cross-process test.
