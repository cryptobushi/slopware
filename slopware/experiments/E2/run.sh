#!/usr/bin/env bash
# Start E2 on the droplet: 32 walkers (16 parent ranges × 2 arms), each sequential with its own anvil. Logs and records
# go to the mounted volume. Idempotent: a walker skips walks whose summary already exists and re-runs unfinished ones.
set -euo pipefail
cd /opt/slopware
export PATH="$HOME/.foundry/bin:$PATH"
export NODE_OPTIONS=--max-old-space-size=4096
OUT=/mnt/record/E2/record; LOGS=/mnt/record/E2/logs; mkdir -p "$LOGS" "$OUT"
N=$(python3 -c "import json;print(json.load(open('slopware/experiments/E2/parents.json'))['count'])")
walker() { # arm from to port
  nohup npx tsx src/e2.ts --arm "$1" --from "$2" --to "$3" --port "$4" --walks 5 --attempts 10000 --out "$OUT" > "$LOGS/$1-$2-$3.log" 2>&1 &
  echo "started $1 $2-$3 on port $4 (pid $!)"
}
case "${1:-status}" in
  all)
    port=8600
    for arm in A B; do
      for i in $(seq 0 15); do from=$(( i * N / 16 )); to=$(( (i + 1) * N / 16 - 1 )); walker $arm $from $to $port; port=$((port + 1)); done
    done ;;
  walker) walker "$2" "$3" "$4" "$5" ;;
  stop) pkill -f "src/e2.ts" || true; pkill -f "anvil --port 86" || true; echo stopped ;;
  status)
    for f in "$LOGS"/*.log; do printf "%-14s %s\n" "$(basename "$f" .log)" "$(tail -1 "$f" | cut -c1-110)"; done
    echo "== walks done: $(cat "$OUT"/*/summaries-*.jsonl 2>/dev/null | wc -l) of $((N * 2 * 5)) · attempts recorded: $(cat "$OUT"/*/walks-*.jsonl 2>/dev/null | wc -l)"
    echo "== record size: $(du -sh /mnt/record/E2 | cut -f1) · load: $(uptime | sed 's/.*load/load/')" ;;
  *) echo "usage: run.sh all|walker arm from to port|stop|status"; exit 1 ;;
esac
