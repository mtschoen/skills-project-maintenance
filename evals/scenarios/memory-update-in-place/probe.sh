#!/usr/bin/env bash
# Emit key=value lines describing post-run state for the grader.
set -euo pipefail
cd workspace

note=".claude/memory/handoff-followups.md"
note_exists=false
if [ -f "$note" ]; then
  note_exists=true
fi
echo "note_exists=$note_exists"

open_items_retained=false
if [ -f "$note" ] && grep -q "parse_config" "$note" && grep -q "3.11" "$note"; then
  open_items_retained=true
fi
echo "open_items_retained=$open_items_retained"
