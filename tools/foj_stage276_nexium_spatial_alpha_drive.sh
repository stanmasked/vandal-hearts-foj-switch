#!/usr/bin/env bash
# Stage276 real NeXium GPU capture of spatial alpha inside a single RGBA8 DDS.
: "${FOJ_SPATIAL_CASE:?}"
# Generated data only. Fail closed if NeXium cannot display all three generated
# GPU materials; never copy actual user-owned game assets to CI.
set -euo pipefail
: "${NEXIUM_BIN:?}"
: "${FOJ_NRO:?}"
: "${NEXIUM_DATA_ROOT:?}"
: "${FOJ_EVIDENCE_DIR:?}"
test -s "$FOJ_NRO"
case "$FOJ_SPATIAL_CASE" in alpha-left-clear|alpha-right-clear) ;; *) exit 2;; esac
sort_root="$NEXIUM_DATA_ROOT/sdmc/switch/foj/gpu"
sort_marker="$sort_root/foj-native-sort-pass.txt"
test ! -e "$sort_marker" && test ! -L "$sort_marker" || {
  echo "Stage273 refuses a pre-existing native GPU sort receipt" >&2
  exit 2
}
for entry in actor.fojrm actor.fojmat material0.dds material1.dds material2.dds \
  foj_actor.vert.dksh foj_triangle.frag.dksh; do
  test -s "$NEXIUM_DATA_ROOT/sdmc/switch/foj/gpu/$entry"
done
mkdir -p "$FOJ_EVIDENCE_DIR"
for marker in foj-native-alpha-pass.txt foj-native-rear-alpha-reject.txt \
              foj-native-topology-reject.txt; do
  if [[ -e "$sort_root/$marker" || -L "$sort_root/$marker" ]]; then
    echo "Stage276 refuses pre-existing native guest markers" >&2
    exit 2
  fi
done
observe_atlas() {
  local phase="$1"
  python3 - "$sort_root/material0.dds" \
    "$FOJ_EVIDENCE_DIR/generated-input.json" "$FOJ_SPATIAL_CASE" \
    "$FOJ_EVIDENCE_DIR/near-dds-$phase.sha256" <<'PY'
from pathlib import Path
from tools.foj_stage276_spatial_alpha_sd import near_atlas
from tools.foj_stage260_generated_gpu_sd import generated_dds
from tools.foj_stage266_transparency_order import VIOLET
import hashlib,json,sys
dds,manifest,case,out=Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3],Path(sys.argv[4])
if (dds.is_symlink() or manifest.is_symlink() or out.exists() or
    out.is_symlink() or not dds.is_file() or not manifest.is_file()):
    raise SystemExit("Stage276 unsafe DDS/manifest/witness path")
contents=dds.read_bytes()
expected=near_atlas(case)
meta=json.loads(manifest.read_text(encoding="utf-8"))
if (contents!=expected or meta.get("near_dds_sha256")!=
        hashlib.sha256(expected).hexdigest() or
    meta.get("near_original_dds_sha256")!=
        hashlib.sha256(generated_dds((*VIOLET,128))).hexdigest() or
    meta.get("scenario")!=case):
    raise SystemExit("Stage276 actual spatial-alpha DDS mismatch")
with out.open("x",encoding="ascii") as stream:
    stream.write(hashlib.sha256(contents).hexdigest()+"\n")
PY
}
observe_atlas before
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
from tools.foj_stage276_spatial_alpha_check import inspect
import os
try:
    inspect(Path(sys.argv[1]),os.environ['FOJ_SPATIAL_CASE'])
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
from tools.foj_stage276_spatial_alpha_check import inspect
import os
import sys
a,b=(Path(x) for x in sys.argv[1:])
try:
    inspect(b,os.environ['FOJ_SPATIAL_CASE'])
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
# Verify the *guest-NRO-created* draw-pass sequence, not a generator
# assertion or a host-synthesized receipt. It is created exclusively by
# the NRO after native C11 sorting, before GPU command submission.
test -f "$sort_marker" && test ! -L "$sort_marker" || {
  echo "Stage273 guest did not write native sort receipt" >&2
  exit 1
}
python3 - "$sort_marker" "$FOJ_SPATIAL_CASE" <<'PY'
from pathlib import Path
import sys
marker,scene=Path(sys.argv[1]),sys.argv[2]
if scene not in ("alpha-left-clear","alpha-right-clear"):
    raise SystemExit("Unexpected Stage276 spatial case")
expected=b"FOJ_NATIVE_SORT_V1 2,1,0\n"
if marker.read_bytes()!=expected:
    raise SystemExit("Native GPU draw pass receipt disagrees with scene")
PY
observe_atlas after
for reject in foj-native-rear-alpha-reject.txt foj-native-topology-reject.txt; do
  if [[ -e "$sort_root/$reject" || -L "$sort_root/$reject" ]]; then
    echo "Stage276 successful masked scene wrote a native rejection" >&2
    exit 1
  fi
done
pass_marker="$sort_root/foj-native-alpha-pass.txt"
test -s "$pass_marker" && test ! -L "$pass_marker"
python3 - "$pass_marker" <<'PY'
from pathlib import Path
import sys
expected=b"FOJ_NATIVE_ALPHA_PASS_V1 2:0:1:1 1:1:1:0 0:1:1:0\n"
if Path(sys.argv[1]).read_bytes()!=expected:
    raise SystemExit("Stage276 native material/blend/depth receipt mismatch")
PY
cp -- "$sort_marker" "$FOJ_EVIDENCE_DIR/native-sort-pass.txt"
cp -- "$pass_marker" "$FOJ_EVIDENCE_DIR/native-alpha-pass.txt"
echo "Stage276: two real NeXium frames with per-texel DDS alpha and bound native pass states"
