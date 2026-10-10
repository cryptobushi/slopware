#!/usr/bin/env bash
# Finish E3. The record (~27 GB) stays on the droplet's volume, which is snapshotted and kept; what comes
# home is the manifest, the root hash, the parent summaries, the analysis, and the readings artefacts.
# Destroying the droplet is a separate, explicit step that runs only after the snapshot exists.
#
#   finish.sh seal       on the droplet: sha256 manifest of every record file; root hash; then fetch
#   finish.sh fetch      copies home: manifest, root, parent summaries, logs
#   finish.sh analyse    on the droplet: the pre-specified analysis and the descent/map artefacts; fetched here
#   finish.sh snapshot   DigitalOcean snapshot of the record volume (kept; ~$0.06/GB/month)
#   finish.sh teardown   destroy the droplet and the volume (asks for confirmation; requires a snapshot)
set -euo pipefail
cd "$(dirname "$0")/../../.."
IP=$(cat /tmp/e3-ip)
SSH="ssh -i $HOME/.ssh/slopware_e1 -o IdentitiesOnly=yes -o BatchMode=yes"
RS() { rsync -az -e "$SSH" "$@"; }
E3=slopware/experiments/E3

case "${1:-}" in
  seal)
    $SSH root@"$IP" 'cd /mnt/record/E3 && find record logs manifest.json -type f | sort | xargs sha256sum > MANIFEST.sha256 && sort MANIFEST.sha256 | sha256sum | cut -d" " -f1 > ROOT && echo "files $(wc -l < MANIFEST.sha256) · root $(cat ROOT) · size $(du -sh . | cut -f1)"'
    "$0" fetch ;;
  fetch)
    mkdir -p "$E3/summaries" results/E3
    for f in MANIFEST.sha256 ROOT manifest.json; do RS root@"$IP":/mnt/record/E3/$f results/E3/; done
    RS --include='*/' --include='summaries-*.jsonl' --include='endpoints-*.jsonl' --include='genomes.jsonl' --include='reproducibility.jsonl' --include='*.crashed.txt' --exclude='*' root@"$IP":/mnt/record/E3/record/ results/E3/record/
    RS root@"$IP":/mnt/record/E3/logs/ results/E3/logs/
    cp results/E3/ROOT "$E3/summaries/ROOT.sha256"; cp results/E3/manifest.json "$E3/summaries/run-manifest.json"; cp results/E3/MANIFEST.sha256 "$E3/summaries/MANIFEST.sha256"
    mkdir -p "$E3/summaries/walks"; cp -r results/E3/record/walks results/E3/record/neighbourhoods "$E3/summaries/" 2>/dev/null; find "$E3/summaries/neighbourhoods" -name "placements-*" -delete 2>/dev/null || true
    echo "sealed: root $(cat results/E3/ROOT) · neighbourhoods $(cat results/E3/record/neighbourhoods/main/summaries-*.jsonl | wc -l)" ;;
  analyse)
    RS scripts/e3_analysis.py scripts/e3_metrics.py root@"$IP":/opt/slopware/scripts/
    $SSH root@"$IP" 'cd /opt/slopware && mkdir -p slopware/experiments/E3/summaries && rm -rf slopware/experiments/E3/record && ln -s /mnt/record/E3/record slopware/experiments/E3/record && python3 scripts/e3_analysis.py scripts/e3_metrics.py slopware/experiments/E3 > slopware/experiments/E3/summaries/report.txt 2>&1; tail -3 slopware/experiments/E3/summaries/report.txt'
    RS root@"$IP":/opt/slopware/slopware/experiments/E3/summaries/ "$E3/summaries/"
    RS --include='*/' --include='summaries-*.jsonl' --include='endpoints-*.jsonl' --include='genomes.jsonl' --include='reproducibility.jsonl' --exclude='*' root@"$IP":/mnt/record/E3/record/ results/E3/record/
    echo "analysis and per-walk summaries fetched" ;;
  snapshot)
    VOL=$(doctl compute volume list --format ID,Name --no-header | awk '/slopware-e3-record/{print $1}')
    doctl compute volume snapshot "$VOL" --snapshot-name "slopware-e3-record-$(date -u +%Y%m%d)" --format ID,Name,Size 2>&1 | tail -2 ;;
  teardown)
    ID=$(doctl compute droplet list --tag-name slopware-e3 --format ID --no-header | head -1)
    VOL=$(doctl compute volume list --format ID,Name --no-header | awk '/slopware-e3-record/{print $1}')
    doctl compute snapshot list --resource volume --format Name --no-header | grep -q slopware-e3-record || { echo "snapshot first"; exit 1; }
    [ -f results/E3/ROOT ] || { echo "seal first"; exit 1; }
    read -r -p "destroy droplet $ID and volume $VOL? (yes/no) " ok; [ "$ok" = yes ] || exit 1
    doctl compute droplet delete "$ID" --force && echo "droplet destroyed"
    sleep 10
    doctl compute volume delete "$VOL" --force && echo "volume destroyed (snapshot kept)" ;;
  *) echo "usage: finish.sh seal|analyse|snapshot|teardown"; exit 1 ;;
esac
