#!/usr/bin/env bash
# Stage 193: deterministic NeXium guest input for invented two-bone animation.
# Uses no copyrighted resources. Evidence includes actual emulator screenshots.
set -euo pipefail
: "${NEXIUM_BIN:?Missing NeXium executable}"
: "${FOJ_NRO:?Missing generated-only animation NRO}"
OUT="${FOJ_EVIDENCE_DIR:-runtime-evidence}"
mkdir -p "$OUT"

"$NEXIUM_BIN" "$FOJ_NRO" >"$OUT/anim-guest.log" 2>&1 &
pid=$!
trap 'kill -KILL "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true' EXIT

alive() {
  local state
  state="$(ps -o stat= -p "$pid" 2>/dev/null | tr -d ' ' || true)"
  if [[ -z "$state" || "$state" == Z* ]] || ! kill -0 "$pid" 2>/dev/null; then
    echo "NeXium synthetic animation guest exited unexpectedly" >&2
    tail -n 50 "$OUT/anim-guest.log" >&2
    return 1
  fi
}

for i in $(seq 1 30); do sleep 1; alive; done
window="$(xdotool search --onlyvisible --name 'NeXium' 2>/dev/null | tail -n 1 || true)"
test -n "$window"
xdotool windowfocus --sync "$window" || true

shot() {
  alive
  timeout --kill-after=2s 10s import -window "$window" "$OUT/anim-$1.png"
  test -s "$OUT/anim-$1.png"
}

press() {
  alive
  # NeXium default binding from earlier guest regression:
  # C = Switch A, X = Switch B, Z = Switch Y, Right = D-pad right.
  timeout --kill-after=1s 3s xdotool keydown --window "$window" "$1"
  sleep 0.18
  timeout --kill-after=1s 3s xdotool keyup --window "$window" "$1"
  sleep 0.50
}

# NRO starts paused at first frame, so this initial screenshot is stable.
shot initial
press c
sleep 1
shot playing
press c
shot paused
sleep 1
shot paused-later

# Reset to A/t=0, start B fade while paused, advance by explicit 1/8s
# steps. Deterministic even if NeXium's frame pacing fluctuates.
press x
press z
shot fade-0
for pair in 'fade-25' 'fade-50' 'fade-75' 'fade-done'; do
  press Right
  shot "$pair"
done
alive
echo "Captured nine separate states of real synthetic animation NRO guest"
