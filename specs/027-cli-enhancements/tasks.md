# Tasks: CLI Enhancements

**Feature**: 027 | **Track**: full | **Spec**: [spec.md](./spec.md)

## Phase 1: Setup
- [x] T001 Baseline: unit + ruff + mypy.

## Phase 2: Flags + wiring (US1 + US2)
- [x] T002 [US2] build subparser: add `--loa`/`--beam`/`--draft` (float, default None) + `--station-count` (int, default None).
- [x] T003 [US1] build subparser: add `--json` (store_true).
- [x] T004 [US2] `_run_build`: build a `HullParameters` from any provided overrides (others default) and pass to `build_hull`; HullParameters validation → existing non-zero exit. No overrides → unchanged (None → defaults).
- [x] T005 [US1] `_run_build`: emit `json.dumps({format,target_path,byte_count,sha256,version})` when `--json`, else the existing human line.

## Phase 3: Tests
- [x] T006 [P] [US1] Unit: `--json` parse + `_run_build` emits one JSON object with the 5 fields (mocked build chain); no `--json` → human line.
- [x] T007 [P] [US2] Unit: each override parses + threads into the `HullParameters` passed to a mocked `build_hull`; out-of-range `--station-count` → non-zero exit + validation message; no overrides → `parameters` None/defaults.
- [x] T008 [US1] Update `test_cli_flags_v103` baseline to include the new flags.

## Phase 4: Polish
- [x] T009 Version 1.6.0 -> 1.7.0 (init, pyproject, version test).
- [x] T010 Verify: full unit suite + ruff + mypy; one smoke build on FreeCAD (single hull) confirms `--json` + an override end-to-end.

## Notes
- No geometry suite needed (CLI/param wiring); /tla skipped.
