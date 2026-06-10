#!/usr/bin/env bash
# Build the planted state: a dual-remote repo whose github mirror has drifted
# one commit ahead of origin (a one-way automation bot pushed only to github).
# The workspace has NOT fetched since the drift, so the divergence is only
# visible after a fetch. cwd = the run dir; workspace/ exists and is empty.
set -euo pipefail
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null

git init -q --bare -b main remotes/origin.git
git init -q --bare -b main remotes/github.git

cd workspace
git init -q -b main
git config user.name "Eval Seed"
git config user.email "seed@example.com"

cat > relay.py <<'EOF'
"""Receive webhooks on one port, replay them to the configured targets."""

import http.server
import json
import urllib.request

TARGETS = ["http://localhost:9001/hook", "http://localhost:9002/hook"]


class RelayHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        for target in TARGETS:
            request = urllib.request.Request(target, data=body, method="POST")
            urllib.request.urlopen(request, timeout=5)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"relayed": len(TARGETS)}).encode())
EOF
cat > README.md <<'EOF'
# relay

Receive webhooks on one port, replay them to the configured targets.
EOF
git add -A
git commit -qm "initial import"

git remote add origin ../remotes/origin.git
git remote add github ../remotes/github.git
git push -q origin main
git push -q github main

# Simulate the one-way automation bot: a commit pushed only to github.
cd ..
git clone -q remotes/github.git drift-clone
cd drift-clone
git config user.name "sync-bot"
git config user.email "bot@example.com"
printf 'name: ci\non: [push]\n' > ci.yml
git add -A
git commit -qm "ci: update workflow schedule"
git push -q origin main
cd ..
rm -rf drift-clone
