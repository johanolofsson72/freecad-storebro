#!/usr/bin/env python3
"""Sync local-LLM hook wiring in this project's .claude/settings.json
to match the template's exactly.

Why this exists: prose-only merge rules in the sync-template skill
("REPLACE the project's local-LLM hook entries with the template's")
proved unreliable — the LLM driving the sync hedged and left stale
hooks wired. This script makes the trim deterministic.

Behavior:
- Walks every hooks config in the project. Strips out every entry
  whose command matches `bash scripts/local-llm-*-hook.sh`. Other
  hook entries (project-specific or non-local-LLM template hooks)
  are preserved verbatim.
- Removes config blocks that become empty after the strip.
- Then appends fresh config blocks copied from the template, one per
  (event, matcher) pair that the template has local-LLM wiring for.
- Writes the result back to the project's settings.json with stable
  2-space indentation.

Usage:
    scripts/sync-local-llm-hooks.py <template-settings.json>

Run from the project root (where .claude/settings.json lives).
Idempotent — running twice produces the same result as running once.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

LOCAL_LLM_RE = re.compile(r"bash\s+scripts/(local-llm-[a-z0-9-]+-hook\.sh)")


def is_local_llm(hook: dict) -> bool:
    return bool(LOCAL_LLM_RE.search(hook.get("command", "")))


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: sync-local-llm-hooks.py <template-settings.json>",
            file=sys.stderr,
        )
        return 2

    template_path = Path(sys.argv[1])
    project_path = Path(".claude/settings.json")

    if not template_path.is_file():
        print(f"template not found: {template_path}", file=sys.stderr)
        return 2
    if not project_path.is_file():
        print(f"project settings not found: {project_path}", file=sys.stderr)
        return 2

    template = json.loads(template_path.read_text())
    project = json.loads(project_path.read_text())

    # 1. Collect template's local-LLM wiring grouped by (event, matcher).
    #    Multiple template config blocks under the same (event, matcher)
    #    flatten into one list — order preserved.
    template_wiring: dict[tuple[str, str], list[dict]] = {}
    for event, configs in template.get("hooks", {}).items():
        for config in configs:
            matcher = config.get("matcher", "")
            for h in config.get("hooks", []):
                if is_local_llm(h):
                    template_wiring.setdefault((event, matcher), []).append(h)

    # 2. Strip every local-LLM entry from every project config.
    removed_count = 0
    for event in list(project.get("hooks", {}).keys()):
        kept_configs: list[dict] = []
        for config in project["hooks"][event]:
            kept_hooks = []
            for h in config.get("hooks", []):
                if is_local_llm(h):
                    removed_count += 1
                else:
                    kept_hooks.append(h)
            if kept_hooks:
                new_config = {k: v for k, v in config.items() if k != "hooks"}
                new_config["hooks"] = kept_hooks
                kept_configs.append(new_config)
        if kept_configs:
            project["hooks"][event] = kept_configs
        else:
            del project["hooks"][event]

    # 3. Append fresh local-LLM blocks from template, one per (event, matcher).
    added_count = 0
    for (event, matcher), hooks in template_wiring.items():
        block: dict = {}
        if matcher:
            block["matcher"] = matcher
        block["hooks"] = hooks
        project.setdefault("hooks", {}).setdefault(event, []).append(block)
        added_count += len(hooks)

    project_path.write_text(json.dumps(project, indent=2) + "\n")

    print(f"removed {removed_count} local-LLM hook entries from project")
    print(f"added {added_count} local-LLM hook entries from template")
    return 0


if __name__ == "__main__":
    sys.exit(main())
