---
name: project-maintenance
description: "Use when the user asks for a maintenance pass, cleanup, end-of-session tidy-up, or health check on a repo. Triggers: 'clean up this project', 'run maintenance', 'end of session cleanup', fleet sweeps that follow projdash.find_stale_maintenance. Performs a researched + interactive checklist covering dirty trees, temp files, dead code, TODOs, stale memory, master->main rename, and CLAUDE.md/AGENTS.md merge. Every action is logged."
---

# Project Maintenance

End-of-session cleanup for a single repo. Works in two modes:

- **Interactive** — running in a user-facing session. Walk the checklist, research each finding, and prompt the user per item before taking action.
- **Fleet subagent** — running under `fleet-orchestration`. Produce the same researched findings but return them to the parent as structured data. Do not prompt — the parent drives the approval loop with the user.

**Relationship to the `wrap` skill:** For the per-session-hygiene portion of a maintenance pass, this skill delegates to `wrap`. PM's own checklist now covers only the rare/audit-tier items that do not belong in a session-close ritual (default-branch renames, CLAUDE/AGENTS merging, missing README/LICENSE/.gitignore, dead code, large tracked files, disk warnings). If you are running in an interactive session and the user wants a full end-of-session hygiene pass, prefer `/wrap` directly — it does the session-scoped work without PM's audit overhead.

## Operating principles

1. **Verify before delete.** Never delete untracked files. For tracked files, delete only when (a) the working tree is clean and (b) you can state why the file has served its purpose. *(Divergence from wrap: the wrap skill **may** delete untracked files with per-item approval. When PM's procedure delegates to wrap as step 0, wrap's looser rule applies during that step — do not let PM's stricter rule override it. PM's stricter rule still applies to everything PM does directly.)*
2. **Research before asking.** Each finding you surface must already include evidence, a recommendation, a confidence level, and the exact action you'd take on approval. The user should be able to y/n without opening any files themselves.
3. **Log everything.** Every automated action, every user-approved action, and every user-rejected proposal must appear in the final action log. Nothing the agent does should be invisible.
4. **Age is a hint, not a gate.** A day-old memory may already be obsolete; a month-old memory may still be load-bearing. Semantic checks (fix-implemented, dangling reference, superseded) decide staleness.

## Procedure

### 0. Delegate to wrap first

Before running any of PM's own checks, invoke the `wrap` skill on this project. Wrap's output (memory offload findings + per-session hygiene findings + action log) is part of this maintenance run. If wrap surfaces findings that overlap with anything in PM's remaining checklist, do not duplicate them — PM's residual checklist covers rare/audit items only.

In fleet-subagent mode, PM's fleet framing propagates through wrap's execution: wrap will produce findings-only output instead of prompting, because the agent running PM is already in that mode.

### 1. Bootstrap

Call `projdash.get_maintenance_checklist(name=<project>)` first. This returns the combined mechanical status in one shot and saves you most of the shell work.

Also call `projdash.find_stale_memory(days=30)` and scope the result to the current project.

### 2. Research each finding

For every item the checklist returned, enrich it into a full finding. The schema is in `references/finding-schema.md`. Never surface a finding without evidence you have actually inspected:

- **Temp files (untracked):** read the contents. Is this scratch still in progress? Was it copied somewhere? Recommend `delete` only if you can explain why it's spent.
- **Temp files (tracked):** use `git log -- <path>` to see when it last changed and why. If the work has landed elsewhere, recommend `delete` (it's recoverable).
- **Dead code:** grep for references to the symbol across the repo and the user's other projects. Don't recommend removal without evidence nothing consumes it.
- **TODO comments:** check whether the referenced condition still holds in current code. Often the fix is already in place and only the comment remains.
- **Stale memory:** read the memory, then verify each claim it makes against current code. If the referenced issue is fixed, recommend deletion with the commit/line that fixed it as evidence. If it's still valid, keep it.
- **CLAUDE.md + AGENTS.md coexist:** read both. Draft the merged AGENTS.md content. Draft the one-line CLAUDE.md alias (`See AGENTS.md — this file is kept as an alias for Claude Code compatibility.`). The merged content goes to the user for approval, not straight to disk.

### 3. Interactive approval loop (interactive mode only)

For each researched finding:

1. Show: **what / evidence / recommendation / confidence / action on approval**.
2. Ask: `[y]es / [n]o / [s]kip / [e]dit the action`.
3. Execute or record accordingly.
4. Append the outcome to the in-memory action log under one of: `automated`, `user_authorized`, `rejected`.

In fleet-subagent mode, skip the loop — return findings to the parent and let it drive approval.

### 4. Safe auto-fixes (Phase 2 only — see rollout)

When Phase 2 is enabled, the following may run without per-item prompting. Log every one under `automated`:

- **Rename `master` to `main`** — only on a clean working tree. Steps:
  - `git branch -m master main`
  - If a remote exists: `git push -u origin main`
  - If GitHub remote: `gh api -X PATCH repos/:owner/:repo -f default_branch=main`
  - `git push origin --delete master`
  - Grep the repo for hard-coded `master` references (CI, README badges, scripts) first; abort the auto-fix and escalate if any exist.
- **`git fetch --prune`**
- **Delete merged local branches** — `git branch --merged main | grep -v '^[* ] main$' | xargs -r git branch -d`
- **Breadcrumb update** — always runs; see step 5.

In Phase 1, treat these as researched findings too: surface them for approval, don't execute unasked.

### 5. Finalize

Build the summary:

```json
{
  "timestamp": "<ISO-8601 UTC>",
  "head": "<git HEAD sha>",
  "automated": [ ... ],
  "user_authorized": [ ... ],
  "rejected": [ ... ]
}
```

Call `projdash.record_maintenance_run(name=<project>, summary=<summary>)` to persist the mechanical log in `.maintenance.json`.

Return to the user (interactive) or parent (fleet):

- The same action log, plus a short natural-language report describing anything the agent found judgment-worthy: surprises, patterns across findings, suggested follow-ups.

## Rollout phase

Check `~/.claude/project-maintenance.phase` (file containing `1` or `2`). If absent, assume **Phase 1**. In Phase 1, skip the Phase-2-only auto-fixes above and treat them as researched findings.

## References

- `references/checklist.md` — the full checklist with each check's purpose
- `references/finding-schema.md` — exact shape of a finding dict
- `references/interactive-loop.md` — the prompt wording and decision tree
