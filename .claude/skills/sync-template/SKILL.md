---
name: sync-template
description: Syncs project configuration from the Claude Code template repo. Updates skills, agents, hooks, rules, and docs to match the latest template. Use when starting a new project or upgrading an existing project's Claude Code configuration.
disable-model-invocation: true
argument-hint: "[full|skills|agents|hooks|docs]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Sync from template repo

Update this project's Claude Code configuration from the template repo at `/Users/jool/repos/Claude`.

## What to sync

Argument controls scope. Default: `full`.

- `full` — sync everything below
- `skills` — only .claude/skills/
- `agents` — only .claude/agents/
- `hooks` — only .claude/settings.json hooks
- `docs` — only .claude/docs/

## Process

### 1. Read template files

Read these files from the template repo (`/Users/jool/repos/Claude`):

**Skills (`.claude/skills/`):**
- `code-review/SKILL.md`
- `explore-codebase/SKILL.md`
- `deploy-checklist/SKILL.md`
- `tla/SKILL.md`
- `allium/SKILL.md`
- `update-template/SKILL.md`
- `sync-template/SKILL.md`

**Agents (`.claude/agents/`):**
- `dotnet-reviewer.md`
- `security-scanner.md`
- `test-runner.md`
- `db-agent.md`

**Settings:** `.claude/settings.json`

**Rules (`.claude/rules/`):**
- `dotnet.md`
- `frontend.md`
- `security.md`
- `wordpress.md`
- `allium.md`
- `specs.md`
- `tests.md`
- `continuous-execution.md`
- `validation-followup.md`
- `feature-pipeline.md`
- `spec-register.md`

**Docs (`.claude/docs/`):**
- `skills.md`
- `workflows.md`
- `agents-templates.md`
- `conventions.md`
- `git.md`
- `security.md`
- `testing.md`
- `deployment.md`
- `stress-testing.md`
- `spec-testing-checklist.md`
- `project-template.md`
- `graphify.md`

**Scripts:**
- `scripts/tla-hook.sh`
- `scripts/allium-hook.sh`
- `scripts/tlc-cleanup.sh`
- `scripts/test-coverage-hook.sh`
- `scripts/continuous-execution-hook.sh`
- `scripts/stop-validation-hook.sh`
- `scripts/ui-design-hook.sh`
- `scripts/after-specify-hook.sh`
- `scripts/feature-pipeline-detect.sh`
- `scripts/spec-register-guard-hook.sh`
- `scripts/spec-register-orientation-hook.sh`
- `scripts/spec-md-coverage-reminder-hook.sh` (deterministic replacement for the legacy `type:"prompt"` spec-completeness hook; never blocks, suppresses reminder on carved-out test slices)
- `scripts/local-llm-call.sh` (telemetry funnel + auto-detect)
- `scripts/local-llm-detect.sh`
- `scripts/local-llm-stats.sh` (per-hook ROI reporter)
- `scripts/sync-local-llm-hooks.py` (deterministic settings.json trim — invoked in step 3)
- **Glob: every `scripts/local-llm-*-hook.sh`** — pull all matching files from the template. The template adds new local-LLM hook scripts over time; do not maintain a hand-edited list. Use `Glob` on `scripts/local-llm-*-hook.sh` against the template root and copy each file. Files present in the project but no longer in the template should also be removed (the template is the source of truth for the local-LLM hook script set).

### 2. Compare and merge

For each file:

1. If the file does not exist in the target project, copy it from the template
2. If the file exists, compare and identify differences
3. Preserve any project-specific customizations (marked with `# PROJECT-SPECIFIC` comments)
4. Update generic template content to match the latest version
5. Report what was changed

### 3. Settings.json merge rules

For `.claude/settings.json`:

**Step 3.1 — local-LLM hooks (deterministic, run the helper script):**

Once `scripts/sync-local-llm-hooks.py` has been copied from the template to the project (in step 1), invoke it from the project root:

```bash
python3 scripts/sync-local-llm-hooks.py /Users/jool/repos/Claude/.claude/settings.json
```

The script removes every `bash scripts/local-llm-*-hook.sh` entry from the project's `hooks` block and replaces them with the template's exact set. Non-local-LLM hook entries are preserved verbatim. The script is idempotent and prints what it changed; capture that output for the report in step 6.

Do NOT try to merge local-LLM hook entries by hand. Prose merge rules proved unreliable — the LLM running the sync hedged on "REPLACE" because it conflicts with "preserve project-specific customizations". The script removes the ambiguity.

**Step 3.2 — non-local-LLM hook entries and other settings (merge):**

For everything else in `settings.json`:
- MERGE `permissions.deny` lists (union of both).
- MERGE `permissions.allow` lists (union of both) — the template's allow list has expanded git/gh entries (`git push:*`, `git pull:*`, `git fetch:*`, `git checkout:*`, `git switch:*`, `git branch:*`, `git merge:*`, `git rebase:*`, `git stash:*`, `git tag:*`, `git restore:*`, `git cherry-pick:*`, `git status:*`, `git diff:*`, `git log:*`, `git show:*`, `git blame:*`, `git remote:*`, `git config --get:*`, `git config --list:*`, `gh pr:*`, `gh issue:*`, `gh repo view:*`, `gh run view:*`) which the project should pick up.
- If `permissions.ask` contains `Bash(git push *)`, REMOVE it (the template has moved this to allow). Other `permissions.ask` entries are preserved.
- MERGE non-local-LLM `hooks` entries — add missing hooks from the template, preserve existing custom hooks.
- Preserve any project-specific settings not in the template.

**Step 3.2.1 — inline-hook OVERWRITE exceptions (the template version wins):**

The merge rule above defaults to preserving customizations, but the following inline hooks have intentionally evolving behavior and MUST be replaced with the template version verbatim — do NOT preserve the project's older copy even if it differs. Match each by the unique grep pattern inside its command string and overwrite the entire hook object with the template version:

| Hook | Match by command containing | Why it must be overwritten |
|---|---|---|
| `UserPromptSubmit` speckit pipeline mandate | `speckit[.:_-](specify\|plan\|tasks\|implement)` or `speckit[.:_-](specify\|clarify\|plan\|tasks\|implement)` | Pipeline phase list evolves; new steps (e.g. `/clarify` between specify and allium, `/speckit.analyze` between tasks and implement) get added over time. The template version mandates `/clarify` immediately after `/specify` on every track and `/allium:elicit` after `/clarify` on full/light tracks — if the project's hook is missing the clarify step, overwrite it. |
| `UserPromptSubmit` speckit.analyze auto-apply | `speckit[.:_-](analyz\|analys)` | Behavior changed from "Reply suggest & apply for all" UX to immediate auto-apply + auto-chain to `/speckit.implement`. The old UX must be removed, not preserved. |
| `UserPromptSubmit` speckit.clarify auto-pick | `speckit[.:_-]clarif` | New hook (auto-picks Recommended). Add if missing; if present in any older form, replace with the template version. |
| `PostToolUse` Edit\|Write spec-completeness `type:"prompt"` | `INTERACTIVE UI` or `always approve and use systemMessage for the reminder` | The LLM-judgment version was observed BLOCKING edits on specs that legitimately carved destructive tests to a later slice (the prompt said "Do NOT block" but the model overrode it under pressure from CLAUDE.md / memory rules). Replace the entire prompt-hook object with the template's `type:"command"` entry pointing at `scripts/spec-md-coverage-reminder-hook.sh`. The new script is deterministic, can never issue a `permissionDecision`, and detects carve-out phrases ("carved to", "out-of-scope", "deferred to", etc.) to suppress false-positive reminders. |

If you find a project's `settings.json` has the OLD analyze hook (containing the phrase `Reply **suggest & apply for all**` or `analyze.md Step 8 default of asking before applying.`), this is the legacy version — overwrite it. Mention the overwrite in the step-6 report so the user knows the analyze behavior has flipped from semi-manual to fully auto.

If you find a project's `settings.json` has the OLD spec-completeness prompt hook (a `PostToolUse` entry with `type:"prompt"` whose prompt contains `INTERACTIVE UI` or `always approve and use systemMessage for the reminder`), this is the legacy LLM-judgment version that was incorrectly blocking edits — overwrite it with the deterministic command hook from the template. Mention the overwrite in the step-6 report so the user knows the spec-completeness check is now deterministic and no longer LLM-mediated.

### 3a. .gitignore additions

Ensure the project's `.gitignore` covers these patterns. Add any that are missing:

- `.claude/validation/`
- `.claude/.local-llm-*` (draft artifact files written by hooks)
- `.claude/local-llm-*.log` (per-project telemetry log)
- `.claude/local-llm-*.log.errors` (telemetry write-error log)
- `.claude/projects/` (per-user memory directory — never commit)
- `.claude/settings.local.json` (per-machine settings)

### 4. CLAUDE.md handling

Do NOT overwrite the project's CLAUDE.md. Instead:
- Check if the project's CLAUDE.md references `.claude/docs/skills.md` — if not, update the reference
- Check if `.claude/skills/` is mentioned in the file organization section — if not, add it
- Report any sections that differ from the template for manual review

### 5. Bootstrap caveat

If the project's `sync-template/SKILL.md` is OLDER than the template's, the current sync run is using outdated instructions. After the run, the project's SKILL.md will have been updated — but the changes you just made followed the OLD rules. Tell the user to re-run `/project-update` once more so the new rules take effect. If the SKILL.md was already current, this step is a no-op.

### 6. Report

After syncing, output a summary:

```
Synced from template (YYYY-MM-DD):
- [CREATED/UPDATED/SKIPPED] .claude/skills/code-review/SKILL.md
- [CREATED/UPDATED/SKIPPED] .claude/agents/dotnet-reviewer.md
- ...

Project-specific files preserved:
- .claude/agents/custom-agent.md
- ...

Manual review needed:
- CLAUDE.md: section X differs from template
- ...
```
