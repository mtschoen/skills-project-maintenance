# project-maintenance

A Claude Code skill that runs an end-of-session maintenance pass on a single repo: a researched, interactive checklist where every finding arrives with evidence, a recommendation, a confidence level, and the exact action on approval — and every action is logged.

## When it fires

"clean up this project", "run maintenance", "end of session cleanup", a health check on a repo, or fleet sweeps following `project-tracker.find_stale_maintenance`. Runs interactively (prompts per finding) or as a fleet subagent (returns findings to the parent).

## What it does

Delegates session hygiene to the `wrap` skill first, then covers the rare/audit-tier items wrap doesn't: default-branch renames, CLAUDE.md/AGENTS.md merging, missing README/LICENSE/.gitignore, dead code, large tracked files, stale memory, remote-lingering merged branches, empty directory husks, and multi-remote mirror drift. Bootstraps from `project-tracker.get_maintenance_checklist` and records the run via `project-tracker.record_maintenance_run`.

The authoritative spec is [`SKILL.md`](SKILL.md).

## Evals

`evals/` holds a runner/grader pair cloned from the docs-update harness, adapted for git-state scenarios: per-scenario `setup.sh` builds the planted repo state (branches, bare remotes, empty directories - state a checked-in seed cannot carry), the agent runs a maintenance pass via `claude -p`, and `probe.sh` captures post-run git state as key=value lines for grading. Outcome buckets: `actioned | surfaced | missed | over_actioned | no_op`. Five scenarios cover the audit checks: merged branch lingering on a remote, empty directory husks, multi-remote mirror drift, memory update-in-place, and a healthy-repo control where any "cleanup" is destructive. Harness mechanics are verified end-to-end; no n>=3 comparison run has been done yet.

**Repo:** <https://github.com/mtschoen/skills-project-maintenance>
