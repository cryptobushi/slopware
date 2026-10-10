#!/usr/bin/env bash
# E3 on the droplet. Phases, in order (E3-somewhere-else.md §4–§6):
#   walks            32 walkers over 88 parents × 3 walks; endpoints frozen at Hamming 8/16/32/48/60
#   genomes          the mechanical genome list (parents first, then endpoints) and the every-tenth reproducibility subset
#   neighbourhoods   32 walkers over the genome list, exhaustive 16,319 children each, tag main; then the subset, tag rep
# A walker skips genomes whose summary already exists. Logs and record on the mounted volume.
set -euo pipefail
cd /opt/slopware
export PATH="$HOME/.foundry/bin:$PATH"
export NODE_OPTIONS=--max-old-space-size=4096
OUT=/mnt/record/E3/record; LOGS=/mnt/record/E3/logs; mkdir -p "$LOGS" "$OUT"
N=$(python3 -c "import json;print(json.load(open('slopware/experiments/E2/parents.json'))['count'])")
W=${WALKERS:-32}
case "${1:-status}" in
  walks)
    port=8700
    for i in $(seq 0 $((W - 1))); do from=$(( i * N / W )); to=$(( (i + 1) * N / W - 1 ))
      nohup npx tsx src/e3.ts --mode walks --from $from --to $to --walks 3 --attempts 2000 --port $port --out "$OUT" > "$LOGS/walks-$from-$to.log" 2>&1 &
      port=$((port + 1)); done; echo "$W walk workers started" ;;
  genomes)
    python3 scripts/e3_genomes.py "$OUT" slopware/experiments/E2/parents.json "$OUT/genomes.jsonl" "$OUT/reproducibility.jsonl" ;;
  neighbourhoods)
    tag=${2:-main}; list=$([ "$tag" = rep ] && echo "$OUT/reproducibility.jsonl" || echo "$OUT/genomes.jsonl"); G=$(wc -l < "$list"); port=8700
    for i in $(seq 0 $((W - 1))); do from=$(( i * G / W )); to=$(( (i + 1) * G / W - 1 ))
      nohup npx tsx src/e3.ts --mode neighbourhoods --genomes "$list" --from $from --to $to --tag $tag --port $port --out "$OUT" > "$LOGS/nbh-$tag-$from-$to.log" 2>&1 &
      port=$((port + 1)); done; echo "$W neighbourhood workers started on $G genomes ($tag)" ;;
  stop) pkill -f "src/e3.ts" || true; pkill -f "anvil --port 87" || true; echo stopped ;;
  status)
    for f in "$LOGS"/*.log; do printf "%-22s %s\n" "$(basename "$f" .log)" "$(tail -1 "$f" | cut -c1-110)"; done
    echo "== endpoints: $(cat "$OUT"/walks/endpoints-*.jsonl 2>/dev/null | grep -vc '"target":"end"') · walks ended: $(cat "$OUT"/walks/endpoints-*.jsonl 2>/dev/null | grep -c '"target":"end"')"
    echo "== neighbourhoods main: $(cat "$OUT"/neighbourhoods/main/summaries-*.jsonl 2>/dev/null | wc -l) · rep: $(cat "$OUT"/neighbourhoods/rep/summaries-*.jsonl 2>/dev/null | wc -l) · placements: $(cat "$OUT"/neighbourhoods/*/placements-*.jsonl 2>/dev/null | wc -l)"
    echo "== size: $(du -sh /mnt/record/E3 | cut -f1) · load: $(uptime | sed 's/.*load/load/')" ;;
  *) echo "usage: run.sh walks|genomes|neighbourhoods [main|rep]|stop|status"; exit 1 ;;
esac
