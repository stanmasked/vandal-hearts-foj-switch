#!/usr/bin/env bash
# Stage329 runs the generated-only corner patch NRO and captures real NeXium
# frames. The upload marker alone is never accepted as GPU rendering evidence.
set -euo pipefail
: "${NEXIUM_BIN:?}"
: "${FOJ_NRO:?}"
: "${NEXIUM_DATA_ROOT:?}"
: "${FOJ_EVIDENCE_DIR:?}"
test -s "$FOJ_NRO"
sd="$NEXIUM_DATA_ROOT/sdmc/switch/foj/gpu"
marker="$sd/foj-native-stage329-corner-patch-upload.txt"
test -s "$sd/foj_actor.vert.dksh"
test -s "$sd/foj_triangle.frag.dksh"
test ! -e "$marker" && test ! -L "$marker" || {
  echo "Stage329 refuses a stale native upload marker" >&2
  exit 2
}
mkdir -p "$FOJ_EVIDENCE_DIR"
"$NEXIUM_BIN" "$FOJ_NRO" >"$FOJ_EVIDENCE_DIR/guest.log" 2>&1 &
guest=$!
# Capture only bounded, synthetic-only metadata when the guest dies.
# NEVER print or upload guest.log: it may include uncontrolled paths or text.
guest_exit_code=unavailable
cleanup() {
  local run_status=$?
  if (( run_status != 0 )); then
    local marker_present=0 log_bytes=0 boot_record=none
    if [[ -f "$marker" && ! -L "$marker" ]]; then marker_present=1; fi
    if [[ -f "$FOJ_EVIDENCE_DIR/guest.log" &&
          ! -L "$FOJ_EVIDENCE_DIR/guest.log" ]]; then
      log_bytes="$(wc -c < "$FOJ_EVIDENCE_DIR/guest.log")"
    fi
    # FOJBOOT1 is a fixed numeric format written by our own NRO.
    # Ignore any unexpected text and all other guest-generated files.
    local boot_file line
    for boot_file in "$sd"/foj-boot-0?.txt; do
      [[ -f "$boot_file" && ! -L "$boot_file" ]] || continue
      line="$(tail -n 1 "$boot_file" 2>/dev/null || true)"
      if [[ "$line" =~ ^FOJBOOT1\ slot=[0-9]{2}\ step=([0-9]{2})\ event=([0-9])\ frames=([0-9]{10})$ ]]; then
        boot_record="step=${BASH_REMATCH[1]},event=${BASH_REMATCH[2]},frames=${BASH_REMATCH[3]}"
        break
      fi
    done
    printf 'STAGE329_EARLY_EXIT_DIAG_V1 guest_exit=%s upload_marker=%s guest_log_bytes=%s boot=%s\n' \
      "$guest_exit_code" "$marker_present" "$log_bytes" "$boot_record" >&2
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
    echo "Stage329 guest died before its real GPU patch frame" >&2
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
test -n "$window" || { echo "Stage329 missing real NeXium GUI" >&2; exit 1; }
# Wait for the NRO to submit and drain the tile upload. This is only a
# prerequisite; the actual framebuffer must pass the independent image audit.
for attempt in $(seq 1 45); do
  sleep 1
  alive
  if [[ -f "$marker" && ! -L "$marker" ]]; then break; fi
done
test -f "$marker" && test ! -L "$marker" || {
  echo "Stage329 native texture upload receipt never appeared" >&2
  exit 1
}
found=0
for attempt in $(seq 1 38); do
  sleep 5
  alive
  if timeout --kill-after=2s 12s import -window "$window" \
       "$FOJ_EVIDENCE_DIR/gpu-initial.png"; then
    if python3 -m tools.foj_stage329_corner_patch_guest frame \
         --image "$FOJ_EVIDENCE_DIR/gpu-initial.png" >/dev/null; then
      found=1
      break
    fi
  fi
done
test "$found" = 1 || {
  echo "Stage329 generated corner-patch gradient never appeared on GPU" >&2
  exit 1
}
phase=0
for attempt in $(seq 1 30); do
  sleep .5
  alive
  if timeout --kill-after=2s 12s import -window "$window" \
       "$FOJ_EVIDENCE_DIR/gpu-later.png"; then
    if python3 - "$FOJ_EVIDENCE_DIR/gpu-initial.png" \
                 "$FOJ_EVIDENCE_DIR/gpu-later.png" <<'PY'
from pathlib import Path
import sys
from PIL import Image, ImageChops
from tools.foj_stage329_corner_patch_guest import _frame
a,b=(Path(value) for value in sys.argv[1:])
try:
    _frame(b)
    with Image.open(a) as first, Image.open(b) as later:
        if ImageChops.difference(first.convert("RGB"),later.convert("RGB")).getbbox():
            raise SystemExit(0)
except (OSError,ValueError):
    pass
raise SystemExit(1)
PY
    then
      phase=1
      break
    fi
  fi
done
test "$phase" = 1 || {
  echo "Stage329 did not capture two distinct real GPU frames" >&2
  exit 1
}
cp -- "$marker" "$FOJ_EVIDENCE_DIR/native-stage329-corner-patch-upload.txt"
python3 -m tools.foj_stage329_corner_patch_guest audit \
  --evidence "$FOJ_EVIDENCE_DIR"
echo STAGE329_REAL_NEIXIUM_CORNER_PATCH_GPU_PASS
