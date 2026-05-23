# freecad-storebro — project reference

Loaded on demand from `CLAUDE.md`. Holds the verbose project-specific reference material that does not need to sit in-session.

## Source layout (src-layout)

```
src/storebro/
  __init__.py       # public API surface, version
  hull.py           # parametric hull
  deck.py           # deck, cabin trunk, hardtop, railings
  interior.py       # cabins, galley, heads, salon, Alternativ1-5
  export.py         # STEP / STL / BREP / .FCStd writers
  cli.py            # `storebro` CLI entry point
  fixtures/         # canonical parameter sets (YAML)
tests/
  unit/             # pure-Python, no FreeCAD runtime
  geometry/         # FreeCAD integration (pytest marker: requires_freecad)
docs/
  references/       # original Storebro cutaway drawings (read-only)
  examples/         # runnable example scripts
```

## Integrations

- FreeCAD Python API (sole external runtime dependency).
- Standard CAD interchange formats via FreeCAD: STEP, STL, BREP, .FCStd.
- No other integrations in scope for v1.0.

## CI/CD and release

- **CI on PR**: `uv run pytest`, `uv run ruff check .`, `uv run mypy src/` across Ubuntu + macOS × Python 3.11 + 3.12. FreeCAD installed in the runner.
- **Release**: tag `vX.Y.Z` on `main` → GitHub Actions builds wheel + sdist via `hatchling`, uploads to PyPI with `twine`. PyPI token in GitHub Secrets.
- **Changelog**: drafted by the local-LLM changelog hook from Conventional Commits, edited manually before tagging. Follows keep-a-changelog format.

## File organization

- **`src/storebro/`** — library source (src-layout).
- **`tests/`** — pytest tests; `unit/` and `geometry/` subdirs.
- **`docs/references/`** — original Storebro cutaway drawings (read-only assets).
- **`docs/examples/`** — runnable example scripts.
- **`scripts/`** — maintenance scripts and local-LLM hooks.
- **`.claude/skills/`** — project skills with SKILL.md (Agent Skills standard).
- **`.claude/agents/`** — subagents.
- **`.claude/rules/`** — auto-loaded rules with path-scoped frontmatter.
- **`.claude/docs/`** — reference material loaded on demand.
- **`CLAUDE.local.md`** — personal project settings, gitignored.

## Design principles (from constitution — non-negotiable)

1. **Parametric Everything** — no hard-coded geometry, every dimension is a named parameter.
2. **Reproducibility** — same params → byte-identical output. Determinism is enforced.
3. **FreeCAD-Idiomatic** — `Part` / `Sketch` / `Body`, never raw mesh hacks. Output stays editable in the FreeCAD GUI.
4. **Reference Fidelity** — defaults match the historical Storebro proportions within ±1% on principal dimensions.
5. **Test-Gated Releases** — `pytest` + `ruff` + `mypy --strict` are CI-enforced; visual verification is a PR description requirement.
6. **Public OSS by Default** — MIT, semver, all decisions in public.
7. **FreeCAD Version Discipline** — supported FreeCAD versions are explicit and CI-tested.

Authoritative source: `.specify/memory/constitution.md`.
