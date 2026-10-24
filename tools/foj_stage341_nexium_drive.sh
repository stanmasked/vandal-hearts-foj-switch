#!/usr/bin/env bash
# Stage341 generated-only CI runner. The checker validates real window pixels;
# the native receipt alone is never accepted as shader-sampling evidence.
set -euo pipefail
: "${NEXIUM_BIN:?}"
: "${FOJ_NRO:?}"
: "${NEXIUM_DATA_ROOT:?}"
: "${FOJ_EVIDENCE_DIR:?}"
test -s "$FOJ_NRO"
sd="$NEXIUM_DATA_ROOT/sdmc/switch/foj/gpu"
marker="$sd/foj-stage341-texture-sample.txt"
test -s "$sd/source.dds"
test -s "$sd/foj_actor.vert.dksh"
test -s "$sd/foj_triangle.frag.dksh"
test ! -e "$marker" && test ! -L "$marker" || {
  echo "Stage341 refuses a stale native sample marker" >&2
  exit 2
}
mkdir -p "$FOJ_EVIDENCE_DIR"
for file in generated-source.json nexium-archive.sha256 guest.log gpu-initial.png gpu-later.png; do
  test ! -e "$FOJ_EVIDENCE_DIR/$file" && test ! -L "$FOJ_EVIDENCE_DIR/$file" || {
    echo "Stage341 refuses pre-existing evidence output" >&2
    exit 2
  }
done
"$NEXIUM_BIN" "$FOJ_NRO" >"$FOJ_EVIDENCE_DIR/guest.log" 2>&1 &
guest=$!
cleanup() {
  kill -TERM "$guest" 2>/dev/null || true
  sleep .2
  kill -KILL "$guest" 2>/dev/null || true
  wait "$guest" 2>/dev/null || true
}
trap cleanup EXIT
alive() {
  state="$(ps -o stat= -p "$guest" 2>/dev/null | tr -d ' ' || true)"
  if [[ -z "$state" || "$state" == Z* ]] || ! kill -0 "$guest" 2>/dev/null; then
    echo "Stage341 NeXium guest exited before verified texture sampling" >&2
    exit 1
  fi
}
window=""
for attempt in $(seq 1 45); do
  sleep 1
  alive
  window="$(xdotool search --onlyvisible --name 'NeXium' 2>/dev/null | tail -n 1 || true)"
  if [[ -n "$window" ]]; then break; fi
done
test -n "$window" || { echo "Stage341 missing real NeXium GUI window" >&2; exit 1; }
window_pid="$(xdotool getwindowpid "$window" 2>/dev/null || true)"
test -n "$window_pid" || { echo "Stage341 cannot bind capture to NeXium window PID" >&2; exit 1; }
window_args="$(ps -o args= -p "$window_pid" 2>/dev/null || true)"
grep -qi 'nexium' <<< "$window_args" || {
  echo "Stage341 capture window is not owned by a NeXium process" >&2
  exit 1
}
for attempt in $(seq 1 90); do
  sleep 1
  alive
  if [[ -f "$marker" && ! -L "$marker" ]]; then break; fi
done
test -f "$marker" && test ! -L "$marker" || {
  echo "Stage341 native texture-sample receipt never appeared" >&2
  exit 1
}
python3 - "$marker" <<'PY'
from pathlib import Path
import sys
from tools.foj_stage341_frame_gate import MARKER
if Path(sys.argv[1]).read_bytes() != MARKER:
    raise SystemExit("Stage341 guest receipt mismatch")
PY
# The NRO writes this receipt only after two frame presents; wait for the
# desktop compositor to settle before recording two independent captures.
sleep 1
timeout --kill-after=2s 12s import -window "$window" "$FOJ_EVIDENCE_DIR/gpu-initial.png"
sleep 1
alive
timeout --kill-after=2s 12s import -window "$window" "$FOJ_EVIDENCE_DIR/gpu-later.png"
python3 -m tools.foj_stage341_frame_gate audit --sd-root "$NEXIUM_DATA_ROOT/sdmc" --evidence "$FOJ_EVIDENCE_DIR" --generated-only
echo STAGE341_REAL_NEIXIUM_ORIGINAL_DDS_TEXTURE_SAMPLE_FRAME_PASS
