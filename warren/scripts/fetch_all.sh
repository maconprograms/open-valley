#!/bin/bash
# Download every Warren VT NEMRC camadetail page into the raw cache.
# Idempotent (skips files already >2KB). 6 parallel workers, 3 retries each.
# Layout: this script lives in warren/scripts/; raw HTML -> warren/raw_html/
# (git-ignored); parcel list read from warren/outputs/parcels.txt.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
BASE="$(dirname "$HERE")"
BASE_URL="https://nemrc.info/web_data/vtwarr/camadetailT.php?prop="
DIR="$BASE/raw_html"
LIST="$BASE/outputs/parcels.txt"
mkdir -p "$DIR"

fetch_one() {
  local pid="$1"
  local out="$DIR/${pid}.html"
  if [ -f "$out" ] && [ "$(wc -c < "$out")" -gt 2048 ]; then return 0; fi
  local code sz
  for attempt in 1 2 3; do
    code=$(curl -s -w "%{http_code}" --max-time 60 "${BASE_URL}${pid}" -o "$out")
    sz=$(wc -c < "$out" 2>/dev/null || echo 0)
    if [ "$code" = "200" ] && [ "$sz" -gt 2048 ]; then return 0; fi
    sleep 2
  done
  echo "FAILED $pid code=$code size=$sz" >&2
  return 1
}
export -f fetch_one
export BASE_URL DIR

xargs -P 6 -I {} bash -c 'fetch_one "$@"' _ {} < "$LIST"
echo "downloaded: $(ls "$DIR" | wc -l | tr -d ' ') / $(wc -l < "$LIST" | tr -d ' ')"
