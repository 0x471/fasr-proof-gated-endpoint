#!/usr/bin/env bash
# One scenario against the v1 image: the endpoint already runs on the Pi (started at boot, settings from the
# signed store), the prover and the observer run on this machine. There is no login on the image, so nothing
# is started, stopped or copied on the Pi; the manifest records what the operator says the Pi runs.
# Usage from the repo root: device/image_scenario.sh NAME N -- prover/server.py args...
#   e.g. IMAGE_SHA=<sdcard.img sha256> LABEL=powersave device/image_scenario.sh timing_ps 512 -- --mode timing_bits --bits $B --slot 1.0
# Needs this machine on 192.168.2.1 and the Pi on 192.168.2.2. Writes OUT/NAME.* files.
# IMAGE_SHA: sha256 of the flashed image; LABEL: the condition (e.g. the CPU speed policy on the kernel command
# line). The observer runs with /usr/bin/python3: on macOS a Homebrew Python may lack Local Network access.
# PERIOD_MS: send one request every PERIOD_MS on one connection without waiting (observer --period-ms), as the
# server's load_bits mode expects; a run where the server logged a late send counts as failed.
set -uo pipefail
cd "$(dirname "$0")/.."
OUT="${OUT:-runs}"
IMAGE_SHA="${IMAGE_SHA:?sha256 of the flashed image}"
LABEL="${LABEL:-}"
PERIOD_MS="${PERIOD_MS:-}"
[[ "${3:-}" == "--" ]] || { echo "usage: $0 NAME N -- prover/server.py args..."; exit 2; }
NAME=$1 N=$2; shift 3
[[ "$NAME" =~ ^[A-Za-z0-9_]+$ ]] || { echo "bad NAME"; exit 2; }
[[ "$N" =~ ^[1-9][0-9]{0,4}$ ]] || { echo "bad N"; exit 2; }
[[ "$IMAGE_SHA" =~ ^[0-9a-f]{64}$ ]] || { echo "bad IMAGE_SHA"; exit 2; }
[[ "$LABEL" =~ ^[A-Za-z0-9_-]*$ ]] || { echo "bad LABEL"; exit 2; }
[[ -z "$PERIOD_MS" || "$PERIOD_MS" =~ ^[1-9][0-9]{1,4}$ ]] || { echo "bad PERIOD_MS"; exit 2; }
[[ -z "$(git status --porcelain)" ]] || { echo "$NAME: the checkout has changes; commit them first"; exit 2; }
COMMIT="$(git rev-parse HEAD)"
STARTED="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
mkdir -p "$OUT"
X='[[0.5, -0.2, 0.9, 0.1]]'
cleanup() {
  pkill -f "[p]rover/server.py --listen 192.168.2.1"; sleep 0.5; pkill -9 -f "[p]rover/server.py --listen 192.168.2.1"; true
}
cleanup
trap cleanup EXIT
.venv/bin/python prover/server.py --listen 192.168.2.1:8701 "$@" 2>"$OUT/$NAME.server.log" &
for i in $(seq 120); do grep -q listening "$OUT/$NAME.server.log" && break; sleep 0.5; done
grep -q listening "$OUT/$NAME.server.log" || { echo "$NAME: server did not start"; exit 1; }
# The endpoint redials the server on its own; wait for its connection.
ok=0
for i in $(seq 120); do
  lsof -nP -iTCP:8701 -sTCP:ESTABLISHED 2>/dev/null | grep -q 192.168.2.2 && { ok=1; break; }
  sleep 0.5
done
[ $ok = 1 ] || { echo "$NAME: the endpoint did not connect"; exit 1; }
# Each answer can take up to the 4 s release time plus a check, so the client's limit grows with N.
limit=$(( N * 7 + 120 ))
timeout "$limit" /usr/bin/python3 observer/client.py 192.168.2.2 8700 "$X" --n "$N" ${PERIOD_MS:+--period-ms "$PERIOD_MS"} \
  > "$OUT/$NAME.trace.jsonl" 2>"$OUT/$NAME.client.err"
rc=$?
rows=$(wc -l < "$OUT/$NAME.trace.jsonl" | tr -d ' ')
late=$(grep -c ' ms late$' "$OUT/$NAME.server.log")
status=ok
[[ $rc == 0 && $rows == "$N" && $late == 0 ]] || status=failed
PERIOD_MS="$PERIOD_MS" LATE="$late" NAME="$NAME" N="$N" COMMIT="$COMMIT" STARTED="$STARTED" RC="$rc" ROWS="$rows" STATUS="$status" IMAGE_SHA="$IMAGE_SHA" LABEL="$LABEL" \
  /usr/bin/python3 -I -c '
import json, os, sys
e = os.environ
m = {"name": e["NAME"], "target": "v1 image", "image_sha256": e["IMAGE_SHA"], "label": e["LABEL"], "n": int(e["N"]),
     "commit": e["COMMIT"], "started": e["STARTED"], "client_exit": int(e["RC"]), "rows": int(e["ROWS"]),
     "status": e["STATUS"], "server_args": sys.argv[1:], "period_ms": e["PERIOD_MS"], "server_late_sends": int(e["LATE"])}
print(json.dumps(m))' "$@" > "$OUT/$NAME.manifest.json" || status=failed
echo "$NAME: client exit $rc rows $rows/$N $status"
[[ $status == ok ]]
