---
description: "Task list for the CLI module (spec 005)"
---

# Tasks: CLI Module

**Input**: Design documents from `/specs/005-cli-module/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/cli-contract.md](./contracts/cli-contract.md), [quickstart.md](./quickstart.md), [spec.allium](./spec.allium)

**Tests**: REQUIRED per constitution V. ≥8 invalid-input cases (SC-007), --help on every subcommand (SC-006), single public function (SC-008).

## Format: `[ID] [P?] [Story?] Description with file path`

## Path Conventions

Single Python project, src-layout (continues from spec 001/002/003/004):
- Library source: `src/storebro/`
- Tests: `tests/unit/` + `tests/geometry/`
- Console-script entry point: `[project.scripts]` in `pyproject.toml`

---

## Phase 1: Setup

- [x] T001 Verify spec 001-004 scaffolding intact: `src/storebro/{__init__.py,hull.py,export.py,deck.py,interior.py,_freecad_check.py}`, `src/storebro/fixtures/Alternativ*.yaml`, conftests. `uv run pytest --collect-only` clean.
- [x] T002 Add `[project.scripts] storebro = "storebro.cli:main"` to `pyproject.toml` (creates the console-script entry point per FR-001). Bump `version = "1.0.0"`. Run `uv sync --extra dev` to refresh the installed entry point.

---

## Phase 2: Foundational

- [x] T003 Create `src/storebro/cli.py`. Define `_INPUT_ERROR_TYPES` and `_SYSTEM_ERROR_TYPES` tuples per data-model §2 (referencing the 4 + 4 exception classes from spec 001-004). Define `_exit_code_for(exc)` helper returning 1, 2, or 2 per the dispatch table.
- [x] T004 In `src/storebro/cli.py`, implement `_build_top_parser()` returning an `argparse.ArgumentParser` with `prog="storebro"` and three subparsers (`build`, `list-layouts`, `info`) per contracts/cli-contract.md. Configure each subparser's arguments per FR-003 (build: --layout, --out (required), --format, --no-overwrite, --tessellation); list-layouts: no options; info: no options.
- [x] T005 In `src/storebro/cli.py`, implement private `_strip_debug_flag(argv)` per research.md R5: returns `(debug_flag: bool, cleaned_argv: list[str])`. Honors `STOREBRO_DEBUG=1` env var. Strips `--debug` from any position in argv before argparse sees it.
- [x] T006 In `src/storebro/cli.py`, implement private `_run_info()` per FR-009 + data-model §5: prints key-value lines for `freecad-storebro version` (from `storebro.__version__`), `Python version` (`platform.python_version()`), `Platform` (`platform.system()` + " " + `platform.machine()`), `FreeCAD detected` (try import FreeCAD; on ImportError print `not detected`; else print `FreeCAD.Version()[0:3]` joined by `.`), `FreeCAD supported range` (read from `pyproject.toml` via storebro._freecad_check helpers). Returns 0.
- [x] T007 In `src/storebro/cli.py`, implement private `_run_list_layouts()` per FR-007 + research.md R4: iterates the five canonical names in fixed order, loads each fixture's YAML via spec 004's `_load_layout`, builds a one-line description from the layout's `source` field + compartment-count summary, prints tab-separated. Returns 0. Does NOT require FreeCAD.
- [x] T008 In `src/storebro/cli.py`, implement private `_run_build(args)` per FR-004 + FR-006: composes `build_hull()` → `build_deck(hull)` → `build_interior(hull, deck, layout=args.layout)` → writer-per-format. Per FR-004's v1.0 pinning: `fcstd` → `export_fcstd(hull.document, args.out, overwrite=not args.no_overwrite)` (full assembly); `step`/`brep` → `export_<f>(hull.body, args.out, overwrite=...)` (hull body only — deck + interior still built, just not in the exported solid; v1.1+ deferred per `spec.allium`); `stl` → `export_stl(hull.body, args.out, overwrite=..., tessellation_tolerance=args.tessellation)` (hull body only). Print one-line success summary per data-model §3. Returns 0.
- [x] T009 In `src/storebro/cli.py`, implement public `main(argv: list[str] | None = None) -> int` per FR-015 + research.md R5: `argv = sys.argv[1:] if argv is None else list(argv)`; `_strip_debug_flag` first; parse remaining argv with top parser; dispatch on `args.subcommand` to one of the three handlers; wrap the whole dispatch in try/except that, on caught exception, either re-raises (`if debug`) or writes `error: <message>` to stderr and returns `_exit_code_for(exc)`.
- [x] T010 Create `src/storebro/__main__.py` per research.md R7: imports `main` from `storebro.cli`, calls `sys.exit(main())` under `if __name__ == "__main__":`. 4 lines plus docstring.
- [x] T011 Update `src/storebro/__init__.py` to re-export `main` from `storebro.cli`. Add to `__all__`. Confirm `__version__` is `"1.0.0"`.

### Foundational tests (parallel after T011)

- [x] T012 [P] `tests/unit/test_cli_argparse.py`: invoke `main(["--help"])` (or capture argparse's SystemExit) → exit code 0, stdout contains "usage:"; same for `main(["build", "--help"])`, `main(["list-layouts", "--help"])`, `main(["info", "--help"])`. Each subcommand has its `--help` (SC-006).
- [x] T013 [P] `tests/unit/test_cli_argparse.py` continued: `main(["frobnicate"])` → argparse exits with code 2 and stderr contains "usage" (FR-002 unknown subcommand). `main(["build"])` without --out → argparse exits with code 2 and stderr names the missing argument. `main(["build", "--out", "x", "--format", "txt"])` (unknown format) → exit code 2. ≥5 cases here.
- [x] T014 [P] `tests/unit/test_cli_exit_codes.py`: parameterize over the 4 input-error exception types from spec 001-004 plus the 4 construction-error types; monkeypatch the relevant module function to raise each type; assert `_exit_code_for(exc)` returns 1 for input errors, 2 for system errors. ≥8 cases here (contributes to SC-007's bar).
- [x] T015 [P] `tests/unit/test_cli_debug_flag.py`: `main(["--debug", "info"])` → debug=True; `main(["info", "--debug"])` → debug=True (works in any position); `STOREBRO_DEBUG=1 main(["info"])` → debug=True; with debug=True, an exception in a subcommand handler propagates (use monkeypatch to force one in `_run_info`); without debug, the same exception produces `error: <msg>` on stderr and a non-zero return code.
- [x] T016 [P] `tests/unit/test_cli_info.py`: `main(["info"])` → exit code 0, stdout contains every required key from data-model §5 (`freecad-storebro version`, `Python version`, `Platform`, `FreeCAD detected`, `FreeCAD supported range`). Use monkeypatch to force `FreeCAD` import to fail and assert `FreeCAD detected: not detected` appears. **FR-012 guard**: assert `re.search(r"\x1b\[", capsys_stdout) is None` (no ANSI escapes). **SC-004 budget**: wrap call in `time.perf_counter()`; assert elapsed < 1.0 s.
- [x] T017 [P] `tests/unit/test_cli_list_layouts.py`: `main(["list-layouts"])` → exit code 0, stdout has exactly 5 lines, each tab-separated; the first column lists `Alternativ1`..`Alternativ5` in order. Does NOT need FreeCAD. **FR-012 guard**: assert `re.search(r"\x1b\[", capsys_stdout) is None` (no ANSI escapes). **SC-003 budget**: wrap call in `time.perf_counter()`; assert elapsed < 1.0 s.
- [x] T018 [P] `tests/unit/test_cli_python_m_entry.py`: `import storebro.__main__` works without side effects (the module-level code only runs under `if __name__ == "__main__":`). Verifies the file exists and exports `main`.
- [x] T019 [P] `tests/unit/test_cli_leaf_dependencies.py`: AST scan of `src/storebro/cli.py` — MUST import all of `storebro.hull`, `storebro.deck`, `storebro.interior`, `storebro.export` (FR-014); the CLI is the dependency-arrow apex.
- [x] T019a [P] `tests/unit/test_cli_no_user_prompts.py` (FR-013 + spec.allium `NoUserPrompts`): AST-scan `src/storebro/cli.py` source for any call to `input` or `getpass.getpass`; assert zero matches. The CLI must be non-interactive — no readlines, no prompts, no confirmations.

**Checkpoint**: `uv run pytest tests/unit/test_cli_*.py -v` green.

---

## Phase 3: User Story 1 - Restorer generates a model with one command (P1, MVP)

**Goal**: `storebro build --out boat.FCStd` produces a valid FreeCAD document.

**Independent Test**: Shell → `storebro build --out /tmp/boat.FCStd` → exit code 0, `/tmp/boat.FCStd` is valid.

### Tests for US1 (parallel after T011)

- [x] T020 [P] [US1] `tests/geometry/test_cli_build_default.py`: `main(["build", "--out", str(tmp_path / "boat.FCStd")])` → exit code 0, file exists, byte_count > 0; stdout matches the data-model §3 success-summary format (regex match the "wrote fcstd to <path> (<bytes> bytes, SHA-256 <hex>)" pattern).
- [x] T021 [P] [US1] `tests/geometry/test_cli_build_byte_determinism.py` (SC-005): two back-to-back `main(["build", "--out", "..."])` calls with the same args → identical SHA-256 hashes in stdout summary. Delegates the determinism guarantee to spec 002's writer.
- [x] T022 [P] [US1] `tests/geometry/test_cli_build_invalid_layout.py`: `main(["build", "--out", str(tmp), "--layout", "BogusLayout"])` → exit code 1, stderr contains "error:" and the layout name. This is the SC-007 + clarify Q3 path: input error → exit 1.

**Checkpoint**: `uv run pytest -m requires_freecad tests/geometry/test_cli_build_default.py tests/geometry/test_cli_build_byte_determinism.py tests/geometry/test_cli_build_invalid_layout.py -v` green.

---

## Phase 4: User Story 2 - Discoverability (P2)

**Goal**: `storebro list-layouts` exposes all five canonical layouts.

**Independent Test**: Shell → `storebro list-layouts` → exit code 0, 5 lines covered.

Covered by T017 in the foundational tier (no FreeCAD needed). Add one polish test:

- [x] T023 [P] [US2] `tests/unit/test_cli_list_layouts_format.py`: `main(["list-layouts"])` stdout — each line has exactly 2 tab separators (3 columns: name, source, description); the third column is non-empty for every layout.

---

## Phase 5: User Story 3 - Info command (P3)

**Goal**: `storebro info` prints package + Python + FreeCAD + platform metadata.

**Independent Test**: Covered by T016 in the foundational tier.

- [x] T024 [P] [US3] `tests/unit/test_cli_info_format.py`: each printed line has the `Key: Value` shape (regex `^[A-Za-z][A-Za-z\- ]+: .+$` per line); the version line matches the pattern `freecad-storebro version: \d+\.\d+\.\d+`.

---

## Phase N: Polish & Cross-Cutting Concerns

- [x] T025 [P] `tests/geometry/test_cli_build_all_formats.py`: parameterize over `["fcstd", "step", "stl", "brep"]`; for each format, run `main(["build", "--format", <fmt>, "--out", str(tmp / f"boat.{ext}")])`; assert exit code 0 and file exists. Exhaustive --format coverage.
- [x] T026 [P] `tests/geometry/test_cli_build_all_layouts.py`: parameterize over the 5 canonical names; for each, run `main(["build", "--layout", <name>, "--out", str(tmp / f"{name}.FCStd")])`; assert exit code 0. Exhaustive --layout coverage.
- [x] T027 [P] `tests/geometry/test_cli_build_visual_signoff.py`: run `main(["build", "--out", "/tmp/storebro_v1_signoff.FCStd"])`; print MANUAL SIGNOFF reminder per project pattern (this is the v1.0.0 release-tag signoff).
- [x] T028 [P] `tests/unit/test_cli_public_docstrings.py` (FR-014): introspect `storebro.cli.__all__` (= `["main"]`); assert `main.__doc__` is non-empty and contains a `>>>` example block.
- [x] T029 [P] Write `docs/examples/cli_quickstart.sh` — a shell script with the 8 quickstart commands, executable, with comments.
- [x] T030 [P] Update `README.md` Quickstart section per FR-017: lead with the CLI invocation (`pip install freecad-storebro` → `storebro build --out boat.FCStd`); demote the Python-API quickstart to a secondary section.
- [x] T031 [P] Run `uv run ruff check src/ tests/ docs/`; fix any complaints.
- [x] T032 [P] Run `uv run mypy --strict src/`; fix any type errors.
- [x] T033 Full pytest `uv run pytest -v`; confirm all unit tests green, geometry tier skips cleanly without FreeCAD.
- [~] T034 Manual visual signoff: run `storebro build --out /tmp/storebro_v1_signoff.FCStd` on a FreeCAD-equipped host, open the result in FreeCAD GUI, eyeball the complete boat (hull + deck + 4 compartments) against `docs/references/Alternativ3.JPG`. Capture "Visually verified in FreeCAD: <version> on <OS>" PR description note per constitution V.
- [x] T035 [P] Update `PROJECT-BRIEF.md` Core Modules table to mark `storebro.cli` as "v1.0.0 (this spec)".
- [x] T036 Tick `specs/INDEX.md`: `[/] 005` → `[x] 005`. **This closes the v1.0.0 register.**

**Final checkpoint**: T033 + T034 green AND register has all 5 entries ticked. Tag `v1.0.0` per constitution.

---

## Dependencies & Execution Order

### Phase dependencies

- Phase 1 (Setup): needs spec 001-004 merged (master already at `bdb3f51` after spec 004)
- Phase 2 (Foundational): needs Phase 1; BLOCKS US1/US2/US3
- Phase 3 (US1): needs Phase 2; the MVP — `storebro build` works end-to-end
- Phase 4 + Phase 5: tests already covered in foundational tier; minor polish-tier supplements
- Phase N (Polish): needs all prior phases

### Per-task dependencies

- T002 → T003-T011 (all touch cli.py, __init__.py, or __main__.py — sequential)
- T012-T019a [P] after T011
- T020-T022 [P] after T011
- T023, T024 [P] after T011
- T025-T030 [P] in Polish
- T031-T032 [P] before T033
- T033 needs all test tasks complete
- T034 needs T027 (signoff file)
- T035 [P] in Polish
- T036 last

---

## Implementation Strategy

### MVP First (US1 — `storebro build`)

1. Setup (T001-T002)
2. Foundational (T003-T019)
3. US1 (T020-T022)
4. STOP + VALIDATE: run `storebro build --out /tmp/boat.FCStd` on a FreeCAD host
5. v1.0.0-alpha is shippable

### Incremental Delivery

1. Setup + Foundational → CLI scaffolding green
2. + US1 → `storebro build` works
3. + US2 + US3 → discovery + diagnostics covered (mostly already done in foundational)
4. + Polish → v1.0.0 visual signoff, register ticked, **tag v1.0.0**

### Solo Strategy

Direct push. Tag `v1.0.0` when T034 green + register has all 5 entries ticked. **This is the constitution's "all four v1.0 modules + CLI" milestone.**

---

## Notes

- Total tasks: 36 — smallest spec yet because the CLI is mostly orchestration of prior modules.
- The MVP (US1) is shippable at T022; the rest is polish + the v1.0.0 release dance.
- After v1.0.0 tag, the v0.2.0 PartDesign upgrade (tracked from spec 001) becomes the obvious next milestone.
