#!/usr/bin/env bash
# Provision a fresh Ubuntu 24.04 droplet for E1 and run it. Idempotent where it can be.
# Run ON the droplet as root after the working tree has been rsynced to /opt/slopware
# and the record volume mounted at /mnt/record.
set -euo pipefail

echo "== packages"
apt-get update -qq && apt-get install -y -qq curl git build-essential python3 >/dev/null

echo "== node 24"
if ! command -v node >/dev/null || [[ "$(node --version)" != v24* ]]; then
  curl -fsSL https://deb.nodesource.com/setup_24.x | bash - >/dev/null && apt-get install -y -qq nodejs >/dev/null
fi
node --version

echo "== foundry (anvil)"
if ! command -v anvil >/dev/null; then
  curl -L https://foundry.paradigm.xyz | bash >/dev/null 2>&1
  export PATH="$HOME/.foundry/bin:$PATH"; foundryup >/dev/null 2>&1
fi
export PATH="$HOME/.foundry/bin:$PATH"; anvil --version

echo "== dependencies"
cd /opt/slopware && npm ci --silent

echo "== record volume"
mkdir -p /mnt/record && mountpoint -q /mnt/record || { echo "mount the volume at /mnt/record first"; exit 1; }
mkdir -p /mnt/record/E1 && ln -sfn /mnt/record/E1 /opt/slopware/slopware/experiments/E1/record

echo "== manifest"
cat > /mnt/record/E1/manifest.json <<EOF
{ "experiment": "E1", "host": "$(hostname)", "startedAt": "$(date -u +%FT%TZ)", "node": "$(node --version)", "anvil": "$(anvil --version | head -1)", "gitCommit": "$(cat /opt/slopware/.gitcommit 2>/dev/null || echo unknown)" }
EOF
cat /mnt/record/E1/manifest.json
echo "ready. start shards with: ./slopware/experiments/E1/run.sh"
