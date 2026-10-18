#!/usr/bin/env bash
# Stage 201: boot REAL original-data-capable actor research NRO in NeXium.
# SD content is *generated fixture only*. Not private PS3 content.
set -euo pipefail
: "${NEXIUM_BIN:?Missing NeXium guest executable}"
: "${FOJ_NRO:?Missing compiled actor NRO}"
: "${NEXIUM_DATA_ROOT:?Missing isolated NeXium data root}"
: "${FOJ_EVIDENCE_DIR:?Missing generated-only screenshot directory}"
OUT="$FOJ_EVIDENCE_DIR"
test -s "$FOJ_NRO"
test -s "$NEXIUM_DATA_ROOT/sdmc/switch/foj/rig/preview.fojrm"
test -s "$NEXIUM_DATA_ROOT/sdmc/switch/foj/anims/preview.banim"
test -s "$NEXIUM_DATA_ROOT/sdmc/switch/foj/anims/preview_b.banim"
mkdir -p "$OUT"
"$NEXIUM_BIN" "$FOJ_NRO" >"$OUT/generated-actor-guest.log" 2>&1 &
pid=$!
trap 'kill -KILL "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true' EXIT

alive() {
  local state
  state="$(ps -o stat= -p "$pid" 2>/dev/null | tr -d " " || true)"
  if [[ -z "$state" || "$state" == Z* ]] || ! kill -0 "$pid" 2>/dev/null; then
    echo "NeXium generated actor guest exited unexpectedly" >&2
    return 1
  fi
}

for tick in $(seq 1 30); do sleep 1; alive; done
window="$(xdotool search --onlyvisible --name 'NeXium' 2>/dev/null | tail -n 1 || true)"
test -n "$window"
xdotool windowfocus --sync "$window" || true

shot() {
  alive
  timeout --kill-after=2s 10s import -window "$window" "$OUT/rig-$1.png"
  test -s "$OUT/rig-$1.png"
}
press() {
  alive
  # NeXium documented defaults: R=E, Switch Y=Z, Switch B=X.
  timeout --kill-after=1s 3s xdotool keydown --window "$window" "$1"
  sleep .18
  timeout --kill-after=1s 3s xdotool keyup --window "$window" "$1"
  sleep .50
}

# The real Stage194 viewer starts paused at clip A, t=0.
shot initial
press e
press e
shot step-025
sleep 1
shot still-025
press x
shot reset
# After reset: request secondary clip crossfade while paused.
press z
shot fade-0
for label in fade-25 fade-50 fade-75 fade-done; do
  press e
  shot "$label"
done
press x
shot reset-after
alive
echo "NeXium generated-only SD rig actor: 10 guest screenshots captured"
