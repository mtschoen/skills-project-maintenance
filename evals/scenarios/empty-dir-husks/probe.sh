#!/usr/bin/env bash
# Emit key=value lines describing post-run state for the grader.
set -euo pipefail
cd workspace

count=$(find . -type d -empty -not -path "./.git/*" | wc -l | tr -d ' ')
echo "empty_dirs_remaining=$count"

tracked_files_intact=false
if [ -f loadgen.py ] && [ -f README.md ]; then
  tracked_files_intact=true
fi
echo "tracked_files_intact=$tracked_files_intact"
