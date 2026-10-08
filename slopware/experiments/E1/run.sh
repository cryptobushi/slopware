#!/usr/bin/env bash
# Start E1 on the droplet: two genesis shards, then two control shards, ten workers each, own anvil each.
# Logs and records go to the mounted volume. Idempotent: a shard whose parents file is complete is skipped.
set -euo pipefail
cd /opt/slopware
export PATH="$HOME/.foundry/bin:$PATH"
export NODE_OPTIONS=--max-old-space-size=8192
OUT=/mnt/record/E1/record
LOGS=/mnt/record/E1/logs; mkdir -p "$LOGS" "$OUT"

N_GENESIS=$(python3 -c "import json;print(json.load(open('slopware/experiments/E1/genesis.json'))['count'])")
N_CONTROL=$(python3 -c "import json;print(json.load(open('slopware/experiments/E1/controls.json'))['count'])")
HALF_G=$(( (N_GENESIS + 1) / 2 )); HALF_C=$(( (N_CONTROL + 1) / 2 ))

shard() { # set from to port
  local set=$1 from=$2 to=$3 port=$4
  nohup npx tsx src/e1.ts --set "$set" --from "$from" --to "$to" --port "$port" --workers 10 --sample 255 --restart-every 10 --out "$OUT" > "$LOGS/$set-$from-$to.log" 2>&1 &
  echo "started $set $from-$to on port $port (pid $!)"
}

case "${1:-genesis}" in
  genesis)
    shard genesis 0 $((HALF_G - 1)) 8560
    shard genesis $HALF_G $((N_GENESIS - 1)) 8561 ;;
  control)
    shard control 0 $((HALF_C - 1)) 8562
    shard control $HALF_C $((N_CONTROL - 1)) 8563 ;;
  status)
    for f in "$LOGS"/*.log; do echo "== $(basename "$f")"; tail -2 "$f"; done
    echo "== parents recorded: $(cat "$OUT"/*/parents-*.jsonl 2>/dev/null | wc -l) · placements: $(cat "$OUT"/*/placements-*.jsonl 2>/dev/null | wc -l)"
    echo "== record size: $(du -sh /mnt/record/E1 | cut -f1) · load: $(uptime | sed 's/.*load/load/')" ;;
  *) echo "usage: run.sh genesis|control|status"; exit 1 ;;
esac
