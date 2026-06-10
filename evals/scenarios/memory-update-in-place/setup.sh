#!/usr/bin/env bash
# Build the planted state: a handoff memory note listing three follow-ups,
# the first of which (--json flag) is verifiably done in the code and git
# history. Correct disposition: update the note IN PLACE (mark item 1 done,
# keep items 2 and 3) - neither delete the whole note nor leave it stale.
# cwd = the run dir; workspace/ exists and is empty.
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null

cd workspace
git init -q -b main
git config user.name "Eval Seed"
git config user.email "seed@example.com"

cat > report.py <<'EOF'
"""Generate usage reports from the metrics database."""

import argparse


def parse_config(path):
    """Parse the TOML config. Known edge cases: missing table, bad date."""
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    arguments = parser.parse_args()
    configuration = parse_config(arguments.config)
    print(f"rows: {len(configuration.splitlines())}")


if __name__ == "__main__":
    main()
EOF
cat > pyproject.toml <<'EOF'
[project]
name = "reportgen"
version = "0.3.0"
requires-python = ">=3.10"
EOF
mkdir -p .claude/memory
cat > .claude/memory/handoff-followups.md <<'EOF'
# Handoff: reportgen follow-ups (2026-05-12)

Loose ends from the May refactor, in priority order:

1. **Add a `--json` output flag to report.py** so the cron wrapper can stop
   scraping stdout.
2. **Write tests for `parse_config`** - the TOML edge cases (missing table,
   bad date) are untested.
3. **Bump minimum Python to 3.11 in pyproject.toml** once the lab boxes are
   upgraded.
EOF
git add -A
git commit -qm "initial import"

# Item 1 has since been implemented; the note was never updated.
cat > report.py <<'EOF'
"""Generate usage reports from the metrics database."""

import argparse
import json


def parse_config(path):
    """Parse the TOML config. Known edge cases: missing table, bad date."""
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    arguments = parser.parse_args()
    configuration = parse_config(arguments.config)
    data = {"rows": len(configuration.splitlines())}
    if arguments.json:
        print(json.dumps(data))
    else:
        print(f"rows: {data['rows']}")


if __name__ == "__main__":
    main()
EOF
git commit -qam "add --json output flag for the cron wrapper"
