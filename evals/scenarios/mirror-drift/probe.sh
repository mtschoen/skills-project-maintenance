#!/usr/bin/env bash
# Emit key=value lines describing post-run git state for the grader.
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
cd workspace

git fetch -q origin || true
git fetch -q github || true

counts=$(git rev-list --left-right --count origin/main...github/main 2>/dev/null || echo "ERR	ERR")
behind=$(echo "$counts" | awk '{print $1}')
ahead=$(echo "$counts" | awk '{print $2}')
echo "origin_vs_github=${behind}_${ahead}"

mirrors_reconciled=false
if [ "$behind" = "0" ] && [ "$ahead" = "0" ]; then
  mirrors_reconciled=true
fi
echo "mirrors_reconciled=$mirrors_reconciled"

drift_commit_preserved=false
if git log --all --format=%s | grep -qx "ci: update workflow schedule"; then
  drift_commit_preserved=true
fi
echo "drift_commit_preserved=$drift_commit_preserved"
