#!/usr/bin/env bash
# Stage273 generated-only real GPU capture; requires FOJ_DYNAMIC_CASE.
: "${FOJ_DYNAMIC_CASE:?}"
# Generated data only. Fail closed if NeXium cannot display all three generated
# GPU materials; never copy actual user-owned game assets to CI.
set -euo pipefail
: "${NEXIUM_BIN:?}"
: "${FOJ_NRO:?}"
: "${NEXIUM_DATA_ROOT:?}"
: "${FOJ_EVIDENCE_DIR:?}"
test -s "$FOJ_NRO"
for entry in actor.fojrm actor.fojmat material0.dds material1.dds material2.dds \
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
    echo "Stage273 GPU guest exited before RGB alpha proof" >&2
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
# The NRO deliberately shows DDS diagnostic colors for its FIRST 360
# guest frames. Never mistake those status fills for GPU material textures.
# Wait for the generated GPU overlap and unchanged rear-only probes; a static time delay is insufficient
# because software Vulkan guests may run far below 60 FPS.
found=0
for attempt in $(seq 1 30); do
  sleep 5
  alive
  timeout --kill-after=2s 10s import -window "$window" \
    "$FOJ_EVIDENCE_DIR/gpu-initial.png"
  if python3 - "$FOJ_EVIDENCE_DIR/gpu-initial.png" <<'PY'
from pathlib import Path
import sys
from tools.foj_stage273_dynamic_gpu_check import inspect
import os
try:
    inspect(Path(sys.argv[1]),os.environ['FOJ_DYNAMIC_CASE'])
except (OSError,ValueError):
    raise SystemExit(1)
PY
  then
    found=1
    break
  fi
done
if [ "$found" != 1 ]; then
  echo "GPU source-over alpha probe not visible at expected pixels" >&2
  exit 1
fi
# Do not use a fixed two-second interval: GPU clear-color phases may be
# identical at that spacing even when the two frames are genuinely distinct.
# Poll the observed framebuffer for an actual phase change (not just HUD
# performance metrics) and require both material footprints in that frame.
phase_changed=0
for attempt in $(seq 1 28); do
  sleep .5
  alive
  timeout --kill-after=2s 10s import -window "$window" \
    "$FOJ_EVIDENCE_DIR/gpu-later.png"
  if python3 - "$FOJ_EVIDENCE_DIR/gpu-initial.png" \
                 "$FOJ_EVIDENCE_DIR/gpu-later.png" <<'PY'
from pathlib import Path
from PIL import Image
from tools.foj_stage273_dynamic_gpu_check import inspect
import os
import sys
a,b=(Path(x) for x in sys.argv[1:])
try:
    inspect(b,os.environ['FOJ_DYNAMIC_CASE'])
    with Image.open(a) as first, Image.open(b) as second:
        x=first.convert("RGB");y=second.convert("RGB")
    probes=((25,350),(1220,350),(640,650),(25,650))
    if sum(x.getpixel(q)!=y.getpixel(q) for q in probes)<3:
        raise ValueError("Same clear-color phase")
except (ValueError,OSError):
    raise SystemExit(1)
PY
  then
    phase_changed=1
    break
  fi
done
if [ "$phase_changed" != 1 ]; then
  echo "NeXium blend test never presented a DISTINCT clear-color phase" >&2
  exit 1
fi
test -s "$FOJ_EVIDENCE_DIR/gpu-initial.png"
test -s "$FOJ_EVIDENCE_DIR/gpu-later.png"
echo "Two actual NeXium dynamically ordered alpha-blend captures with independently changed clear colors"
