#!/usr/bin/env bash
# E4 on the droplet (E4-after.md §5–§8). Phases, in order:
#   tables        canonical E3 child tables for the generation-1 check, from the E3 snapshot copy mounted at /mnt/e3 (hash-checked)
#   run           W workers, each over whole populations: pairs split across workers, both founders, all 16 replicates
#   status | stop
# A worker skips populations whose record already has its final line. Logs and record on the mounted record volume.
set -euo pipefail
cd /opt/slopware
export PATH="$HOME/.foundry/bin:$PATH"
export NODE_OPTIONS=--max-old-space-size=4096
OUT=/mnt/record/E4/record; LOGS=/mnt/record/E4/logs; TABLES=/mnt/record/E4/e3-tables; mkdir -p "$LOGS" "$OUT"
SEED=${SEED:-E4-2026-10-11}; W=${WALKERS:-32}; REPS=${REPS:-0-15}; GENS=${GENS:-256}
case "${1:-status}" in
  tables)
    python3 scripts/e4_tables.py /mnt/e3/E3/record slopware/experiments/E4/predictors.json "$TABLES" ;;
  run)
    [ -d "$TABLES" ] && [ "$(ls "$TABLES" | wc -l)" -eq 176 ] || { echo "E3 tables missing; run tables first"; exit 1; }
    port=8700
    for i in $(seq 0 $((W - 1))); do from=$(( i * 88 / W )); to=$(( (i + 1) * 88 / W - 1 ))
      nohup npx tsx src/e4.ts --pairs $from-$to --founders P,N --replicates "$REPS" --generations "$GENS" --seed "$SEED" --e3tables "$TABLES" --port $port --out "$OUT" > "$LOGS/run-$from-$to.log" 2>&1 &
      port=$((port + 1)); done; echo "$W workers started · seed $SEED · replicates $REPS · generations $GENS" ;;
  stop) pkill -f "src/e4.ts" || true; pkill -f "anvil --port 87" || true; echo stopped ;;
  status)
    for f in "$LOGS"/*.log; do printf "%-18s %s\n" "$(basename "$f" .log)" "$(tail -1 "$f" | cut -c1-120)"; done
    echo "== populations finished: $(grep -l '"final":true' "$OUT"/populations/*.jsonl 2>/dev/null | wc -l) of 2816 · mismatches: $(grep -l 'GENERATION-1 MISMATCH' "$LOGS"/*.log 2>/dev/null | wc -l)"
    echo "== size: $(du -sh /mnt/record/E4 | cut -f1) · load: $(uptime | sed 's/.*load/load/')" ;;
  *) echo "usage: run.sh tables|run|stop|status"; exit 1 ;;
esac
