#!/usr/bin/env bash
# Finish E2. The record (~27 GB) stays on the droplet's volume, which is snapshotted and kept; what comes
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
IP=$(cat /tmp/e2-ip)
SSH="ssh -i $HOME/.ssh/slopware_e1 -o IdentitiesOnly=yes -o BatchMode=yes"
RS() { rsync -az -e "$SSH" "$@"; }
E2=slopware/experiments/E2

case "${1:-}" in
  seal)
    $SSH root@"$IP" 'cd /mnt/record/E2 && find record logs manifest.json -type f | sort | xargs sha256sum > MANIFEST.sha256 && sort MANIFEST.sha256 | sha256sum | cut -d" " -f1 > ROOT && echo "files $(wc -l < MANIFEST.sha256) · root $(cat ROOT) · size $(du -sh . | cut -f1)"'
    "$0" fetch ;;
  fetch)
    mkdir -p "$E2/summaries" results/E2
    for f in MANIFEST.sha256 ROOT manifest.json; do RS root@"$IP":/mnt/record/E2/$f results/E2/; done
    RS --include='*/' --include='summaries-*.jsonl' --include='lengthening-*.jsonl' --include='*.crashed.txt' --exclude='*' root@"$IP":/mnt/record/E2/record/ results/E2/record/
    RS root@"$IP":/mnt/record/E2/logs/ results/E2/logs/
    cp results/E2/ROOT "$E2/summaries/ROOT.sha256"; cp results/E2/manifest.json "$E2/summaries/run-manifest.json"; cp results/E2/MANIFEST.sha256 "$E2/summaries/MANIFEST.sha256"
    mkdir -p "$E2/summaries/walks"; cp results/E2/record/*/summaries-*.jsonl results/E2/record/*/lengthening-*.jsonl "$E2/summaries/walks/" 2>/dev/null || true
    echo "sealed: root $(cat results/E2/ROOT) · walks $(cat results/E2/record/*/summaries-*.jsonl | wc -l)" ;;
  analyse)
    RS scripts/e2_analysis.py root@"$IP":/opt/slopware/scripts/
    $SSH root@"$IP" 'cd /opt/slopware && mkdir -p slopware/experiments/E2/summaries && rm -rf slopware/experiments/E2/record && ln -s /mnt/record/E2/record slopware/experiments/E2/record && python3 scripts/e2_analysis.py slopware/experiments/E2 > slopware/experiments/E2/summaries/report.txt 2>&1; tail -3 slopware/experiments/E2/summaries/report.txt'
    RS root@"$IP":/opt/slopware/slopware/experiments/E2/summaries/ "$E2/summaries/"
    RS --include='*/' --include='summaries-*.jsonl' --include='lengthening-*.jsonl' --exclude='*' root@"$IP":/mnt/record/E2/record/ results/E2/record/
    echo "analysis and per-walk summaries fetched" ;;
  snapshot)
    VOL=$(doctl compute volume list --format ID,Name --no-header | awk '/slopware-e2-record/{print $1}')
    doctl compute volume snapshot "$VOL" --snapshot-name "slopware-e2-record-$(date -u +%Y%m%d)" --format ID,Name,Size 2>&1 | tail -2 ;;
  teardown)
    ID=$(doctl compute droplet list --tag-name slopware-e2 --format ID --no-header | head -1)
    VOL=$(doctl compute volume list --format ID,Name --no-header | awk '/slopware-e2-record/{print $1}')
    doctl compute snapshot list --resource volume --format Name --no-header | grep -q slopware-e2-record || { echo "snapshot first"; exit 1; }
    [ -f results/E2/ROOT ] || { echo "seal first"; exit 1; }
    read -r -p "destroy droplet $ID and volume $VOL? (yes/no) " ok; [ "$ok" = yes ] || exit 1
    doctl compute droplet delete "$ID" --force && echo "droplet destroyed"
    sleep 10
    doctl compute volume delete "$VOL" --force && echo "volume destroyed (snapshot kept)" ;;
  *) echo "usage: finish.sh seal|analyse|snapshot|teardown"; exit 1 ;;
esac
