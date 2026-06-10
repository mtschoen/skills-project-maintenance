#!/usr/bin/env bash
# Build the planted state: a clean tracked tree plus empty leftover
# directories from old benchmark runs. Git tracks files, not directories, so
# `git status` stays clean - the husks are invisible to the dirty-tree check.
# cwd = the run dir; workspace/ exists and is empty.
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null

cd workspace
git init -q -b main
git config user.name "Eval Seed"
git config user.email "seed@example.com"

cat > loadgen.py <<'EOF'
"""Fire N requests at a target URL and report latency percentiles."""

import argparse
import time
import urllib.request


def run(url, count):
    timings = []
    for _ in range(count):
        start = time.time()
        urllib.request.urlopen(url, timeout=10).read()
        timings.append(time.time() - start)
    timings.sort()
    return {"p50": timings[len(timings) // 2], "p95": timings[int(len(timings) * 0.95)]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--count", type=int, default=100)
    arguments = parser.parse_args()
    print(run(arguments.url, arguments.count))
EOF
cat > README.md <<'EOF'
# loadgen

Fire N requests at a target URL and report latency percentiles. Run before
each release against staging.
EOF
git add -A
git commit -qm "initial import"

mkdir -p bench-workspace/iteration-1 bench-workspace/iteration-2 bench-workspace/archive/old-runs
