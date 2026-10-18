#!/usr/bin/env bash
# Stage 187: actual NeXium guest input, screenshots and HOST RSS checkpoints.
# This file runs inside xvfb-run and must not include original PS3 resources.
set -euo pipefail

: "${NEXIUM_BIN:?Missing NeXium executable}"
: "${FOJ_NRO:?Missing generated-only COLL NRO}"
OUT="${FOJ_EVIDENCE_DIR:-runtime-evidence}"
mkdir -p "$OUT"
"$NEXIUM_BIN" "$FOJ_NRO" >"$OUT/nexium-coll-guest.log" 2>&1 &
pid=$!
trap 'kill -KILL "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true' EXIT

alive() {
  local state
  state="$(ps -o stat= -p "$pid" 2>/dev/null | tr -d ' ' || true)"
  if [[ -z "$state" || "$state" == Z* ]] || ! kill -0 "$pid" 2>/dev/null; then
    echo "NeXium guest exited or became a zombie" >&2
    tail -n 70 "$OUT/nexium-coll-guest.log" >&2
    return 1
  fi
}

window=""
for tick in $(seq 1 30); do
  sleep 1
  alive
done
window="$(xdotool search --onlyvisible --name "NeXium" 2>/dev/null | tail -n 1 || true)"
test -n "$window"
xdotool windowfocus --sync "$window" || true

checkpoint() {
  local count="$1" rss image
  alive
  rss="$(ps -o rss= -p "$pid" | tr -d '[:space:]')"
  [[ "$rss" =~ ^[0-9]+$ ]] && (( rss > 0 ))
  image="$(printf '%s/coll-endurance-%02d.png' "$OUT" "$count")"
  timeout --kill-after=2s 10s import -window "$window" "$image"
  test -s "$image"
  printf '%s\t%s\t%s\n' "$count" "$rss" "$(date +%s)" \
    >> "$OUT/nexium-host-rss.tsv"
}

# Source-verified NeXium default mapping: z = Nintendo Switch Y.
# Each event uses keydown/keyup, not a single held key.
checkpoint 0
for count in $(seq 1 48); do
  alive
  timeout --kill-after=1s 3s xdotool keydown --window "$window" z
  sleep 0.18
  timeout --kill-after=1s 3s xdotool keyup --window "$window" z
  sleep 0.18
  case "$count" in
    1|8|9|24|25|40|41|48)
      sleep 0.50
      checkpoint "$count"
      ;;
  esac
done
echo "NeXium guest remained alive for 48 separate Y button events"
