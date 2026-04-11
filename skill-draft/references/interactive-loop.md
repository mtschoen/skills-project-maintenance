# Interactive Loop

Use this wording when surfacing findings to the user in interactive mode. In fleet subagent mode, skip the prompts and return findings to the parent.

## Per-finding prompt

```
[ kind ] what
  evidence: <one line>
  recommendation: <rec> (confidence: <level>)
  rationale: <one line>
  -> I would: <action_on_approval>

[y] do it   [n] skip (log as rejected)   [s] skip silently   [e] edit action
```

- `y` -> execute, append to `user_authorized`
- `n` -> record the rejection with an optional reason, append to `rejected`
- `s` -> move on without recording
- `e` -> let the user modify `action_on_approval`, then re-prompt

## Batch mode

If the user says "approve all deletes" or similar, group findings by `recommendation` and confirm the whole bucket at once. Still log each individually.

## End of loop

Print the final action log with counts per bucket and a one-sentence natural-language report.
