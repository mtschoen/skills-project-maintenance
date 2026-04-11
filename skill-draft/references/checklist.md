# Project Maintenance Checklist

Every item below maps to either a `projdash` query (preferred — fast + reliable) or an agent-run inspection. Every item produces zero or more findings; findings are researched before surfacing.

**Note:** Rows for per-session hygiene (temp files, uncommitted/unpushed, stale memory, merged branches, stale worktrees) have been moved to the `wrap` skill. PM invokes wrap as step 0 of its procedure, and wrap's findings are part of a PM run. This table now contains only the rare/audit-tier checks PM owns directly.

| Check | Source | Auto-fix (Phase 2) | Research required |
|---|---|---|---|
| Default branch is `master` | `projdash.get_maintenance_checklist.default_branch` | Rename to `main` (clean tree only) | Grep for `master` in CI/README/scripts before rename |
| TODO/FIXME/XXX | `…todo_comments` | — | Verify the referenced issue isn't already fixed |
| CLAUDE.md + AGENTS.md coexist | `…claude_agents` | — | Draft merged AGENTS.md + CLAUDE.md alias |
| Missing README/LICENSE/.gitignore | `…hygiene` | — | Suggest MIT for missing LICENSE; offer minimal template for others |
| Dead code | agent grep | — | Confirm no references anywhere in repo/fleet |
| Accidentally tracked large files | `git ls-files` + size | — | Verify no longer needed; propose `git rm` + `.gitignore` |
| Disk warnings | projdash disk badge | — | Report only |
