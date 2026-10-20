#!/usr/bin/env bash
# Generated data only. Fail closed if NeXium cannot display both private
# GPU materials; never copy actual user-owned game assets to CI.
set -euo pipefail
: "${NEXIUM_BIN:?}"
: "${FOJ_NRO:?}"
: "${NEXIUM_DATA_ROOT:?}"
: "${FOJ_EVIDENCE_DIR:?}"
test -s "$FOJ_NRO"
for entry in actor.fojrm actor.fojmat material0.dds material1.dds \
  foj_actor.vert.dksh foj_triangle.frag.dksh; do
  test -s "$NEXIUM_DATA_ROOT/sdmc/switch/foj/gpu/$entry"
done
mkdir -p "$FOJ_EVIDENCE_DIR"
"$NEXIUM_BIN" "$FOJ_NRO" >"$FOJ_EVIDENCE_DIR/guest.log" 2>&1 &
guest=$!
trap 'kill -KILL "$guest" 2>/dev/null || true; wait "$guest" 2>/dev/null || true' EXIT
alive() {
  state="$(ps -o stat= -p "$guest" 2>/dev/null | tr -d ' ' || true)"
  if [[ -z "$state" || "$state" == Z* ]] || ! kill -0 "$guest" 2>/dev/null; then
    echo "Stage260 GPU guest exited before visual proof" >&2
    tail -n 50 "$FOJ_EVIDENCE_DIR/guest.log" >&2
    exit 1
  fi
}
window=""
for attempt in $(seq 1 30); do
  sleep 1
  alive
  window="$(xdotool search --onlyvisible --name 'NeXium' 2>/dev/null | tail -n 1 || true)"
  if [[ -n "$window" ]]; then break; fi
done
test -n "$window" || { echo "NeXium window not visible" >&2; exit 1; }
sleep 3
alive
timeout --kill-after=2s 10s import -window "$window" \
  "$FOJ_EVIDENCE_DIR/gpu-initial.png"
sleep 2
alive
timeout --kill-after=2s 10s import -window "$window" \
  "$FOJ_EVIDENCE_DIR/gpu-later.png"
test -s "$FOJ_EVIDENCE_DIR/gpu-initial.png"
test -s "$FOJ_EVIDENCE_DIR/gpu-later.png"
echo "Two real NeXium window captures created; no visual result is claimed until classifier passes"
