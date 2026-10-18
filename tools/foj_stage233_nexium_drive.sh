#!/usr/bin/env bash
set -euo pipefail
test -s "$FOJ_NRO"
mkdir -p "$FOJ_EVIDENCE_DIR"
"$NEXIUM_BIN" "$FOJ_NRO" > "$FOJ_EVIDENCE_DIR/guest.log" 2>&1 &
pid=$!
trap 'kill -KILL "$pid" 2>/dev/null || true' EXIT
for i in $(seq 1 30); do
  sleep 1
  state="$(ps -o stat= -p "$pid" 2>/dev/null | tr -d " " || true)"
  if [ -z "$state" ] || [[ "$state" == Z* ]]; then
    tail -n 60 "$FOJ_EVIDENCE_DIR/guest.log" >&2
    exit 1
  fi
done
window="$(xdotool search --onlyvisible --name 'NeXium' 2>/dev/null | tail -n 1 || true)"
test -n "$window"
timeout --kill-after=1s 3s xdotool windowfocus --sync "$window" || true
press() {
  timeout --kill-after=1s 3s xdotool keydown --window "$window" "$1"
  sleep 0.17
  timeout --kill-after=1s 3s xdotool keyup --window "$window" "$1"
  sleep 0.5
}
capture() {
  kill -0 "$pid"
  timeout --kill-after=2s 10s import -window "$window" \
    "$FOJ_EVIDENCE_DIR/$1.png"
  test -s "$FOJ_EVIDENCE_DIR/$1.png"
}
# NeXium source default: A=C, right-stick click=G.
capture toggle-initial
press c
capture toggle-visible
press g
capture toggle-hidden
press g
capture toggle-restored
kill -INT "$pid" 2>/dev/null || true
sleep 1
kill -KILL "$pid" 2>/dev/null || true
wait "$pid" 2>/dev/null || true
