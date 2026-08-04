# Cross-project configuration conventions

The canonical *target shapes* for the fleet-wide conventions project-maintenance checks. When a
project-tracker `get_maintenance_checklist` finding points here, use these as
the draft you bring to the user — never apply straight to disk.

This list grows. **When a new cross-project convention is adopted, add its
target shape here AND a detection check in project-tracker's checklist
scanner so project-maintenance surfaces drift automatically.**

---

## Agent-instruction file convention

**AGENTS.md is the single source of truth.** It is the cross-tool standard
(Linux Foundation / Agentic AI Foundation; read natively by Codex, Cursor,
Copilot, opencode, Amp, …). Tool-specific files are **thin import pointers**:

- `CLAUDE.md` and `GEMINI.md` contain the import directive **`@AGENTS.md`**.
- Claude Code and Gemini CLI **auto-expand `@`-imports into context** at launch
  (relative path, max 4 hops). A plain markdown link — `See [AGENTS.md](AGENTS.md)`
  — does **not** load; the guidance is then silently absent from most sessions.
  That is why a linked pointer is flagged (`agents_pointer_weak_link`) for upgrade.
- A symlink (`ln -s AGENTS.md CLAUDE.md`) is the upstream recommendation but is
  sketchy on Windows — prefer the `@AGENTS.md` text pointer, which is
  git-portable and cross-platform.

### Target shapes

Bare pointer (the common case — nothing tool-specific):

```text
@AGENTS.md
```

Pointer **with a platform-specific addendum** (the allowed exception). The
import line comes first; genuinely tool-specific rules follow below it:

```text
@AGENTS.md

## Claude-only
- Worktrees live under `.claude/worktrees/`; reserve with `.worktree-reserved`.
- The on-save linter hook is configured in `.claude/settings.json`.
```

### What counts as "platform-specific" (stays in CLAUDE.md / GEMINI.md)

Keep below the import line ONLY content that is meaningless to other agents:
Claude Code hooks/settings paths, the `Skill` tool, `claude -p`, subagent
`model:` routing, `~/.claude/...` locations. **Everything else is shared and
belongs in AGENTS.md** — including quality-gate docs (aislop), build/test
commands, architecture notes, and coding conventions. A frequent mistake is
leaving the aislop section in CLAUDE.md; it is not Claude-specific — move it.

---

## On-save linter hook (`.claude/settings.json`)

A `PostToolUse` Write|Edit hook that lints each file as it is written. This is a
genuinely Claude-Code-specific mechanism (stays in `.claude/settings.json`, not
AGENTS.md). Canonical ruff + shellcheck form:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "f=$(jq -r '.tool_input.file_path // .tool_response.filePath // empty'); case \"$f\" in *.py) o=$(ruff check -q \"$f\" 2>/dev/null); [ -n \"$o\" ] && jq -n --arg c \"ruff:\\n$o\" '{hookSpecificOutput:{hookEventName:\"PostToolUse\",additionalContext:$c}}';; *.sh) o=$(shellcheck \"$f\" 2>/dev/null); [ -n \"$o\" ] && jq -n --arg c \"shellcheck:\\n$o\" '{hookSpecificOutput:{hookEventName:\"PostToolUse\",additionalContext:$c}}';; esac; exit 0"
          }
        ]
      }
    ]
  }
}
```

Repos with an aislop gate add a second hook entry of the same shape that runs
the pinned aislop binary. **Pin the aislop binary version in a hook — never
`@latest`** (a hook runs on every edit and `@latest` does a network check each
time). Tailor the `case` arms to the repo's actual languages.

---

## CI (`.gitea/workflows/` — Gitea Actions)

Automates the validate tier (lint + format check + tests) so regressions block
at merge. Minimal lint skeleton:

```yaml
name: lint
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install ruff
      - run: ruff check . && ruff format --check .
```

Scope paths explicitly (or rely on a root `pyproject.toml` `exclude`) so CI does
not run on generated/fixture trees. GitHub-mirrored repos use `.github/workflows/`.

---

## aislop quality gate (`.aislop/config.yml`)

Language-agnostic AI-slop gate (deterministic, scored 0–100). Per-edit hook +
PR/CI gate. Target config:

```yaml
ci:
  failBelow: 80          # tune to the repo's current pass rate
exclude:
  - "*/workspace/**"     # generated / fixture trees
```

CI step (pin a version, NOT `@latest`): `npx --yes aislop@<ver> ci .` — use the
CLI on Gitea Actions, not the GitHub composite action. Known Python false
positive: `ai-slop/unused-import` fires on `from __future__ import annotations`
(do NOT remove that line). aislop scores the **whole repo** — there is no
diff-only mode.

---

## `.claude/` settings tracking convention

Claude Code splits its config into two files:

- **`.claude/settings.json`** - shared, **committed**. Plugins, hooks, shared
  permissions: anything the whole team/fleet should get.
- **`.claude/settings.local.json`** - per-machine **local override**, must
  **never** be tracked. The permission-approval flow writes to it every session
  (each approved command becomes an `allow` entry), so a tracked copy churns on
  every run and can smuggle in an over-broad grant like `PowerShell(curl *)`.

The convention ignores the whole `.claude/` tree and re-includes only the shared
settings, so any local file (settings.local.json, state, scratch) is
auto-ignored:

```gitignore
.claude/*
!.claude/settings.json
```

Two distinct findings draw from this section:

- **`claude_settings_local_tracked`** (high, `recommendation: untrack`) -
  `.claude/settings.local.json` is tracked. The fix is **`git rm --cached
  .claude/settings.local.json`** then commit; the working copy stays on disk and
  is caught by the ignore rule going forward. `action_on_approval` is exactly
  that `git rm --cached` (do **not** delete the working file). Critically, a
  `.gitignore` rule added *after* the file was committed does NOT retroactively
  untrack it - git keeps tracking an already-tracked path regardless of a later
  ignore rule, so "the ignore line exists" does not clear this finding. The only
  fix is to untrack.
- **`missing_claude_settings_ignore`** (low, `recommendation:
  setup:claude_ignore`) - the repo tracks `.claude/settings.json` (so it is
  Claude-configured) but `.gitignore` lacks the two-line convention above. Draft
  is to append those two lines. Tolerate leading slashes (`/.claude/*`,
  `!/.claude/settings.json`). Note: a repo may also *intentionally* track other
  `.claude/` files (CLAUDE.md, AISLOP.md, notes/) as force-added-despite-ignore;
  that is fine and this check does not flag it - it only validates the gitignore
  shape, never the other tracked files.

---

## Full detail

- A repo's own `LINTER-SETUP.md` — the per-repo survey output, when present.
- The aislop section of the user's global `CLAUDE.md` - install rules and the
  pinned version.
