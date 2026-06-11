# Feature Specification: FCStd Cross-Invocation Byte Determinism

**Feature Branch**: `028-fcstd-byte-determinism`

**Created**: 2026-06-10

**Status**: Draft

**Input**: User description: "Resolve the v1.0.0 P0-tracked deferral (Fcstd.cross_invocation_byte_determinism): scrub Object IDs / UUIDs / save-timestamps / hex tags across process and invocation boundaries so two storebro build runs emit byte-identical FCStd. Removes the three standing xfails."

## Overview

Constitution principle II (Reproducibility) is NON-NEGOTIABLE: identical inputs must produce byte-identical output, including `.FCStd`. Today STEP/STL/BREP are byte-deterministic across invocations, but FCStd is not — three tests are marked `xfail` because two `storebro build` runs (separate processes) emit different FCStd bytes. The difference comes from FreeCAD's per-session counters leaking into the archive: a document UUID, save-timestamps, sequential Object IDs in `Document.xml`, and Topological-Naming hex tags in the `StringHasher.Table.txt` and `*.Shape.Map.txt` entries. Specs 006/009/011/012 deferred this after naive scrubbing broke FreeCAD's cross-references ("shape is invalid" / loader crash). A pre-implementation spike proved the correct fix works: a **consistent, bijective renumbering** of each per-session identifier (Object IDs via XML parsing; hex hash tags via a global cross-entry map) preserves every cross-reference — the renumbered FCStd reloads with valid geometry — while making the bytes canonical. This spec applies that scrub so two invocations produce byte-identical FCStd, then removes the three `xfail`s. This is a hardening fix to `export.py`'s existing `_scrub_fcstd_zip` — no new public API, no new geometry, no new state.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Byte-identical FCStd across two builds (Priority: P1)

A library consumer (or a CI reproducibility check) runs `storebro build --format fcstd` twice — in the same process or in two separate process invocations — and expects byte-identical output, the same guarantee STEP/STL/BREP already give.

**Why this priority**: It is the entire feature and closes a NON-NEGOTIABLE constitution-II gap (a P0 bug since v1.0.0).

**Independent Test**: Build the same model to FCStd twice in two separate processes; confirm the two files have equal SHA-256, and that each file still opens in FreeCAD with valid geometry (the scrub must not break the document).

**Acceptance Scenarios**:

1. **Given** the same hull+deck+interior(+propulsion) model, **When** exported to FCStd twice in the same process, **Then** the two files are byte-identical (equal SHA-256).
2. **Given** the same model built in two separate process invocations, **When** each is exported to FCStd, **Then** the two files are byte-identical (equal SHA-256).
3. **Given** a scrubbed FCStd, **When** it is re-opened in FreeCAD, **Then** the document loads and every body's shape is valid (`isValid()`), with unchanged geometry (volume/topology equal to an unscrubbed build).

---

### Edge Cases

- **Cross-reference integrity**: the scrub MUST be a consistent bijective renumbering — every occurrence of a given per-session identifier maps to the same canonical value, so FreeCAD's name/handle graph stays intact and the document reloads with valid shapes. Setting identifiers to a constant (breaking uniqueness) or renumbering only some occurrences is forbidden (it is what broke the prior attempts).
- **Entry ordering**: if the per-session counter leak also reorders `*.Map.txt` entries between builds, the scrub MUST canonicalize the order so the bytes match, without breaking the reload.
- **Geometry untouched**: the scrub MUST NOT alter the `.brp` geometry entries or any geometry-bearing data — only the per-session metadata/handles.
- **Within-process regression**: two consecutive same-process exports (already deterministic) MUST remain byte-identical after the change.
- **Partial coverage**: any per-session token format not yet normalized (a new hex-tag shape, a counter) MUST be caught — the test compares full byte equality, so an unnormalized token fails the test rather than passing silently.
- **All layouts / variants**: determinism holds for every canonical layout and the DS variant, and with propulsion on/off, not just one configuration.

## Clarifications

### Session 2026-06-10

- Q: If full byte-determinism for some archive entry would require a normalization that breaks the FreeCAD reload, which constraint wins? → A: Reload-validity wins. FR-004 (the scrubbed FCStd MUST re-open with valid geometry) is the hard constraint — a byte-deterministic but unloadable FCStd is useless. If a specific entry proves irreducible to a canonical form without breaking the reload, that is surfaced as a finding rather than shipping a broken document. (The spike indicates full determinism IS achievable: a renumbered-ID document reloads valid.)
- Q: How is `*.Map.txt` entry reordering (when the per-session counter leak reorders entries between builds) canonicalized? → A: Sort the affected entries on a hex-masked structural key — mask each per-session hex token to a placeholder, sort the entries by the masked form, then renumber the real tokens by appearance — so the order is stable across builds. Each such transform is gated by the per-entry reload-validity check.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Two FCStd exports of the same model **within the same process** MUST be byte-identical (equal SHA-256). **Outcome: achieved** — the comprehensive scrub closes within-process determinism. (Cross-invocation parity is bounded by a FreeCAD-internal limit — see FR-012.)
- **FR-002**: The FCStd scrub MUST normalize every per-session identifier that leaks into the archive: the document UUID, save-timestamps, sequential Object IDs in `Document.xml`, and the Topological-Naming hex tags / hash keys / postfix counters in `StringHasher.Table.txt` and `*.Shape.Map.txt`.
- **FR-003**: Normalization MUST be a consistent bijective renumbering — each distinct per-session identifier maps to one canonical value applied at EVERY occurrence (definition and every reference) — so FreeCAD's cross-reference graph is preserved.
- **FR-004**: A scrubbed FCStd MUST re-open in FreeCAD as a valid document: every body's shape is valid (`isValid()`) and its geometry (volume, topology) is unchanged versus an unscrubbed build.
- **FR-005**: The scrub MUST NOT modify the geometry-bearing entries (`.brp` and equivalent); only per-session metadata/handles are normalized.
- **FR-006**: If `*.Map.txt` entries are reordered between builds by the counter leak, the scrub MUST canonicalize their order by sorting on a hex-masked structural key (mask per-session hex → placeholder, sort, then renumber real tokens by appearance) so the bytes match — each such transform gated by the per-entry reload-validity check.
- **FR-011**: Reload-validity (FR-004) is the hard constraint and takes precedence: the scrub MUST NOT produce an FCStd that fails to reopen in FreeCAD with valid geometry, even to achieve byte-determinism. An entry that proves irreducible to a canonical form without breaking the reload is surfaced as a finding, not shipped broken.
- **FR-007**: Within-process determinism (already holding) MUST be preserved; the change MUST NOT regress STEP/STL/BREP determinism or any other export.
- **FR-008**: The two **within-process** FCStd-determinism `xfail` markers MUST be removed and pass as real assertions. The **cross-invocation** xfail MUST remain — reclassified from "v1.1+ scrub upgrade" to a precisely characterized FreeCAD-internal limitation (FR-012) — with its reason updated to cite the evidence.
- **FR-009**: The fix MUST stay within `export.py`'s existing FCStd scrub path (`_scrub_fcstd_zip` and its helpers); no new public API, no change to `export_fcstd`'s signature.
- **FR-010**: Determinism MUST hold across the supported configurations: every canonical layout (Alternativ1–5), the DS variant, and propulsion on/off — **for the achieved (within-process) guarantee and the reload-validity guarantee**.
- **FR-012** (FreeCAD-internal limitation, discovered during implementation): Full **cross-invocation** byte-determinism is NOT achievable by post-processing. Two separate process invocations occasionally produce a **structurally different** Topological-Naming map for some compartments — e.g. `Interior_Alternativ3_ForwardCabin.Shape.Map.txt` at 842 vs 841 lines, one extra `;<hex>` postfix entry — caused by per-session hash-collision variance in FreeCAD's `StringHasher`. A different NUMBER of distinct tags cannot be canonicalized by scrubbing one file (the scrub cannot see the other build). Closing this requires a FreeCAD upstream fix or a deterministic-hasher reset before save; tracked as `Fcstd.cross_invocation_freecad_hasher_nondeterminism`.

### Key Entities

- **Per-session identifier**: a value FreeCAD assigns from a process-global counter at save time (document UUID, Object ID, Topological-Naming hex tag / hash key, postfix count); varies between invocations and must be canonicalized.
- **Renumbering map**: a bijective old→canonical mapping per identifier domain (Object IDs; hash tags), built in a fixed traversal order and applied to every occurrence across all archive entries.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Two FCStd exports of the same model in the same process have equal SHA-256. **(Achieved.)**
- **SC-002**: ~~Two FCStd exports … in two separate process invocations have equal SHA-256.~~ **Bounded by FR-012** (FreeCAD-internal): cross-invocation parity holds for ~95% of archive entries but not in general; the cross-process test characterizes the residual as an `xfail`.
- **SC-003**: A scrubbed FCStd re-opens in FreeCAD; every body's shape `isValid()` is true and its volume equals an unscrubbed build's. **(Achieved — `test_fcstd_reload_valid`.)**
- **SC-004**: The two within-process FCStd-determinism `xfail` markers are removed and pass as real assertions; the cross-invocation one remains with an updated FreeCAD-limitation reason. **(Achieved.)**
- **SC-005**: STEP/STL/BREP determinism and all other export tests still pass (no regression).
- **SC-006**: The within-process + reload-validity guarantees hold for Alternativ1–5, the DS variant, and propulsion on/off.

## Assumptions

- **Bijective renumbering is the mechanism** (spike-proven): Object IDs are XML attributes referenced by FreeCAD via object NAME, so renumbering the `id` attributes by appearance is safe and reloads valid; hash tags in StringHasher/Map.txt are renumbered via a global cross-entry map. The spike confirmed a renumbered-ID Document.xml reloads with `HullBody` valid (1 solid, full volume).
- **Reordering, if present, is canonicalized** by sorting the affected `*.Map.txt` entries on a hex-masked structural key (so order is stable across builds) — validated by the reload-validity gate; if sorting a given entry breaks the reload, that entry's order is preserved and an alternative normalization is used.
- **Scope**: FCStd only. STEP/STL/BREP/OBJ/IGES/DXF are already deterministic. No geometry, no new public API. The `_scrub_fcstd_zip` path is extended; `export_fcstd` is unchanged.
- **Spec-only track**: this is a hardening fix with no new entities or state transitions, so no `.allium` and no `/tla` — the determinism constraint is expressed as tests (within-process byte-equality + reload-validity, both passing; a cross-process characterization test marked `xfail` per FR-012).
- **Verification host**: FreeCAD 1.1+ via the bundled-Python `PYTHONPATH`; the cross-process test spawns two subprocess builds and compares SHA-256 + reloads each.
- **FR-012 was discovered, not assumed**: implementation cleared the prior wall (Document.xml ID renumber reloads valid) and got ~95% of the way; the residual was then precisely characterized (842 vs 841 lines for ForwardCabin) as FreeCAD `StringHasher` nondeterminism, surfaced to the user, and the agreed landing is "ship the within-process + reload-safe win, document the FreeCAD limit, keep the cross-invocation xfail." See the register history for spec 028.
