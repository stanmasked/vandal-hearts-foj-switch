#!/usr/bin/env bash
# Actual Stage312 guest execution. Synthetic-only: refuse material-identity
# failures and never publish raw log/private files. Two real NeXium captures.
set -euo pipefail
: "${NEXIUM_BIN:?}"
: "${FOJ_NRO:?}"
: "${NEXIUM_DATA_ROOT:?}"
: "${FOJ_EVIDENCE_DIR:?}"
test -s "$FOJ_NRO"
sd="$NEXIUM_DATA_ROOT/sdmc/switch/foj/gpu"
marker="$sd/foj-native-stage312-horizontal-gutter-pass.txt"
test ! -e "$marker" && test ! -L "$marker" || {
  echo "Stage312 refuses stale GPU split marker" >&2;exit 2;
}
for f in actor.fojrm actor.fojmat material0.dds material1.dds material2.dds     foj_actor.vert.dksh foj_triangle.frag.dksh; do
  test -s "$sd/$f"
done
mkdir -p "$FOJ_EVIDENCE_DIR"
"$NEXIUM_BIN" "$FOJ_NRO" >"$FOJ_EVIDENCE_DIR/guest.log" 2>&1 &
guest=$!
trap 'kill -KILL "$guest" 2>/dev/null || true;wait "$guest" 2>/dev/null || true' EXIT
alive() {
  state="$(ps -o stat= -p "$guest" 2>/dev/null | tr -d ' ' || true)"
  if [[ -z "$state" || "$state" == Z* ]] || ! kill -0 "$guest" 2>/dev/null; then
    echo "Stage312 guest died before contrasting-edge GPU screenshot" >&2
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
test -n "$window" || { echo "Stage312 missing real NeXium GUI" >&2;exit 1; }
# Never conflate the initial 360 diagnostic guest frames with the
# actual texture GPU draw; require BOTH colors in a single screenshot.
found=0
for attempt in $(seq 1 38); do
  sleep 5
  alive
  timeout --kill-after=2s 12s import -window "$window"     "$FOJ_EVIDENCE_DIR/gpu-initial.png"
  if python3 - "$FOJ_EVIDENCE_DIR/gpu-initial.png" <<'PY'
from pathlib import Path
import sys
from tools.foj_stage312_horizontal_gpu_guest import _frame
try:_frame(Path(sys.argv[1]))
except (OSError,ValueError):raise SystemExit(1)
PY
  then found=1;break;fi
done
if [[ "$found" != 1 ]]; then
  echo "Stage312 horizontal eight-band BC1 gutter never reached actual GPU frame" >&2
  exit 1
fi
phase=0
for attempt in $(seq 1 30); do
  sleep .5
  alive
  timeout --kill-after=2s 12s import -window "$window"     "$FOJ_EVIDENCE_DIR/gpu-later.png"
  if python3 - "$FOJ_EVIDENCE_DIR/gpu-initial.png"                  "$FOJ_EVIDENCE_DIR/gpu-later.png" <<'PY'
from pathlib import Path
import sys
from tools.foj_stage312_horizontal_gpu_guest import _frame,phase_changed
a,b=(Path(z) for z in sys.argv[1:])
try:
    _frame(b)
    if not phase_changed(a,b):raise ValueError("No phase transition")
except (OSError,ValueError):
    raise SystemExit(1)
PY
  then phase=1;break;fi
done
test "$phase" = 1 || {
  echo "Stage312 guest did not display two different GPU clear phases" >&2
  exit 1
}
test -s "$FOJ_EVIDENCE_DIR/gpu-initial.png"
test -s "$FOJ_EVIDENCE_DIR/gpu-later.png"
test -f "$marker" && test ! -L "$marker"
python3 - "$marker" <<'PY'
from pathlib import Path
import sys
m=Path(sys.argv[1]).read_bytes()
if m!=b"FOJ_NATIVE_STAGE312_HORIZONTAL_GUTTER_V1 pairs=8 columns=256 strict_mix=256 pages=1,1+1,2 verts=18\n":
    raise SystemExit("Stage312 guest-native page/vertex receipt disagrees")
PY
cp -- "$marker" "$FOJ_EVIDENCE_DIR/native-stage312-horizontal-gutter-pass.txt"
echo STAGE312_REAL_NEIXUM_SAME_FRAME_BC1_PAGES_CAPTURED
