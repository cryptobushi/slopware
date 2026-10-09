#!/usr/bin/env bash
# Finish E1. The record (~27 GB) stays on the droplet's volume, which is snapshotted and kept; what comes
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
IP=$(cat /tmp/e1-ip)
SSH="ssh -i $HOME/.ssh/slopware_e1 -o IdentitiesOnly=yes -o BatchMode=yes"
RS() { rsync -az -e "$SSH" "$@"; }
E1=slopware/experiments/E1

case "${1:-}" in
  seal)
    $SSH root@"$IP" 'cd /mnt/record/E1 && find record logs manifest.json -type f | sort | xargs sha256sum > MANIFEST.sha256 && sort MANIFEST.sha256 | sha256sum | cut -d" " -f1 > ROOT && echo "files $(wc -l < MANIFEST.sha256) · root $(cat ROOT) · size $(du -sh . | cut -f1)"'
    "$0" fetch ;;
  fetch)
    mkdir -p "$E1/summaries" results/E1
    for f in MANIFEST.sha256 ROOT manifest.json; do RS root@"$IP":/mnt/record/E1/$f results/E1/; done
    RS --include='*/' --include='parents-*.jsonl' --include='*.crashed.txt' --exclude='*' root@"$IP":/mnt/record/E1/record/ results/E1/record/
    RS root@"$IP":/mnt/record/E1/logs/ results/E1/logs/
    cp results/E1/ROOT "$E1/summaries/ROOT.sha256"; cp results/E1/manifest.json "$E1/summaries/run-manifest.json"; cp results/E1/MANIFEST.sha256 "$E1/summaries/MANIFEST.sha256"
    mkdir -p "$E1/summaries/parents"; cp results/E1/record/*/parents-*.jsonl "$E1/summaries/parents/" 2>/dev/null || true
    echo "sealed: root $(cat results/E1/ROOT) · parents $(cat results/E1/record/*/parents-*.jsonl | wc -l)" ;;
  analyse)
    RS scripts/e1_analysis.py scripts/e1_descent.py scripts/e1_aggregate.py root@"$IP":/opt/slopware/scripts/
    $SSH root@"$IP" 'cd /opt/slopware && mkdir -p slopware/experiments/E1/summaries && rm -rf slopware/experiments/E1/record && ln -s /mnt/record/E1/record slopware/experiments/E1/record && python3 scripts/e1_analysis.py slopware/experiments/E1 | tee slopware/experiments/E1/summaries/report.txt | tail -5 && mkdir -p /mnt/record/E1/site && python3 scripts/e1_descent.py /mnt/record/E1/record /mnt/record/E1/site && python3 scripts/e1_aggregate.py /mnt/record/E1/record slopware/experiments/E1/genesis.json slopware/experiments/E1/summaries/aggregates.json'
    RS root@"$IP":/opt/slopware/slopware/experiments/E1/summaries/ "$E1/summaries/"
    RS root@"$IP":/mnt/record/E1/site/ slopware/site/
    echo "analysis and descent artefacts fetched" ;;
  snapshot)
    VOL=$(doctl compute volume list --format ID,Name --no-header | awk '/slopware-e1-record/{print $1}')
    doctl compute volume snapshot "$VOL" --snapshot-name "slopware-e1-record-$(date -u +%Y%m%d)" --format ID,Name,Size 2>&1 | tail -2 ;;
  teardown)
    ID=$(doctl compute droplet list --tag-name slopware-e1 --format ID --no-header | head -1)
    VOL=$(doctl compute volume list --format ID,Name --no-header | awk '/slopware-e1-record/{print $1}')
    doctl compute snapshot list --resource volume --format Name --no-header | grep -q slopware-e1-record || { echo "snapshot first"; exit 1; }
    [ -f results/E1/ROOT ] || { echo "seal first"; exit 1; }
    read -r -p "destroy droplet $ID and volume $VOL? (yes/no) " ok; [ "$ok" = yes ] || exit 1
    doctl compute droplet delete "$ID" --force && echo "droplet destroyed"
    sleep 10
    doctl compute volume delete "$VOL" --force && echo "volume destroyed (snapshot kept)" ;;
  *) echo "usage: finish.sh seal|analyse|snapshot|teardown"; exit 1 ;;
esac
