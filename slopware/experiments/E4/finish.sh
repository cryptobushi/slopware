#!/usr/bin/env bash
# Finish E4. The record (~5 GB) stays on the droplet's volume, which is snapshotted and kept; what comes
# home is the manifest, the root hash, the analysis (results, report, trajectories for the renderer).
# Destroying the droplet is a separate, explicit step that runs only after the snapshot exists.
#
#   finish.sh seal       on the droplet: sha256 manifest of every record file; root hash; then fetch
#   finish.sh fetch      copies home: manifest, root, parent summaries, logs
#   finish.sh analyse    on the droplet: the pre-specified analysis and the descent/map artefacts; fetched here
#   finish.sh snapshot   DigitalOcean snapshot of the record volume (kept; ~$0.06/GB/month)
#   finish.sh teardown   destroy the droplet and the E3 snapshot copy volume; the E4 record volume is kept (asks for confirmation; requires a snapshot)
set -euo pipefail
cd "$(dirname "$0")/../../.."
IP=$(cat /tmp/e4-ip)
SSH="ssh -i $HOME/.ssh/slopware_e1 -o IdentitiesOnly=yes -o BatchMode=yes"
RS() { rsync -az -e "$SSH" "$@"; }
E4=slopware/experiments/E4

case "${1:-}" in
  seal)
    $SSH root@"$IP" 'cd /mnt/record/E4 && find record logs manifest.json -type f | sort | xargs sha256sum > MANIFEST.sha256 && sort MANIFEST.sha256 | sha256sum | cut -d" " -f1 > ROOT && echo "files $(wc -l < MANIFEST.sha256) · root $(cat ROOT) · size $(du -sh . | cut -f1)"'
    "$0" fetch ;;
  fetch)
    mkdir -p "$E4/summaries" results/E4
    for f in MANIFEST.sha256 ROOT manifest.json; do RS root@"$IP":/mnt/record/E4/$f results/E4/; done
    RS root@"$IP":/mnt/record/E4/logs/ results/E4/logs/
    cp results/E4/ROOT "$E4/summaries/ROOT.sha256"; cp results/E4/manifest.json "$E4/summaries/run-manifest.json"; cp results/E4/MANIFEST.sha256 "$E4/summaries/MANIFEST.sha256"
    echo "sealed: root $(cat results/E4/ROOT) · populations $(grep -c populations/ results/E4/MANIFEST.sha256)" ;;
  analyse)
    RS scripts/e4_analysis.py root@"$IP":/opt/slopware/scripts/
    $SSH root@"$IP" 'cd /opt/slopware && mkdir -p slopware/experiments/E4/summaries && (apt-get install -y -qq python3-numpy python3-scipy >/dev/null 2>&1 || true) && python3 scripts/e4_analysis.py /mnt/record/E4/record slopware/experiments/E4/summaries > /mnt/record/E4/logs/analysis.log 2>&1; tail -9 slopware/experiments/E4/summaries/report.txt'
    RS root@"$IP":/opt/slopware/slopware/experiments/E4/summaries/ "$E4/summaries/"
    echo "analysis fetched: results.json, report.txt, trajectories.json" ;;
  snapshot)
    VOL=$(doctl compute volume list --format ID,Name --no-header | awk '/slopware-e4-record/{print $1}')
    doctl compute volume snapshot "$VOL" --snapshot-name "slopware-e4-record-$(date -u +%Y%m%d)" --format ID,Name,Size 2>&1 | tail -2 ;;
  teardown)
    ID=$(doctl compute droplet list --tag-name slopware-e4 --format ID --no-header | head -1)
    VOL=$(doctl compute volume list --format ID,Name --no-header | awk '/slopware-e4-e3copy/{print $1}')
    doctl compute snapshot list --resource volume --format Name --no-header | grep -q slopware-e4-record || { echo "snapshot first"; exit 1; }
    [ -f results/E4/ROOT ] || { echo "seal first"; exit 1; }
    read -r -p "destroy droplet $ID and the E3 copy volume $VOL (the E4 record volume is kept)? (yes/no) " ok; [ "$ok" = yes ] || exit 1
    doctl compute droplet delete "$ID" --force && echo "droplet destroyed"
    sleep 10
    doctl compute volume delete "$VOL" --force && echo "E3 copy volume deleted (E4 record volume and snapshot kept)" ;;
  *) echo "usage: finish.sh seal|fetch|analyse|snapshot|teardown"; exit 1 ;;
esac
