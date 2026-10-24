#!/usr/bin/env bash
# Stage340 captures real NeXium frames after a Stage332/339-decoded DDS has
# been uploaded through Stage336. Public CI must supply only a generated DDS.
set -euo pipefail
: "${NEXIUM_BIN:?}"
: "${FOJ_NRO:?}"
: "${NEXIUM_DATA_ROOT:?}"
: "${FOJ_EVIDENCE_DIR:?}"
test -s "$FOJ_NRO"
sd="$NEXIUM_DATA_ROOT/sdmc/switch/foj/gpu"
source_dds="$sd/material0.dds"
marker="$sd/foj-stage340-private-dds-gpu.txt"
test -d "$sd" && test ! -L "$sd"
test -f "$source_dds" && test ! -L "$source_dds" && test -s "$source_dds"
test "$(wc -c < "$source_dds")" -le 33554432
test -s "$sd/foj_actor.vert.dksh"
test -s "$sd/foj_triangle.frag.dksh"
test ! -e "$marker" && test ! -L "$marker" || {
  echo "Stage340 refuses a stale native GPU receipt" >&2
  exit 2
}
mkdir -p "$FOJ_EVIDENCE_DIR"
for name in "$marker" "$FOJ_EVIDENCE_DIR/gpu-initial.png" \
            "$FOJ_EVIDENCE_DIR/gpu-later.png" \
            "$FOJ_EVIDENCE_DIR/$MARKER_NAME" \
            "$FOJ_EVIDENCE_DIR/stage340-gpu-frame-receipt.json" \
            "$FOJ_EVIDENCE_DIR/guest.log"; do
  test ! -e "$name" && test ! -L "$name" || {
    echo "Stage340 refuses pre-existing evidence" >&2
    exit 2
  }
done
before="$(sha256sum "$source_dds" | cut -d' ' -f1)"
"$NEXIUM_BIN" "$FOJ_NRO" >"$FOJ_EVIDENCE_DIR/guest.log" 2>&1 &
guest=$!
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
    local boot_file line
    for boot_file in "$sd"/foj-boot-??.txt; do
      [[ -f "$boot_file" && ! -L "$boot_file" ]] || continue
      line="$(tail -n 1 "$boot_file" 2>/dev/null || true)"
      if [[ "$line" =~ ^FOJBOOT1\ slot=[0-9]{2}\ step=([0-9]{2})\ event=([0-9])\ frames=([0-9]{10})$ ]]; then
        boot_record="step=${BASH_REMATCH[1]},event=${BASH_REMATCH[2]},frames=${BASH_REMATCH[3]}"
        break
      fi
    done
    printf 'STAGE340_EARLY_EXIT_DIAG_V1 guest_exit=%s receipt=%s guest_log_bytes=%s boot=%s\n' \
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
    echo "Stage340 guest exited without a sampled DDS frame" >&2
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
test -n "$window" || { echo "Stage340 missing NeXium GUI" >&2; exit 1; }
for attempt in $(seq 1 45); do
  sleep 1
  alive
  if [[ -f "$marker" && ! -L "$marker" ]]; then break; fi
done
test -f "$marker" && test ! -L "$marker" || {
  echo "Stage340 native DDS upload/sample receipt never appeared" >&2
  exit 1
}
found=0
for attempt in $(seq 1 38); do
  sleep 2
  alive
  if timeout --kill-after=2s 12s import -window "$window" \
       "$FOJ_EVIDENCE_DIR/gpu-initial.png"; then
    if python3 -m tools.foj_stage340_private_dds_gate frame \
         --image "$FOJ_EVIDENCE_DIR/gpu-initial.png" \
         --source-dds "$source_dds" >/dev/null; then
      found=1
      break
    fi
  fi
done
test "$found" = 1 || {
  echo "Stage340 DDS pixels never appeared in the real GPU framebuffer" >&2
  exit 1
}
found=0
for attempt in $(seq 1 30); do
  sleep .5
  alive
  if timeout --kill-after=2s 12s import -window "$window" \
       "$FOJ_EVIDENCE_DIR/gpu-later.png"; then
    if python3 -m tools.foj_stage340_private_dds_gate frame \
         --image "$FOJ_EVIDENCE_DIR/gpu-later.png" \
         --source-dds "$source_dds" >/dev/null; then
      found=1
      break
    fi
  fi
done
test "$found" = 1 || {
  echo "Stage340 second GPU frame did not match the DDS CPU oracle" >&2
  exit 1
}
after="$(sha256sum "$source_dds" | cut -d' ' -f1)"
test "$before" = "$after" || {
  echo "Stage340 source DDS changed during GPU run" >&2
  exit 1
}
cp -- "$marker" "$FOJ_EVIDENCE_DIR/foj-stage340-private-dds-gpu.txt"
args=(audit --source-dds "$source_dds" --evidence "$FOJ_EVIDENCE_DIR" --expected-sha256 "$before")
if [[ "${FOJ_ORIGINAL_PS3_ASSET:-0}" == "1" ]]; then
  args+=(--original-ps3)
fi
python3 -m tools.foj_stage340_private_dds_gate "${args[@]}"
echo STAGE340_REAL_NEIXIUM_PRIVATE_DDS_SAMPLE_PASS
