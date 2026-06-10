# Project Maintenance Checklist

Every item below maps to either a `project-tracker` query (preferred — fast + reliable) or an agent-run inspection. Every item produces zero or more findings; findings are researched before surfacing.

**Note:** Rows for per-session hygiene (temp files, uncommitted/unpushed, stale memory, merged branches, stale worktrees) have been moved to the `wrap` skill. PM invokes wrap as step 0 of its procedure, and wrap's findings are part of a PM run. This table now contains only the rare/audit-tier checks PM owns directly.

| Check | Source | Auto-fix (Phase 2) | Research required |
|---|---|---|---|
| Default branch is `master` | `get_maintenance_checklist.default_branch` | Rename to `main` (clean tree only) | Grep for `master` in CI/README/scripts before rename |
| TODO/FIXME/XXX | `…todo_comments` | — | Verify the referenced issue isn't already fixed |
| Branches (unmerged) | `git branch` inspection | — | Run `git merge-base --is-ancestor <tip> <target>`; if not merged, diff first (`git diff <target>..<branch> --stat`). Generic messages ("chore: wrap session hygiene") can mask significant WIP. |
| Merged branch lingering on remote | `git ls-remote --heads <remote>` per merged branch | - | Local delete alone leaves the remote copy; `git fetch --prune` never deletes the remote branch itself. Propose `git push <remote> --delete <branch>` |
| Empty directory husks | `find . -type d -empty -not -path "./.git/*"` | - | Invisible to `git status` (git tracks files, not directories). No file content at risk; confirm the name doesn't signal reserved future use before removing |
| Multi-remote mirror drift | `git rev-list --left-right --count <r1>/main...<r2>/main` after fetching both remotes | - | Identify orphan commits on each side; recommend merge-reconcile, not force-push. Drift usually comes from one-way automation pushing to a single host |
| Agent-instruction file convention | `…agents_convention` (list) | — | AGENTS.md = source of truth; CLAUDE.md/GEMINI.md = `@AGENTS.md` import pointers. Split platform-specific from shared content; draft per `references/cross-project-config.md` |
| On-save linter hook missing | `…onsave_hook` | — | Confirm repo languages; offer the canonical `.claude/settings.json` hook (low confidence) |
| CI missing | `…ci` | — | Offer the Gitea/GitHub Actions lint+test workflow; defer to user on whether repo warrants CI |
| aislop gate missing | `…aislop` | — | Offer `.aislop/config.yml`; note the `from __future__ import annotations` false positive |
| Missing README/LICENSE/.gitignore | `…hygiene` | — | Suggest MIT for missing LICENSE; offer minimal template for others |
| Dead code | agent grep | — | Confirm no references anywhere in repo/fleet |
| Accidentally tracked large files | `git ls-files` + size | — | Verify no longer needed; propose `git rm` + `.gitignore` |
| Disk warnings | project-tracker disk badge | — | Report only |
| Docs content drift (`docs_content_drift`) | agent read + code compare | — | Read each major doc surface (README, CLAUDE.md / AGENTS.md, other in-repo docs, inline doc comments) and compare claimed behavior to current code. Distinct from `agents_convention`, which validates the AGENTS.md import **shape** - this check asks whether the **content** of those files still matches current code. Low confidence by default (the agent must actually read the doc and compare it to the code). Cite the stale statement and the code that contradicts it. Use the **docs-update** skill for the per-surface check. |

The `agents_convention`, `onsave_hook`, `ci`, and `aislop` checks all draft their fixes from `references/cross-project-config.md` — the canonical target shapes for fleet-wide conventions.
