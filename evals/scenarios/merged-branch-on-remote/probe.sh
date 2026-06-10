#!/usr/bin/env bash
# Emit key=value lines describing post-run git state for the grader.
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
cd workspace

local_present=false
if git show-ref --verify --quiet refs/heads/add-retry-logic; then
  local_present=true
fi
remote_present=false
if [ -n "$(git ls-remote --heads origin add-retry-logic)" ]; then
  remote_present=true
fi
echo "local_branch_present=$local_present"
echo "remote_branch_present=$remote_present"

fully_removed=false
if [ "$local_present" = false ] && [ "$remote_present" = false ]; then
  fully_removed=true
fi
echo "merged_branch_fully_removed=$fully_removed"

main_present=false
if git show-ref --verify --quiet refs/heads/main; then
  main_present=true
fi
echo "main_present=$main_present"

retry_code_on_main=false
if git grep -q "retries" main -- fetchkit.py; then
  retry_code_on_main=true
fi
echo "retry_code_on_main=$retry_code_on_main"
