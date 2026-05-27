# project-maintenance

A Claude Code skill that runs an end-of-session maintenance pass on a single repo: a researched, interactive checklist where every finding arrives with evidence, a recommendation, a confidence level, and the exact action on approval — and every action is logged.

## When it fires

"clean up this project", "run maintenance", "end of session cleanup", a health check on a repo, or fleet sweeps following `projdash.find_stale_maintenance`. Runs interactively (prompts per finding) or as a fleet subagent (returns findings to the parent).

## What it does

Delegates session hygiene to the `wrap` skill first, then covers the rare/audit-tier items wrap doesn't: default-branch renames, CLAUDE.md/AGENTS.md merging, missing README/LICENSE/.gitignore, dead code, large tracked files, and stale memory. Bootstraps from `projdash.get_maintenance_checklist` and records the run via `projdash.record_maintenance_run`.

The authoritative spec is [`SKILL.md`](SKILL.md).

**Repo:** <https://github.com/mtschoen/skills-project-maintenance>
