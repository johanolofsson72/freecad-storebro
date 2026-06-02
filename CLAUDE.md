# CLAUDE.md

## Critical rules (READ FIRST)

- **ALWAYS** read the code first — base ALL conclusions on evidence from the codebase, not assumptions.
- **ALWAYS** verify with `uv run pytest`, `uv run ruff check .`, and `uv run mypy src/` before claiming anything is "done".
- **ALWAYS** use the Edit tool for surgical changes — never copy entire files.
- **ALWAYS** run the full pipeline (`/specify` → `/clarify` → `/allium:elicit` → `/plan` → `/tasks` → `/speckit.analyze` → `/implement` → tests → `/tla`) for any non-trivial feature, refactor, or fix. The pipeline is ONE task — never stop between phases to ask permission. `/clarify` runs on ALL tracks (auto-pick recommended) and catches underspecified requirements before `/plan`/`/tasks` lock them in; `/allium:elicit` runs on full/light tracks only. Trivial-fix bypass requires an explicit classification sentence. See `.claude/rules/feature-pipeline.md`. This is a **BLOCKING REQUIREMENT**.
- **ALWAYS** consult `specs/INDEX.md` (the spec register) before starting feature work. Work the next unchecked spec end-to-end (pipeline → commit → push → tick the register), then stop with a status summary. The only legitimate mid-spec stops are real ambiguity, hard blockers, Allium/TLA+ findings, or a register-rewrite proposal. See `.claude/rules/spec-register.md`. This is a **BLOCKING REQUIREMENT**.
- **ALWAYS** run generated text through the `humanizer` skill via the Skill tool BEFORE delivering to humans (documentation, commit messages, PR descriptions, README, CHANGELOG). This is a **BLOCKING REQUIREMENT**.
- **ALWAYS** follow existing patterns in the codebase — look at similar functions first.
- **ALWAYS** treat geometry as PARAMETRIC — no magic numbers in function bodies. Every dimension is a named parameter with a default. See constitution principle I.
- **ALWAYS** preserve REPRODUCIBILITY — same inputs must produce byte-identical outputs. No timestamps in artifacts, no env-dependent paths. See constitution principle II.
- **ALWAYS** stay FreeCAD-idiomatic — use `Part`, `Sketch`, `Body`, `PartDesign`. No raw mesh generation outside the explicit mesh-export adapters. See constitution principle III.

## Execution mode

### Autonomous mode (NON-INTERACTIVE)

- Act immediately without waiting for confirmation.
- Missing information is not a blocker — make reasonable assumptions and continue.
- Errors should be handled and fixed independently.
- Questions are allowed ONLY for architecture decisions or requirement interpretations that cannot reasonably be assumed.
- **Max 3 attempts per problem** — if the same approach fails 3 times, run `/clear` and try a completely different strategy with a better prompt.

### Anti-stall rule

If no clear task is found — pick the most likely task and act. Stagnation is treated as failure.

### Hook recovery rule

When a hook stops continuation or provides feedback: acknowledge the feedback, handle it (fix the issue OR explain why it's not applicable), and **continue working autonomously**. Never stop and wait silently after hook feedback — that is treated as stalling.

### Interview pattern

For larger features: interview the developer with `AskUserQuestion` before implementation. Ask about technical implementation, edge cases, and tradeoffs. Then write a spec before coding begins.

## Priority order

1. **Correctness** — geometry must be reproducible and dimensionally faithful
2. **Security** — never compromise (no arbitrary code eval in fixtures, no unsafe pickle, no shell injection in CLI)
3. **Simplicity** — minimum necessary complexity
4. **Readability** — clear code over clever code
5. **Performance** — optimize only when needed; geometry build time is fine at "human-scale" seconds

# PROJECT-SPECIFIC

## Project description

**freecad-storebro** is an open-source Python library that builds a parametric
3D model of a vintage Storebro motor yacht inside FreeCAD. Given hull
parameters (LOA, beam, draft, etc.) and one of five canonical interior layouts,
it generates a fully editable `.FCStd` document plus standard CAD exports
(`.step`, `.stl`, `.brep`).

Core flow: **parameters → FreeCAD B-rep geometry → editable .FCStd + exports**

**GitHub**: https://github.com/johanolofsson72/freecad-storebro
**PyPI**: `freecad-storebro` (import as `storebro`)
**Constitution**: see [.specify/memory/constitution.md](.specify/memory/constitution.md)

### Why this exists

- No public, parametric digital model of vintage Storebro yachts exists today.
- Restorers, scale modelers, and FreeCAD scripters need editable B-rep geometry, not flat PNGs or one-off `.FCStd` snapshots.
- Build it once, ship it permissively (MIT), let the niche community extend.

### Design principles

Seven non-negotiable principles drive every design decision (parametric, reproducible, FreeCAD-idiomatic, reference-faithful, test-gated, public OSS, FreeCAD-version-disciplined). Authoritative source: `.specify/memory/constitution.md`. Summary: `.claude/docs/project.md`.

## Language

- Communicate in **English** in conversations, commit messages, documentation, and code.
- Code, variable names, and technical terms are in English.
- Comments in code are in English.

## Tech stack

- **Python 3.11+** — minimum runtime (matches FreeCAD 1.1's bundled Python)
- **FreeCAD 1.1+** — geometry runtime (declared as a supported version range)
- **uv** — dependency management and virtualenv
- **hatchling** — PEP 517 build backend
- **pytest** — tests, with geometry property assertions
- **ruff** — lint + format (replaces black/isort/flake8)
- **mypy --strict** — static typing
- **GitHub Actions** — CI: Ubuntu + macOS × Python 3.11 + 3.12
- **PyPI** — distribution (`freecad-storebro`)

Source layout, integrations, CI/CD, and release details: `.claude/docs/project.md`.

## Workflow

### Complexity assessment

- **Trivial** (one file, obvious fix, no new geometry) → execute immediately
- **Medium** (2-5 files, clear scope, parameter additions) → brief planning, then execute
- **Complex** (new module, new geometry surface, API change) → full speckit pipeline (`/specify` → `/clarify` → `/allium:elicit` → `/plan` → `/tasks` → `/implement`)

### Plan → Implement → Verify

1. **Explore** — read existing module(s), understand parameter patterns.
2. **Plan** — for medium/complex: use Plan Mode (Shift+Tab) to write a plan before implementation.
3. **Implement** — write parametric code. Reuse existing parameter naming. No magic numbers.
4. **Verify** — `uv run pytest && uv run ruff check . && uv run mypy src/`. Then open the generated `.FCStd` in the FreeCAD GUI and eyeball it.
5. **Commit** — Conventional Commit in English: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`. Details in `.claude/docs/git.md`.

## Verification and grounding

> Giving Claude ways to verify its own work is the single most important measure for quality. — Anthropic Best Practices

- **IMPORTANT:** ALWAYS read relevant files BEFORE answering about the codebase. NEVER guess.
- Run tests after every implementation.
- Run individual tests over the full suite for faster feedback: `uv run pytest tests/unit/test_hull.py::test_loa -x`.
- For geometry tests requiring FreeCAD: `uv run pytest -m requires_freecad`.

### Definition of "implemented"

NEVER say something is "implemented" or "done" until:

1. All **pytest** tests pass (`uv run pytest`).
2. **ruff** is clean (`uv run ruff check .`).
3. **mypy --strict** is clean (`uv run mypy src/`).
4. For geometry changes: the generated `.FCStd` has been opened in the FreeCAD GUI and visually verified. The PR description includes: "Visually verified in FreeCAD: \<version\> on \<OS\>".
5. For public-API changes: a runnable example exists in `docs/examples/` or as a docstring example.
6. The code is assessed as **100% functional**.

If tests cannot be run (missing FreeCAD on the agent's machine), clearly inform about this and run unit-only suite: `uv run pytest -m "not requires_freecad"`.

## Context management

- During compaction: ALWAYS preserve modified files, error messages verbatim, debugging steps, and test commands.
- Use subagents for exploration and research — keep the main context clean.
- Use `/clear` between unrelated tasks.
- Use `/compact <focus>` for controlled compaction.
- Break down large tasks into discrete subtasks.
- After 2 failed fixes of the same problem: `/clear` and write a better prompt from scratch.

## Commands

```bash
uv sync                                  # Install dependencies into .venv
uv run pytest                            # Run all tests
uv run pytest -m "not requires_freecad"  # Unit tests only (no FreeCAD needed)
uv run pytest -m requires_freecad        # Geometry integration tests
uv run pytest tests/unit/test_hull.py::test_loa -x  # Single test, fail-fast
uv run ruff check .                      # Lint
uv run ruff format .                     # Format
uv run mypy src/                         # Static type check
uv run storebro build --layout 3 --out boat.FCStd  # CLI: build Alternativ3 layout
uv build                                 # Build wheel + sdist
```

## Principles

- **YAGNI** — only build what is needed now. v1.0 is hull + deck + interior + export/CLI. Propulsion, render pipeline, generative variants live in v1.1+.
- **Fail fast** — clear error messages with context. Invalid parameters raise `ValueError` with the offending value and the valid range.
- **DX** — code should be readable without comments. Good naming is usually enough. Every public function has a one-line docstring and at least one example.

## Reference files (loaded on demand)

Read these files WHEN you need them — do not load everything upfront:

- **New project start** or architecture questions → `.claude/docs/project-template.md`
- **Code style, naming, forbidden patterns** → `.claude/docs/conventions.md`
- **Security questions** → `.claude/docs/security.md`
- **Git commit/branch/PR** → `.claude/docs/git.md`
- **Hooks, subagents, plugins, sessions** → `.claude/docs/workflows.md`
- **Creating new agents** → `.claude/docs/agents-templates.md`
- **Skills, SKILL.md format, Agent Skills standard** → `.claude/docs/skills.md`
- **Tests** → `.claude/docs/testing.md`
- **Spec testing checklist** → `.claude/docs/spec-testing-checklist.md`
- **Feature pipeline** → `.claude/rules/feature-pipeline.md`
- **Spec register** → `.claude/rules/spec-register.md`
- **Project source layout, CI/CD, release** → `.claude/docs/project.md`
- **Codebase knowledge graph (opt-in per project)** → `.claude/docs/graphify.md`

## Iterative improvement

- If the same mistake repeats: suggest a new rule for CLAUDE.md or a hook that prevents it.
- Every code review comment is a signal that the agent lacked context — update CLAUDE.md.
- Edit existing files over creating new ones.
- Keep this file focused — if an instruction can be removed without Claude making errors, remove it.

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
at `specs/016-ds-variant-superstructure/plan.md`.
<!-- SPECKIT END -->

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
