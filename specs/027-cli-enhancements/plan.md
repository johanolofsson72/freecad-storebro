# Implementation Plan: CLI Enhancements

**Branch**: master | **Date**: 2026-06-02 | **Spec**: [spec.md](./spec.md)

## Summary
Add `--json` (machine-readable build output) + hull overrides (`--loa`, `--beam`,
`--draft`, `--station-count`) to `storebro build`. The overrides build a
`HullParameters` only when any is provided (else None → defaults); validation is
inherited from `HullParameters` (out-of-range → existing non-zero CLI exit).
`--json` prints one `json.dumps` object instead of the human line. No geometry.

## Technical Context
- File: `src/storebro/cli.py` (build subparser + `_run_build`). Import
  `HullParameters` from `storebro.hull`. Tests: `tests/unit/`.
- Fully unit-testable (argparse + a mocked build chain capturing kwargs);
  one smoke build confirms end-to-end.

## Constitution Check
I parametric (overrides are named params) · II reproducible (deterministic JSON) ·
III n/a (no geometry) · IV n/a · V test-gated (unit) · VI MINOR (additive CLI) ·
VII n/a. **PASS.**

## Build sequence
1. build subparser: add `--json` (store_true), `--loa`/`--beam`/`--draft` (float),
   `--station-count` (int). Defaults None.
2. `_run_build`: if any hull override is not None, construct `HullParameters(...)`
   from the provided overrides (others default) and pass to `build_hull`; let
   `HullParameters` validation raise (mapped to the existing non-zero exit).
3. `_run_build`: if `args.json`, print `json.dumps({format,target_path,
   byte_count,sha256,version})`; else the existing human line.
4. Tests + version 1.6.0 -> 1.7.0.

## Complexity Tracking
No violations.
