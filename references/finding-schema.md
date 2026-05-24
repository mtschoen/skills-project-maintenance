# Finding Schema

Every finding surfaced by this skill (whether to the user or back to a fleet parent) must match this shape:

```json
{
  "kind": "<stable_identifier, e.g. 'todo_comment'>",
  "what": "<human-readable location or summary>",
  "path": "<repo-relative path, empty string if not file-specific>",
  "evidence": "<what the agent actually inspected to form its opinion>",
  "recommendation": "delete | merge_into:<target> | keep | needs_human_judgment | rename_master_to_main | report_only",
  "confidence": "high | medium | low",
  "rationale": "<one-line 'why this recommendation'>",
  "action_on_approval": "<exact shell/edit operation the agent will run>"
}
```

`projdash.get_maintenance_checklist` returns partial findings — they will have `kind`, `what`, `path`, `evidence`, `recommendation`, `confidence`. The skill must fill in `rationale` and `action_on_approval` after researching.

## Action log entry shape

Each entry appended to `automated` / `user_authorized` / `rejected`:

```json
{
  "kind": "...",
  "action": "<short description>",
  "detail": "<file, command, or data touched>",
  "reason": "<only for rejected — the user's stated reason or 'declined'>"
}
```
