#!/usr/bin/env bash
# Stage238: observe real NRO cache reuse and invalidation in NeXium.
set -euo pipefail
test -s "$FOJ_NRO"
mkdir -p "$FOJ_EVIDENCE_DIR"
"$NEXIUM_BIN" "$FOJ_NRO" >"$FOJ_EVIDENCE_DIR/guest.log" 2>&1 &
guest=$!
trap 'kill -KILL "$guest" 2>/dev/null || true' EXIT
for i in $(seq 1 30); do
  sleep 1
  state="$(ps -o stat= -p "$guest" 2>/dev/null | tr -d ' ' || true)"
  if [ -z "$state" ] || [[ "$state" == Z* ]]; then
    tail -n 70 "$FOJ_EVIDENCE_DIR/guest.log" >&2
    exit 1
  fi
done
window="$(xdotool search --onlyvisible --name 'NeXium' 2>/dev/null | tail -n 1 || true)"
test -n "$window"
timeout --kill-after=1s 3s xdotool windowfocus --sync "$window" || true
tap() {
  timeout --kill-after=1s 3s xdotool keydown --window "$window" "$1"
  sleep 0.16
  timeout --kill-after=1s 3s xdotool keyup --window "$window" "$1"
  sleep 0.45
}
capture() {
  kill -0 "$guest"
  timeout --kill-after=2s 10s import -window "$window" \
    "$FOJ_EVIDENCE_DIR/$1.png"
  test -s "$FOJ_EVIDENCE_DIR/$1.png"
}
# Source-verified NeXium default: A=c, B=x, ZR=t, Y=z, RStick=g.
capture cache-initial
tap c
capture cache-selected
tap Right
capture cache-hovered
tap g
capture cache-hidden
tap g
capture cache-restored
tap x
capture cache-cancelled
tap t
tap Left
tap c
capture cache-guarded
tap Right
capture cache-guard-hovered
tap z
capture cache-ended
kill -INT "$guest" 2>/dev/null || true
sleep 1
kill -KILL "$guest" 2>/dev/null || true
wait "$guest" 2>/dev/null || true
