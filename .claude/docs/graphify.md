# Graphify — optional codebase knowledge graph

Graphify (`safishamsi/graphify`, MIT) is an external tool that parses a codebase locally with tree-sitter and writes a queryable graph of symbols, files, and call/import edges. Claude Code can then query the graph instead of re-reading source files when answering structural questions ("where is `X` defined", "who calls `Y`", "what connects auth to the database").

This doc is **opt-in per project**. The template repo does not install Graphify by default. Decide per project whether the payoff justifies the extra tool.

## When to install

| Situation | Install? |
| --- | --- |
| Project has < ~30 source files | No — overhead exceeds savings |
| Project has 50+ source files in a supported language | Yes |
| Project is short-lived (prototype, spike, demo) | No |
| Project is long-lived and Claude frequently does cross-file lookups | Yes |
| Project lives in a private repo with no outbound network | Yes — AST mode is fully offline |

If unsure: skip it. The template's existing flow (spec register, `/explore-codebase` skill, `Grep`/`Glob`) is sufficient for most work.

## Supported languages

`.cs .ts .tsx .js .jsx .mjs .py .go .rs .java .c .cpp .h .hpp .rb .kt .scala .php .swift .lua .zig .ps1 .ex .exs .m .mm .jl .vue .svelte .astro .groovy .gradle .dart .sql .sh .bash .json`

Covers the template's stack (.NET, React/TypeScript, Python). WordPress (`.php`) is covered. Razor (`.razor`, `.cshtml`) is not — Razor-heavy projects gain less.

## Install (project-scoped)

Run from the project root:

```bash
pip install graphifyy        # CLI is `graphify`, PyPI package is `graphifyy`
graphify install --project   # writes .claude/skills/graphify/SKILL.md + PreToolUse hook entry
graphify .                   # initial extraction → ./graphify-out/graph.json
graphify hook install        # post-commit + post-checkout git hooks for auto-rebuild
```

`graphify install --project` writes its own skill at `.claude/skills/graphify/SKILL.md` and adds a `PreToolUse` hook entry to the project's `.claude/settings.json` (or `settings.local.json`). Do not hand-write a wrapper skill in the template repo — Graphify ships its own and a parallel skill would conflict.

## What gets written

| Path | Purpose |
| --- | --- |
| `.claude/skills/graphify/SKILL.md` | The Graphify skill — Claude reads this when asked structural questions |
| `.claude/settings.json` (modified) | PreToolUse hook entry nudging Claude toward graph queries before file-search tool calls |
| `graphify-out/graph.json` | The graph itself (nodes, edges, communities) |
| `graphify-out/wiki/` | Human-readable index files |
| `.git/hooks/post-commit`, `.git/hooks/post-checkout` | Auto-rebuild on commit/checkout |

Add to `.gitignore` (the graph is a derived artifact and rebuilds on commit):

```
graphify-out/
```

Commit `.claude/skills/graphify/` and the settings.json hook entry so the team shares the integration; do not commit `graphify-out/`.

## Daily use

Once installed, Claude calls these via the skill without prompting. They also work directly in a terminal:

```bash
graphify query "what connects the auth service to the database?"
graphify path "UserService" "DatabasePool"     # shortest path between two symbols
graphify explain "RateLimiter"                  # neighborhood of one symbol
graphify . --update                             # re-extract changed files only
graphify export callflow-html                   # render a callflow diagram
```

## Privacy and cost

- **AST extraction is fully offline** — tree-sitter only, no LLM API key required, no code leaves the machine.
- **The `/graphify` skill** uses the active Claude Code session's model — no extra API key.
- **Headless `graphify extract --backend gemini|claude-cli`** requires the corresponding API key; only use when you explicitly want LLM-driven semantic enrichment.

## Integration with template conventions

- **Spec register (`specs/INDEX.md`)** — unchanged. Graphify is for navigation, not planning. Specs remain the source of truth for what to build.
- **Feature pipeline** — unchanged. `/specify → /clarify → ... → /implement` still runs in full. The graph helps `/implement` find existing call sites faster, nothing else.
- **Project workflow (solo vs team)** — unchanged. The git hooks rebuild the graph for whoever pushes; PR ceremony is unaffected.
- **`/explore-codebase` skill** — complementary, not a replacement. Use Graphify for symbol-level lookups, `/explore-codebase` for architecture-level orientation.

## Uninstall

```bash
graphify hook uninstall
rm -rf .claude/skills/graphify graphify-out
```

Then remove the Graphify entry from `.claude/settings.json` `hooks` block and the `graphify-out/` line from `.gitignore`.

## Source

- Repo: https://github.com/safishamsi/graphify
- Docs: https://graphify.net/
- License: MIT
