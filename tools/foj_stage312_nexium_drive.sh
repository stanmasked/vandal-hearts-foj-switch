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
guest_exit_code=unavailable
cleanup() {
  local run_status=$?
  if (( run_status != 0 )); then
    local log_bytes=0 boot_record=none progress_record=none
    local progress_file="$sd/foj-stage312-frame-progress.txt" progress_line
    local last_frames=none
    if [[ -f "$FOJ_EVIDENCE_DIR/guest.log" &&
          ! -L "$FOJ_EVIDENCE_DIR/guest.log" ]]; then
      log_bytes="$(wc -c < "$FOJ_EVIDENCE_DIR/guest.log")"
    fi
    # The journal contains only fixed numeric stage/event/frame fields.
    # Never print or upload raw guest.log or any free-form guest text.
    local boot_file line
    for boot_file in "$sd"/foj-boot-??.txt; do
      [[ -f "$boot_file" && ! -L "$boot_file" ]] || continue
      line="$(tail -n 1 "$boot_file" 2>/dev/null || true)"
      if [[ "$line" =~ ^FOJBOOT1\ slot=[0-9]{2}\ step=([0-9]{2})\ event=([0-9])\ frames=([0-9]{10})$ ]]; then
        boot_record="$line"
        break
      fi
    done
    if [[ -f "$progress_file" && ! -L "$progress_file" ]]; then
      progress_line="$(grep -E '^FOJ312P1 phase=[0-7]$' "$progress_file" 2>/dev/null | tail -n 1 || true)"
      if [[ "$progress_line" =~ ^FOJ312P1\ phase=([0-7])$ ]]; then
        progress_record="phase=${BASH_REMATCH[1]}"
      fi
      progress_line="$(grep -E '^FOJ312F1 frames=[0-9]{10}$' "$progress_file" 2>/dev/null | tail -n 1 || true)"
      if [[ "$progress_line" =~ ^FOJ312F1\ frames=([0-9]{10})$ ]]; then
        last_frames="${BASH_REMATCH[1]}"
      fi
    fi
    printf 'STAGE312_EARLY_EXIT_DIAG_V3 guest_exit=%s guest_log_bytes=%s boot=%s progress=%s present_frames=%s\n' \
      "$guest_exit_code" "$log_bytes" "$boot_record" "$progress_record" "$last_frames" >&2
    # The workflow attests all generated-only DDS inputs before launch.
    # Print only ten fixed RGB tuples, never screenshot or raw guest logs.
    if [[ -f "$FOJ_EVIDENCE_DIR/gpu-initial.png" &&
          ! -L "$FOJ_EVIDENCE_DIR/gpu-initial.png" ]]; then
      python3 - "$FOJ_EVIDENCE_DIR/gpu-initial.png" <<'PY'
from PIL import Image
from pathlib import Path
import sys
try:
    with Image.open(Path(sys.argv[1])) as opened:
        if opened.size != (1280,720):
            raise ValueError("Wrong dimensions")
        pixels=opened.convert("RGB")
    positions=((315,280),(315,346),(315,460),
               (685,280),(685,346),(685,460),
               (962,280),(962,346),(962,460),(315,360))
    samples=(",".join(str(channel) for channel in pixels.getpixel(pos))
             for pos in positions)
    print("STAGE312_LAST_FRAME_RGB_V1 "+" ".join(samples),file=sys.stderr)
except (OSError,ValueError):
    print("STAGE312_LAST_FRAME_RGB_V1 unavailable",file=sys.stderr)
PY
    fi
  fi
  kill -KILL "$guest" 2>/dev/null || true
  wait "$guest" 2>/dev/null || true
}
trap cleanup EXIT
alive() {
  state="$(ps -o stat= -p "$guest" 2>/dev/null | tr -d ' ' || true)"
  if [[ -z "$state" || "$state" == Z* ]] || ! kill -0 "$guest" 2>/dev/null; then
    guest_exit_code=0
    wait "$guest" || guest_exit_code=$?
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
capture_window_png() {
  local output="$1"
  local xwd_file="${output%.png}.xwd"
  timeout --kill-after=2s 12s xwd -silent -id "$window" -out "$xwd_file"
  timeout --kill-after=2s 12s bash -o pipefail -c \
    'xwdtopnm "$1" | pnmtopng > "$2"' _ "$xwd_file" "$output"
  rm -f -- "$xwd_file"
}
# Never conflate the initial 12 diagnostic guest frames with the
# actual texture GPU draw; require BOTH colors in a single screenshot.
found=0
for attempt in $(seq 1 38); do
  sleep 5
  alive
  capture_window_png "$FOJ_EVIDENCE_DIR/gpu-initial.png"
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
  capture_window_png "$FOJ_EVIDENCE_DIR/gpu-later.png"
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
progress_file="$sd/foj-stage312-frame-progress.txt"
test -f "$progress_file" && test ! -L "$progress_file"
progress_line="$(grep -E '^FOJ312P1 phase=[0-7]$' "$progress_file" | tail -n 1)"
[[ "$progress_line" == "FOJ312P1 phase=7" ]] || {
  echo "Stage312 first-frame presentation checkpoint incomplete" >&2
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
