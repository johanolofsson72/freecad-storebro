# Feature Specification: CLI Enhancements

**Feature Branch**: `027-cli-enhancements` | **Created**: 2026-06-02 | **Status**: Draft

**Input**: Roadmap 027 — grow the CLI beyond `build/list-layouts/info`. Scoped to the highest-value, fully-testable subset: a `--json` machine-readable output mode and hull parameter overrides. GUI launch, config file, multi-format export, and custom-layout dir are deferred (see Clarifications).

## Context

The `storebro build` command writes one artifact and prints a human line. Two gaps bite real users: (1) no machine-readable output, so scripting around the build means scraping the print line; (2) no way to tune hull dimensions from the CLI — `station_count` (the spec 018 smoothness knob), `loa`, `beam`, and `draft` are Python-only. This spec closes both with additive, fully unit-testable flags. No geometry changes.

## Clarifications

### Session 2026-06-02

- Q: Which CLI items are in scope? → A: `--json` output mode + hull overrides (`--loa`, `--beam`, `--draft`, `--station-count`). DEFERRED: GUI launch (environment-dependent, not headless-testable), config file, multi-format single-invocation export, custom-layout directory — each is a larger follow-on.
- Q: How does `--json` interact with the human line? → A: `--json` replaces the human line with a single JSON object on stdout (`{format, target_path, byte_count, sha256, version}`); without it, the existing human line is unchanged.
- Q: How do overrides compose with defaults? → A: A hull override flag that is omitted uses the `HullParameters` default; any provided override is validated by `HullParameters` (out-of-range → the existing non-zero CLI error). Overrides are independent of `--layout`/`--superstructure`/`--engine-count`.
- Q: Back-compat? → A: All flags omitted ⇒ byte-identical to the current `build` behavior and output.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Machine-readable build output (Priority: P1)

A script runs `storebro build ... --json` and parses the result (path, size, hash) without scraping prose.

**Independent Test**: Run build with `--json`; stdout is a single valid JSON object with `format`, `target_path`, `byte_count`, `sha256`, `version`; without `--json` the human line is unchanged.

**Acceptance Scenarios**:
1. **Given** `--json`, **When** the build succeeds, **Then** stdout is one JSON object with the artifact fields + version and exit code 0.
2. **Given** no `--json`, **When** the build succeeds, **Then** the existing human line prints (back-compat).

---

### User Story 2 — Hull overrides from the CLI (Priority: P1)

A user tunes the hull without writing Python: `--station-count 51 --loa 11.0`.

**Independent Test**: Run build with each override; the value threads into `HullParameters`; an out-of-range value is rejected with a non-zero exit.

**Acceptance Scenarios**:
1. **Given** `--station-count 51`, **When** the build runs, **Then** the hull is built with `station_count=51`.
2. **Given** `--loa 11.0 --beam 3.4 --draft 1.1`, **When** the build runs, **Then** those dimensions thread into `HullParameters`.
3. **Given** an out-of-range override (`--station-count 999`), **When** the build runs, **Then** it exits non-zero with the `HullParameters` validation message.
4. **Given** no override flags, **When** the build runs, **Then** `HullParameters` defaults are used (back-compat).

---

### Edge Cases

- `--json` on a failed build → the existing error path + non-zero exit (no partial JSON).
- An override equal to the default → identical output to omitting it.
- Overrides + `--format step/stl/brep` → the override threads through regardless of format.
- Reproducibility: identical flags → identical artifact + identical JSON (modulo the inherently input-determined hash).

## Requirements *(mandatory)*

- **FR-001**: `storebro build` MUST accept `--json`; when present, stdout MUST be a single JSON object with `format`, `target_path`, `byte_count`, `sha256`, and `version`, and nothing else on stdout.
- **FR-002**: Without `--json`, the existing human-readable line MUST print unchanged (back-compat).
- **FR-003**: `storebro build` MUST accept `--loa`, `--beam`, `--draft` (floats, meters) and `--station-count` (int); each provided value MUST thread into `HullParameters`.
- **FR-004**: An omitted hull override MUST use the `HullParameters` default; the build with no overrides MUST be byte-identical to the current behavior.
- **FR-005**: An out-of-range override MUST be rejected via `HullParameters` validation and surface as the existing non-zero CLI exit with the validation message (before/without writing an artifact).
- **FR-006**: `--json` MUST compose with all existing flags (`--format`, `--layout`, `--superstructure`, `--engine-count`, `--no-*`).
- **FR-007**: GUI launch, config file, multi-format single-invocation export, and custom-layout directory are OUT OF SCOPE (deferred follow-ons).

## Key Entities

- **Build result JSON**: The machine-readable object emitted under `--json` (artifact fields + library version).
- **Hull overrides**: The optional CLI flags that, when present, populate `HullParameters` fields, else fall back to defaults.

## Success Criteria

- **SC-001**: `--json` emits one parseable JSON object with the five fields; exit 0 on success.
- **SC-002**: Each hull override threads into `HullParameters`; an out-of-range value exits non-zero with the validation message.
- **SC-003**: With no new flags, `build` output + artifact are byte-identical to the current behavior.

## Assumptions

- Overrides only populate `HullParameters`; deck/interior/propulsion overrides stay out of scope.
- No geometry change — this is a CLI surface + output-format spec (spec-only-grade risk, but full track since it adds user-facing behavior). Unit tests (argparse + wiring with a mocked build chain) cover it; one smoke build confirms end-to-end.
- Additive public CLI surface → MINOR bump.
