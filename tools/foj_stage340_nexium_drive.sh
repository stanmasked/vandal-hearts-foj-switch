#!/usr/bin/env bash
# Stage340 generated-only NeXium run. Never export guest.log, DDS bytes or progress.
set -euo pipefail
: "${NEXIUM_BIN:?}" "${FOJ_NRO:?}" "${NEXIUM_DATA_ROOT:?}" "${FOJ_EVIDENCE_DIR:?}"
sd="$NEXIUM_DATA_ROOT/sdmc"
gpu="$sd/switch/foj/gpu"
marker="$gpu/foj-stage340-native-dds-roundtrip.txt"
progress="$gpu/foj-stage340-progress.txt"
test -s "$FOJ_NRO"
test -d "$gpu" && test ! -L "$gpu"
test -s "$gpu/source.dds" && test ! -L "$gpu/source.dds"
python3 -m tools.foj_stage340_fixture verify --path "$gpu/source.dds" >/dev/null
test ! -e "$marker" && test ! -L "$marker" && \
     test ! -e "$progress" && test ! -L "$progress" || {
  echo 'Stage340 refuses preexisting GPU success/progress markers' >&2; exit 2;
}
mkdir -p "$FOJ_EVIDENCE_DIR"
test ! -e "$FOJ_EVIDENCE_DIR/guest.log" || exit 2
"$NEXIUM_BIN" "$FOJ_NRO" > "$FOJ_EVIDENCE_DIR/guest.log" 2>&1 &
guest=$!
cleanup() {
  local result=$?
  if (( result != 0 )); then
    local stage=none line=""
    if [[ -f "$progress" && ! -L "$progress" ]] &&
       [[ "$(wc -c < "$progress")" -le 512 ]]; then
      line="$(tail -n 1 "$progress" 2>/dev/null || true)"
      if [[ "$line" =~ ^FOJ340P1\ stage=([0-9]{2})$ ]]; then
        stage="${BASH_REMATCH[1]}"
      fi
    fi
    printf 'STAGE340_BOUNDED_GUEST_DIAG last_stage=%s\n' "$stage" >&2
  fi
  kill -KILL "$guest" 2>/dev/null || true
  wait "$guest" 2>/dev/null || true
}
trap cleanup EXIT
for n in $(seq 1 150); do
  if [[ -f "$marker" && ! -L "$marker" ]]; then
    python3 -m tools.foj_stage340_receipt check \
      --sd-root "$sd" --evidence "$FOJ_EVIDENCE_DIR"
    python3 -m tools.foj_stage340_fixture verify --path "$gpu/source.dds" >/dev/null
    echo STAGE340_REAL_NEIXIUM_GENERATED_DDS_GPU_ROUNDTRIP_PASS
    exit 0
  fi
  state="$(ps -o stat= -p "$guest" 2>/dev/null | tr -d ' ' || true)"
  if [[ -z "$state" || "$state" == Z* ]] || ! kill -0 "$guest" 2>/dev/null; then
    if [[ -f "$marker" && ! -L "$marker" ]]; then
      python3 -m tools.foj_stage340_receipt check \
        --sd-root "$sd" --evidence "$FOJ_EVIDENCE_DIR"
      python3 -m tools.foj_stage340_fixture verify --path "$gpu/source.dds" >/dev/null
      echo STAGE340_REAL_NEIXIUM_GENERATED_DDS_GPU_ROUNDTRIP_PASS
      exit 0
    fi
    echo 'Stage340 guest exited without a native DDS GPU readback witness' >&2
    exit 1
  fi
  sleep 1
done
echo 'Stage340 timed out without native DDS GPU readback witness' >&2
exit 1
