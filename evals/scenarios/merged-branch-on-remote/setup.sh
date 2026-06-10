#!/usr/bin/env bash
# Build the planted state: a feature branch fully merged into main that still
# exists BOTH locally and on the origin remote. The differentiator under test
# is the remote copy - deleting/surfacing only the local branch is a miss.
# cwd = the run dir; workspace/ exists and is empty.
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null

git init -q --bare -b main remotes/origin.git

cd workspace
git init -q -b main
git config user.name "Eval Seed"
git config user.email "seed@example.com"

cat > fetchkit.py <<'EOF'
"""Tiny HTTP fetch helper used by internal cron jobs."""

import urllib.request


def fetch(url, timeout=10):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()
EOF
cat > README.md <<'EOF'
# fetchkit

Tiny HTTP fetch helper used by internal cron jobs.
EOF
git add -A
git commit -qm "initial import"

git checkout -qb add-retry-logic
cat > fetchkit.py <<'EOF'
"""Tiny HTTP fetch helper used by internal cron jobs."""

import time
import urllib.request


def fetch(url, timeout=10, retries=3):
    last_error = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return response.read()
        except OSError as error:
            last_error = error
            time.sleep(2**attempt)
    raise last_error
EOF
git commit -qam "add retry with exponential backoff to fetch"

git checkout -q main
git merge -q --no-ff add-retry-logic -m "Merge branch 'add-retry-logic'"

git remote add origin ../remotes/origin.git
git push -q origin main add-retry-logic
