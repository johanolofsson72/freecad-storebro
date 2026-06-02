# Getting started with the Claude Code configuration

Step-by-step guide for using this template repo in a new or existing project. Works on **macOS, Linux, and Windows** (Git Bash or WSL).

---

## Cross-platform prerequisites

Before running any of the install steps below, verify these are present. The same template repo is used by developers on macOS, Linux (Debian/Ubuntu, Fedora/RHEL, Arch, openSUSE), and Windows. Pick the column that matches your machine.

| Prerequisite | macOS | Linux (apt) | Linux (dnf) | Linux (pacman) | Windows (Git Bash) |
|---|---|---|---|---|---|
| **bash** | built-in | built-in | built-in | built-in | Git for Windows ships it |
| **git** | `brew install git` | `sudo apt install git` | `sudo dnf install git` | `sudo pacman -S git` | Git for Windows installer |
| **python3** | `brew install python` | `sudo apt install python3 python3-pip` | `sudo dnf install python3 python3-pip` | `sudo pacman -S python python-pip` | `scoop install python` or python.org installer |
| **jq** | `brew install jq` | `sudo apt install jq` | `sudo dnf install jq` | `sudo pacman -S jq` | `scoop install jq` or `winget install jqlang.jq` |
| **pipx** | `brew install pipx && pipx ensurepath` | `sudo apt install pipx && pipx ensurepath` | `sudo dnf install pipx && pipx ensurepath` | `sudo pacman -S python-pipx && pipx ensurepath` | `scoop install pipx` or `winget install pipx` |
| **gh** (optional) | `brew install gh` | `sudo apt install gh` | `sudo dnf install gh` | `sudo pacman -S github-cli` | `scoop install gh` or `winget install gh` |

**Windows notes:**
- Run all bash commands in this guide from **Git Bash** (recommended) or **WSL2** (also fully supported). Native PowerShell will not execute the `.sh` scripts directly.
- Paths like `$HOME/.local/bin` work identically under Git Bash. If `pipx`-installed tools are not on PATH after install, add `export PATH="$HOME/.local/bin:$PATH"` to `~/.bashrc` (Git Bash) or `~/.profile` (WSL).
- For native PowerShell users, every `.sh` script in this template is callable via `bash scripts/foo.sh` once Git Bash is on PATH. There is no native PowerShell equivalent — that is intentional, since the template repo standardizes on bash to keep one source of truth.

If you skip the prerequisites, the install scripts fail with a clear error pointing at the missing tool — they don't silently degrade.

---

## New project

### 1. Copy all configuration files

Run the following from your new project's root directory. Set `TEMPLATE` to wherever you cloned this template repo on your machine.

```bash
# Path to the template repo — adjust for your platform/clone location
#   macOS:    TEMPLATE=$HOME/repos/Claude
#   Linux:    TEMPLATE=$HOME/repos/Claude
#   Win/Bash: TEMPLATE=$HOME/repos/Claude    (Git Bash translates ~/repos to /c/Users/<you>/repos)
TEMPLATE="$HOME/repos/Claude"

# Create directory structure
mkdir -p .claude/docs .claude/agents .claude/rules

# Copy main file
cp "$TEMPLATE/CLAUDE.md" ./CLAUDE.md

# Copy reference files
cp "$TEMPLATE/.claude/docs/conventions.md"      .claude/docs/
cp "$TEMPLATE/.claude/docs/deployment.md"       .claude/docs/
cp "$TEMPLATE/.claude/docs/git.md"              .claude/docs/
cp "$TEMPLATE/.claude/docs/project-template.md" .claude/docs/
cp "$TEMPLATE/.claude/docs/security.md"         .claude/docs/
cp "$TEMPLATE/.claude/docs/skills.md"           .claude/docs/
cp "$TEMPLATE/.claude/docs/testing.md"          .claude/docs/
cp "$TEMPLATE/.claude/docs/workflows.md"        .claude/docs/
cp "$TEMPLATE/.claude/docs/agents-templates.md" .claude/docs/

# Copy hooks
cp "$TEMPLATE/.claude/settings.json" .claude/settings.json

# Copy path-scoped rules (pick the relevant ones)
cp "$TEMPLATE/.claude/rules/security.md"  .claude/rules/    # Always
cp "$TEMPLATE/.claude/rules/dotnet.md"    .claude/rules/    # .NET projects
cp "$TEMPLATE/.claude/rules/frontend.md"  .claude/rules/    # Frontend
cp "$TEMPLATE/.claude/rules/wordpress.md" .claude/rules/    # WordPress (remove if not needed)

# Copy agents (pick the relevant ones)
cp "$TEMPLATE/.claude/agents/dotnet-reviewer.md"  .claude/agents/  # .NET
cp "$TEMPLATE/.claude/agents/security-scanner.md" .claude/agents/  # Always
cp "$TEMPLATE/.claude/agents/test-runner.md"      .claude/agents/  # Always
cp "$TEMPLATE/.claude/agents/db-agent.md"         .claude/agents/  # EF Core + SQLite
```

### 2. Fill in project-specific information

Open `CLAUDE.md` and update the **Project description** section:

```markdown
## Project description

This is a **[PROJECT NAME]** — [short description of what the system does and for whom].

> **On project start:** Fill in core principles, architecture, and dev environment in `.claude/docs/project-template.md`
```

### 3. Fill in the project template

Open `.claude/docs/project-template.md` and fill in ALL sections marked with `[FILL IN]`:

- **Core principles** — rules that must NEVER be broken (e.g., "All data MUST be tenant-scoped")
- **Project name and purpose** — one line to orient Claude
- **Architecture** — ASCII diagram of system components
- **Key patterns** — authentication, database access, API patterns, error handling, state management, domain terms
- **Start command** — e.g., `dotnet run --project src/AppHost`
- **URLs** — e.g., `https://localhost:5001`
- **Known workarounds** — IPv6 issues, certificates, etc.

### 4. Remove what is not relevant

- Not WordPress? → Remove `.claude/rules/wordpress.md`
- Not .NET? → Remove `.claude/rules/dotnet.md` and `.claude/agents/dotnet-reviewer.md`
- Not EF Core/SQLite? → Remove `.claude/agents/db-agent.md`
- Different deploy environment? → Update `.claude/docs/deployment.md` with your own details

### 5. Commit

```bash
git add CLAUDE.md .claude/
git commit -m "feat: Add Claude Code configuration"
```

### 6. (Optional) Bootstrap Graphify — codebase knowledge graph

If the project has 30+ source files in a supported language (`.cs/.ts/.tsx/.js/.py/.go/.rs/.java/...`), install Graphify so Claude can query the AST graph instead of grepping raw files. The bootstrap script is cross-platform and self-detects the package manager:

```bash
bash scripts/graphify-bootstrap.sh
```

Cross-platform fallback (run only if the bootstrap exits non-zero pointing at a missing tool):

| Platform | Manual install |
|---|---|
| macOS | `brew install pipx && pipx ensurepath && pipx install graphifyy` |
| Debian/Ubuntu | `sudo apt install -y pipx && pipx ensurepath && pipx install graphifyy` |
| Fedora/RHEL | `sudo dnf install -y pipx && pipx ensurepath && pipx install graphifyy` |
| Arch | `sudo pacman -S python-pipx && pipx ensurepath && pipx install graphifyy` |
| openSUSE | `sudo zypper install python3-pipx && pipx ensurepath && pipx install graphifyy` |
| Windows Git Bash | `scoop install pipx && pipx install graphifyy` (or `winget install pipx`) |

After `graphify` is on PATH, run:

```bash
graphify install --project   # writes .claude/skills/graphify/SKILL.md + PreToolUse nudge hook
graphify update .            # AST-only initial extraction (no API key needed) → graphify-out/graph.json
graphify hook install        # post-commit + post-checkout auto-rebuild hooks
```

The token-savings telemetry hook (`scripts/graphify-fire-hook.sh`) logs every query to `.claude/graphify-fire.log`. Read it with:

```bash
bash scripts/graphify-stats.sh           # this project
bash scripts/graphify-stats.sh --all     # aggregate across ~/repos/* and ~/Projects/*
```

See `.claude/docs/graphify.md` for full details on when to install, supported languages, and uninstall.

---

## Existing project

### Option A: Copy everything (recommended)

Same steps as for new project above. If the project already has a `CLAUDE.md`, make a backup first:

```bash
cp CLAUDE.md CLAUDE.md.backup
```

Then copy the template files and merge the existing content with the new.

### Option B: Incremental update

If you only want to add what is missing:

```bash
TEMPLATE="$HOME/repos/Claude"  # works on macOS, Linux, and Windows Git Bash

# 1. Hooks (if .claude/settings.json is missing)
cp "$TEMPLATE/.claude/settings.json" .claude/settings.json

# 2. Path-scoped rules (if .claude/rules/ is missing)
mkdir -p .claude/rules
cp "$TEMPLATE/.claude/rules/"*.md .claude/rules/

# 3. Agents (if .claude/agents/ is missing)
mkdir -p .claude/agents
cp "$TEMPLATE/.claude/agents/"*.md .claude/agents/

# 4. Reference files (if .claude/docs/ is missing)
mkdir -p .claude/docs
cp "$TEMPLATE/.claude/docs/"*.md .claude/docs/
```

Then open `CLAUDE.md` and add the missing sections (copy from the template).

### Option C: Use `/init` as starting point

Run `/init` in the project — Claude generates a starter CLAUDE.md based on the project structure. Then supplement with the template repo's files:

```bash
TEMPLATE="$HOME/repos/Claude"  # works on macOS, Linux, and Windows Git Bash
cp "$TEMPLATE/.claude/settings.json" .claude/settings.json
cp -r "$TEMPLATE/.claude/rules/" .claude/rules/
cp -r "$TEMPLATE/.claude/agents/" .claude/agents/
cp -r "$TEMPLATE/.claude/docs/" .claude/docs/
```

### Option D: Let Claude do it

Start a Claude Code session in the project and type:

```
Update or create CLAUDE.md with the template files from /Users/jool/repos/Claude.
Copy hooks, rules, agents, and docs.
Fill in project name: [YOUR PROJECT NAME]
Fill in purpose: [WHAT THE PROJECT DOES]
Remove what is not relevant for this project.
```

---

## Post-installation checklist

- [ ] `CLAUDE.md` — Project description filled in
- [ ] `.claude/docs/project-template.md` — All `[FILL IN]` placeholders filled
- [ ] `.claude/settings.json` — Hooks configured
- [ ] `.claude/rules/` — Only relevant rules (remove unused)
- [ ] `.claude/agents/` — Only relevant agents
- [ ] `.claude/docs/deployment.md` — Updated with project deploy info
- [ ] `.gitignore` — Contains `CLAUDE.local.md` and `temp/`
- [ ] Skills installed — Run the installation script from `.claude/docs/skills.md`

---

## File overview

```
your-project/
├── CLAUDE.md                          ← Main file (~155 lines, always loaded)
├── CLAUDE.local.md                    ← Personal, gitignored (create as needed)
├── .claude/
│   ├── settings.json                  ← Hooks (deterministic rules)
│   ├── docs/                          ← Reference files (loaded on demand)
│   │   ├── project-template.md        ← Project-specific info (FILL IN!)
│   │   ├── conventions.md             ← Code style
│   │   ├── security.md                ← Security rules
│   │   ├── git.md                     ← Git conventions
│   │   ├── testing.md                 ← Testing conventions
│   │   ├── deployment.md              ← CI/CD and deploy
│   │   ├── workflows.md               ← Hooks, subagents, plugins
│   │   ├── agents-templates.md        ← Agent templates (reference)
│   │   └── skills.md                  ← Skills and plugins
│   ├── rules/                         ← Auto-loaded, path-scoped
│   │   ├── security.md                ← *.cs, *.cshtml, *.razor
│   │   ├── dotnet.md                  ← *.cs, *.csproj
│   │   ├── frontend.md                ← *.html, *.css, *.js, *.tsx
│   │   └── wordpress.md               ← *.php, wp-content/**
│   └── agents/                        ← Subagents
│       ├── dotnet-reviewer.md         ← Code review (sonnet)
│       ├── security-scanner.md        ← Security scanning (sonnet)
│       ├── test-runner.md             ← Test execution (haiku)
│       └── db-agent.md                ← Database operations (inherit)
```

---

## FAQ

**Do I need to fill in all placeholders?**
Yes. Repo-specific customization yields 2x better results according to Arize ML research. The more concrete information Claude has about your project, the better the code produced.

**Can I remove files I don't need?**
Absolutely. Remove anything that is not relevant. A WordPress rule in a pure .NET project just takes up space without contributing.

**Should .claude/settings.json be committed?**
Yes, it is shared with the team. Personal settings go in `.claude/settings.local.json` (gitignored).

**What is the difference between rules/ and docs/?**
- `rules/` is auto-loaded every session with high priority, filtered by which files you are working with
- `docs/` is loaded only when Claude determines they are needed (or you reference them with `@`)
