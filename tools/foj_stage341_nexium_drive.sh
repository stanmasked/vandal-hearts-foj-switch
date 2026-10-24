#!/usr/bin/env bash
# Stage341 captures two real NeXium frames for the bounded native DDS shader quad.
# Raw frames and guest logs are local evidence only and must never be public artifacts.
set -euo pipefail
: "${NEXIUM_BIN:?}"
: "${FOJ_NRO:?}"
: "${NEXIUM_DATA_ROOT:?}"
: "${FOJ_EVIDENCE_DIR:?}"
test -s "$FOJ_NRO"
sd="$NEXIUM_DATA_ROOT/sdmc/switch/foj/gpu"
marker="$sd/foj-stage341-private-dds-frame-ready.txt"
test -d "$sd" && test ! -L "$sd"
test -f "$sd/source.dds" && test ! -L "$sd/source.dds"
test -s "$sd/foj_actor.vert.dksh" && test ! -L "$sd/foj_actor.vert.dksh"
test -s "$sd/foj_triangle.frag.dksh" && test ! -L "$sd/foj_triangle.frag.dksh"
[[ "$(stat -c %s "$sd/source.dds")" -eq 262272 ]]
for path in "$marker" "$sd/foj-native-stage330-partition-draw-upload.txt"; do
  test ! -e "$path" && test ! -L "$path" || {
    echo "Stage341 refuses a stale guest marker" >&2
    exit 2
  }
done
mkdir -p "$FOJ_EVIDENCE_DIR"
test ! -L "$FOJ_EVIDENCE_DIR"
for name in source-before.sha256 source-after.sha256 ready-marker.txt gpu-initial.png gpu-later.png guest.log; do
  test ! -e "$FOJ_EVIDENCE_DIR/$name" && test ! -L "$FOJ_EVIDENCE_DIR/$name" || {
    echo "Stage341 refuses pre-existing evidence output" >&2
    exit 2
  }
done
for entry in "$FOJ_EVIDENCE_DIR"/*; do
  [[ -e "$entry" || -L "$entry" ]] || continue
  case "$(basename "$entry")" in
    generated-input.json|nexium-archive.sha256) ;;
    *) echo "Stage341 evidence directory has an unexpected pre-run file" >&2; exit 2 ;;
  esac
  test -f "$entry" && test ! -L "$entry"
done
sha256sum "$sd/source.dds" | awk '{print $1}' > "$FOJ_EVIDENCE_DIR/source-before.sha256"
"$NEXIUM_BIN" "$FOJ_NRO" >"$FOJ_EVIDENCE_DIR/guest.log" 2>&1 &
guest=$!
guest_exit_code=unavailable
cleanup() {
  local run_status=$?
  if (( run_status != 0 )); then
    # Only fixed numeric metadata is written to public step output.
    local marker_present=0
    if [[ -f "$marker" && ! -L "$marker" ]]; then marker_present=1; fi
    printf 'STAGE341_EARLY_EXIT_V1 guest_exit=%s ready_marker=%s\n' \
      "$guest_exit_code" "$marker_present" >&2
  fi
  kill -KILL "$guest" 2>/dev/null || true
  wait "$guest" 2>/dev/null || true
}
trap cleanup EXIT
alive() {
  local state
  state="$(ps -o stat= -p "$guest" 2>/dev/null | tr -d ' ' || true)"
  if [[ -z "$state" || "$state" == Z* ]] || ! kill -0 "$guest" 2>/dev/null; then
    guest_exit_code=0
    wait "$guest" || guest_exit_code=$?
    echo "Stage341 guest exited before the native frame-ready marker" >&2
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
test -n "$window" || { echo "Stage341 missing real NeXium GUI" >&2; exit 1; }
ready=0
for attempt in $(seq 1 45); do
  sleep 1
  alive
  if [[ -f "$marker" && ! -L "$marker" ]]; then ready=1; break; fi
done
test "$ready" = 1 || { echo "Stage341 native frame-ready marker missing" >&2; exit 1; }
cp -- "$marker" "$FOJ_EVIDENCE_DIR/ready-marker.txt"
# The inset quad leaves the alternating clear color visible at (20,20).
# Capture the second frame only after that border changes; do not accept stale
# or duplicate captures just because the file exists.
found=0
for attempt in $(seq 1 24); do
  alive
  if timeout --kill-after=2s 12s import -window "$window" \
       "$FOJ_EVIDENCE_DIR/gpu-initial.png"; then
    break
  fi
  sleep .5
done
test -s "$FOJ_EVIDENCE_DIR/gpu-initial.png" || {
  echo "Stage341 failed to capture first NeXium framebuffer" >&2
  exit 1
}
tmp="$FOJ_EVIDENCE_DIR/.gpu-later-candidate.png"
for attempt in $(seq 1 24); do
  sleep .5
  alive
  rm -f -- "$tmp"
  if ! timeout --kill-after=2s 12s import -window "$window" "$tmp"; then
    continue
  fi
  if python3 - "$FOJ_EVIDENCE_DIR/gpu-initial.png" "$tmp" <<'PY'
from pathlib import Path
import sys
from PIL import Image
try:
    with Image.open(Path(sys.argv[1])) as a, Image.open(Path(sys.argv[2])) as b:
        if a.size != (1280, 720) or b.size != (1280, 720):
            raise SystemExit(1)
        if a.convert("RGB").getpixel((20, 20)) != b.convert("RGB").getpixel((20, 20)):
            raise SystemExit(0)
except (OSError, ValueError):
    pass
raise SystemExit(1)
PY
  then
    mv -- "$tmp" "$FOJ_EVIDENCE_DIR/gpu-later.png"
    found=1
    break
  fi
done
rm -f -- "$tmp"
test "$found" = 1 || {
  echo "Stage341 did not capture a second frame with a distinct clear-color phase" >&2
  exit 1
}
sha256sum "$sd/source.dds" | awk '{print $1}' > "$FOJ_EVIDENCE_DIR/source-after.sha256"
echo STAGE341_NEIXIUM_TWO_FRAME_CAPTURE_COMPLETE
