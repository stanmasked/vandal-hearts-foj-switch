#!/usr/bin/env bash
# Stage 202: real NeXium repeated actor A/B transitions with GENERATED-ONLY SD.
# The SD root is freshly populated by the Stage 201 generated-fixture script.
# Never run this workflow with owner-held original game data.
set -euo pipefail
: "${NEXIUM_BIN:?Missing NeXium binary}"
: "${FOJ_NRO:?Missing actual rigged actor NRO}"
: "${NEXIUM_DATA_ROOT:?Missing isolated NeXium data root}"
: "${FOJ_EVIDENCE_DIR:?Missing synthetic evidence directory}"
: "${FOJ_CYCLES:=6}"
[[ "$FOJ_CYCLES" =~ ^[0-9]+$ ]] && (( FOJ_CYCLES >= 3 && FOJ_CYCLES <= 8 ))
[[ "$NEXIUM_DATA_ROOT" == *"stage202-generated-only"* ]] || {
  echo "Require stage202-generated-only isolated SD data root" >&2; exit 3;
}
test -s "$FOJ_NRO"
test -s "$NEXIUM_DATA_ROOT/sdmc/switch/foj/rig/preview.fojrm"
test -s "$NEXIUM_DATA_ROOT/sdmc/switch/foj/anims/preview.banim"
test -s "$NEXIUM_DATA_ROOT/sdmc/switch/foj/anims/preview_b.banim"
mkdir -p "$FOJ_EVIDENCE_DIR"
OUT="$FOJ_EVIDENCE_DIR"

"$NEXIUM_BIN" "$FOJ_NRO" > "$OUT/generated-only-actor-endurance.log" 2>&1 &
pid=$!
trap 'kill -KILL "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true' EXIT

alive() {
  local state
  state="$(ps -o stat= -p "$pid" 2>/dev/null | tr -d ' ' || true)"
  if [[ -z "$state" || "$state" == Z* ]] || ! kill -0 "$pid" 2>/dev/null; then
    echo "NeXium generated SD actor exited unexpectedly" >&2
    return 1
  fi
}
for tick in $(seq 1 30); do sleep 1; alive; done
window="$(xdotool search --onlyvisible --name 'NeXium' 2>/dev/null | tail -n 1 || true)"
test -n "$window"
xdotool windowfocus --sync "$window" || true

press() {
  alive
  timeout --kill-after=1s 3s xdotool keydown --window "$window" "$1"
  sleep .13
  timeout --kill-after=1s 3s xdotool keyup --window "$window" "$1"
  sleep .23
}

shot() {
  alive
  timeout --kill-after=2s 10s import -window "$window" "$OUT/endurance-$1.png"
  test -s "$OUT/endurance-$1.png"
}

rss() {
  local memory
  memory="$(ps -o rss= -p "$pid" 2>/dev/null | tr -d '[:space:]')"
  [[ "$memory" =~ ^[0-9]+$ ]] && ((memory>0))
  printf '%02d\t%s\n' "$1" "$memory" >> "$OUT/endurance-generated-host-rss.tsv"
}

shot baseline
rss 0
# Defaults verified in NeXium controller source and Stage 201:
# X keyboard = Switch B (reset), E = Switch R (paused 125 ms step),
# Z = Switch Y (0.5-second A/B crossfade).
for iteration in $(seq 1 "$FOJ_CYCLES"); do
  label="$(printf '%02d' "$iteration")"
  press x
  shot "reset-$label"
  press e
  press e
  shot "a-step-$label"
  sleep .70
  shot "a-paused-$label"

  press z
  for step in $(seq 1 4); do press e; done
  shot "b-complete-$label"

  press z
  for step in $(seq 1 4); do press e; done
  shot "a-return-$label"
  rss "$iteration"
done
alive
echo "NeXium guest survived $FOJ_CYCLES generated-only, bidirectional clip cycles"
