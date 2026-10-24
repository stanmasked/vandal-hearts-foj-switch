#!/usr/bin/env bash
# Run an actual deko3d GPU image transfer/readback in an isolated guest.
# Native marker is valid only after two completed GPU submissions AND a
# byte-for-byte compare inside the NRO. Never export uncontrolled guest logs.
set -euo pipefail
: "${NEXIUM_BIN:?}" "${FOJ_NRO:?}" "${NEXIUM_DATA_ROOT:?}" "${FOJ_EVIDENCE_DIR:?}"
sd="$NEXIUM_DATA_ROOT/sdmc/switch/foj/gpu"
marker="$sd/foj-stage337-native-roundtrip.txt"
progress_path="$sd/foj-stage337-progress.txt"
test -s "$FOJ_NRO"
test -d "$sd" && test ! -L "$sd"
test ! -e "$marker" && test ! -L "$marker" && \
     test ! -e "$progress_path" && test ! -L "$progress_path" || {
  echo 'Stage337 refuses preexisting success marker' >&2; exit 2;
}
mkdir -p "$FOJ_EVIDENCE_DIR"
test ! -e "$FOJ_EVIDENCE_DIR/guest.log" || exit 2
"$NEXIUM_BIN" "$FOJ_NRO" > "$FOJ_EVIDENCE_DIR/guest.log" 2>&1 &
guest=$!
cleanup() {
  local result=$?
  if (( result != 0 )); then
    # Report only fixed syntax and a two-digit progress code; never guest.log.
    local stage=none line=""
    if [[ -f "$progress_path" && ! -L "$progress_path" ]] &&
       [[ "$(wc -c < "$progress_path")" -le 512 ]]; then
      line="$(tail -n 1 "$progress_path" 2>/dev/null || true)"
      if [[ "$line" =~ ^FOJ337P1\ stage=([0-9]{2})$ ]]; then
        stage="${BASH_REMATCH[1]}"
      fi
    fi
    printf 'STAGE337_BOUNDED_GUEST_DIAG last_stage=%s\n' "$stage" >&2
  fi
  kill -KILL "$guest" 2>/dev/null || true
  wait "$guest" 2>/dev/null || true
}
trap cleanup EXIT
for n in $(seq 1 150); do
  if [[ -f "$marker" && ! -L "$marker" ]]; then
    python3 -m tools.foj_stage337_receipt check --receipt "$marker"
    python3 -m tools.foj_stage337_receipt publish \
       --receipt "$marker" --output "$FOJ_EVIDENCE_DIR"
    echo STAGE337_REAL_NEIXIUM_IMAGE_GPU_COPY_READBACK_PASS
    exit 0
  fi
  state="$(ps -o stat= -p "$guest" 2>/dev/null | tr -d ' ' || true)"
  if [[ -z "$state" || "$state" == Z* ]] || ! kill -0 "$guest" 2>/dev/null; then
    # A rapidly exiting successful homebrew may have written its marker.
    if [[ -f "$marker" && ! -L "$marker" ]]; then
      python3 -m tools.foj_stage337_receipt check --receipt "$marker"
      python3 -m tools.foj_stage337_receipt publish \
         --receipt "$marker" --output "$FOJ_EVIDENCE_DIR"
      echo STAGE337_REAL_NEIXIUM_IMAGE_GPU_COPY_READBACK_PASS
      exit 0
    fi
    echo 'Stage337 guest exited without a native GPU readback witness' >&2
    exit 1
  fi
  sleep 1
done
echo 'Stage337 timed out without GPU-copy readback witness' >&2
exit 1
