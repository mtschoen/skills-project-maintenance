---
name: project-maintenance
description: "Use when the user asks for a maintenance pass, cleanup, end-of-session tidy-up, or health check on a repo. Triggers: 'clean up this project', 'run maintenance', 'end of session cleanup', fleet sweeps that follow projdash.find_stale_maintenance. Performs a researched + interactive checklist covering dirty trees, temp files, dead code, TODOs, stale memory, master->main rename, and CLAUDE.md/AGENTS.md merge. Every action is logged."
---

# Project Maintenance

End-of-session cleanup for a single repo. Works in two modes:

- **Interactive** — running in a user-facing session. Walk the checklist, research each finding, and prompt the user per item before taking action.
- **Fleet subagent** — running under `fleet-orchestration`. Produce the same researched findings but return them to the parent as structured data. Do not prompt — the parent drives the approval loop with the user.

**Relationship to the `wrap` skill:** For the per-session-hygiene portion of a maintenance pass, this skill delegates to `wrap`. PM's own checklist now covers only the rare/audit-tier items that do not belong in a session-close ritual (default-branch renames, the agent-instruction file convention — AGENTS.md source of truth with `@AGENTS.md` import pointers, missing README/LICENSE/.gitignore, dead code, large tracked files, disk warnings, and cross-project config drift — on-save linter hook, CI, aislop gate). If you are running in an interactive session and the user wants a full end-of-session hygiene pass, prefer `/wrap` directly — it does the session-scoped work without PM's audit overhead.

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
- **Branches:** before recommending branch deletion, run `git merge-base --is-ancestor <tip> <target>` to confirm the branch's tip commit is fully merged into the target branch. If the branch is **not** merged (the common case — agent work branches that were force-pushed, rebased, or abandoned), diff it against the target: `git diff <target>..<branch> --stat` at minimum. Generic commit messages ("chore: wrap session hygiene", "chore: cleanup") can mask significant unmerged WIP — the diff is the only way to know. If the diff is non-trivial, surface it to the user.
- **Agent-instruction file convention** (`agents_convention` findings): the canonical layout is **AGENTS.md as the single source of truth**, with `CLAUDE.md` and `GEMINI.md` as thin **`@AGENTS.md` import pointers**. Claude Code and Gemini CLI auto-expand the `@`-import into context; a plain markdown link does NOT load, so a linked pointer is flagged for upgrade. The exact target shapes (bare pointer vs. pointer + platform-specific addendum) and the test for what counts as "platform-specific" are in `references/cross-project-config.md`. Per finding kind:
  - `agents_source_missing` — a `CLAUDE.md`/`GEMINI.md` holds real content and no `AGENTS.md` exists. Draft: move the content into a new `AGENTS.md`, then rewrite the tool file to the `@AGENTS.md` pointer. The migrated content goes to the user for approval, not straight to disk.
  - `agents_pointer_divergent` — `AGENTS.md` exists but the tool file has its own content. Separate the genuinely platform-specific part (Claude-Code-only / Gemini-only rules) from the shared part. Fold the shared part into `AGENTS.md`; rewrite the tool file as `@AGENTS.md` plus the platform-specific addendum below the import line. If nothing is platform-specific (the common case), it becomes a bare `@AGENTS.md`.
  - `agents_pointer_weak_link` — the tool file points at `AGENTS.md` via a markdown link. Mechanical fix: replace the link line with `@AGENTS.md` (keep any addendum below it).
- **Docs content drift** (`docs_content_drift` findings): read each major doc surface (README, CLAUDE.md / AGENTS.md, other in-repo docs, inline doc comments) and compare to what the code currently does. Cite the stale statement and the line or commit that contradicts it - the finding must be specific enough that the user can y/n without opening the file themselves. Use the **docs-update** skill for the per-surface check. This is distinct from `agents_convention`, which validates import shape; `docs_content_drift` asks whether the content is still accurate.
- **Cross-project config drift** (`onsave_hook`, `ci`, `aislop` findings): a code repo missing a fleet-standard config. Each is **low confidence** — confirm the repo's languages and judge whether it warrants the config before surfacing (a tiny script repo may not need an aislop gate). Draft the fix from the canonical shape in `references/cross-project-config.md`:
  - `onsave_hook` — no `PostToolUse` Write|Edit linter hook in `.claude/settings.json`.
  - `ci` — no `.gitea/workflows/` or `.github/workflows/`.
  - `aislop` — no `.aislop/config.yml` quality gate.

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
- **Delete merged local branches** — only delete branches whose tips are **confirmed merged** into the target branch (`git branch --merged main` already guarantees this; each returned branch's tip is an ancestor of main, so its content is safe). **Do not use this auto-fix for branches that are not merged** — those must be researched per Step 2 (merge-base check + diff) and treated as Phase 1 findings.
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
