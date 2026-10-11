#!/usr/bin/env bash
# Provision a fresh Ubuntu 24.04 droplet for E4 (E4-after.md §8). Two volumes: the E4 record at /mnt/record and a read-only copy of the E3 snapshot at /mnt/e3. Idempotent where it can be.
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

echo "== record volume and the E3 snapshot copy (read-only, for the generation-1 tables)"
mkdir -p /mnt/record && mountpoint -q /mnt/record || { echo "mount the record volume at /mnt/record first"; exit 1; }
mkdir -p /mnt/e3 && mountpoint -q /mnt/e3 || { echo "mount the E3 snapshot copy read-only at /mnt/e3 first"; exit 1; }
[ "$(cat /mnt/e3/E3/ROOT)" = "70471484778c5c91a8e7a299524af13d127bf491d70a0a62e7e53cd2628b8205" ] || { echo "E3 ROOT mismatch on /mnt/e3"; exit 1; }
mkdir -p /mnt/record/E4 && ln -sfn /mnt/record/E4 /opt/slopware/slopware/experiments/E4/record

echo "== manifest"
cat > /mnt/record/E4/manifest.json <<EOF
{ "experiment": "E4", "host": "$(hostname)", "startedAt": "$(date -u +%FT%TZ)", "node": "$(node --version)", "anvil": "$(anvil --version | head -1)", "gitCommit": "$(cat /opt/slopware/.gitcommit 2>/dev/null || echo unknown)" }
EOF
cat /mnt/record/E4/manifest.json
echo "ready. start shards with: ./slopware/experiments/E4/run.sh"
