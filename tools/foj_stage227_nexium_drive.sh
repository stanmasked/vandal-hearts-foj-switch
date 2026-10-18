#!/usr/bin/env bash
set -euo pipefail
test -s "$FOJ_NRO"
mkdir -p "$FOJ_EVIDENCE_DIR"

"$NEXIUM_BIN" "$FOJ_NRO" >"$FOJ_EVIDENCE_DIR/battle.log" 2>&1 &
guest=$!
trap 'kill -KILL "$guest" 2>/dev/null || true' EXIT

for n in $(seq 1 30); do
  sleep 1
  status="$(ps -o stat= -p "$guest" 2>/dev/null | tr -d ' ' || true)"
  if [ -z "$status" ] || [[ "$status" == Z* ]]; then
    tail -n 70 "$FOJ_EVIDENCE_DIR/battle.log" >&2
    exit 1
  fi
done
window="$(xdotool search --onlyvisible --name 'NeXium' 2>/dev/null | tail -n 1 || true)"
test -n "$window"

tap() {
  timeout --kill-after=1s 3s xdotool keydown --window "$window" "$1"
  sleep 0.18
  timeout --kill-after=1s 3s xdotool keyup --window "$window" "$1"
  sleep 0.5
}
capture() {
  kill -0 "$guest"
  timeout --kill-after=2s 10s import -window "$window" \
    "$FOJ_EVIDENCE_DIR/$1.png"
  test -s "$FOJ_EVIDENCE_DIR/$1.png"
}

timeout --kill-after=1s 3s xdotool windowfocus --sync "$window" || true
# Real input mapping verified in NeXium controller_config.rs:
# Switch A=c, X=v, Y=z, DRight=Right.
capture battle-initial
tap c
for step in 1 2 3 4; do tap Right; done
tap c
capture battle-moved
tap z
capture battle-turn1
tap Right
tap v
capture battle-hit1
tap z
capture battle-turn2
tap v
capture battle-victory
# A victory is terminal; another Y must not advance battle or hurt hero.
tap z
capture battle-terminal-y

kill -INT "$guest" 2>/dev/null || true
sleep 1
kill -KILL "$guest" 2>/dev/null || true
wait "$guest" 2>/dev/null || true
