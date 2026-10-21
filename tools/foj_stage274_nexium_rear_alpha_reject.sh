#!/usr/bin/env bash
# Stage274: one invented rear DDS texel becomes 254-alpha. The opt-in
# native NRO must reject before GPU init; host-generated markers never pass.
set -euo pipefail
: "${NEXIUM_BIN:?}"
: "${FOJ_NRO:?}"
: "${NEXIUM_DATA_ROOT:?}"
: "${FOJ_EVIDENCE_DIR:?}"
test -s "$FOJ_NRO"
sd="$NEXIUM_DATA_ROOT/sdmc/switch/foj/gpu"
receipt="$sd/foj-native-rear-alpha-reject.txt"
for name in actor.fojrm actor.fojmat material0.dds material1.dds material2.dds \
            foj_actor.vert.dksh foj_triangle.frag.dksh; do
  test -s "$sd/$name" && test ! -L "$sd/$name"
done
for name in foj-native-rear-alpha-reject.txt foj-native-sort-pass.txt \
            foj-native-alpha-pass.txt; do
  if [[ -e "$sd/$name" || -L "$sd/$name" ]]; then
    echo "Stage274 refuses pre-existing guest markers" >&2
    exit 2
  fi
done
if compgen -G "$sd/foj-boot-*.txt" >/dev/null; then
  echo "Stage274 refuses pre-existing GPU boot journal" >&2
  exit 2
fi
mkdir -p "$FOJ_EVIDENCE_DIR"
# Before launching the guest, independently verify the exact DDS bytes
# and the manifest digests. A one-byte mutation claim on its own is not
# enough: the actual file must contain only that invented change.
python3 -m tools.foj_stage274_rear_dds_witness \
  --dds "$sd/material2.dds" \
  --manifest "$FOJ_EVIDENCE_DIR/generated-input.json" \
  --phase before \
  --output "$FOJ_EVIDENCE_DIR/rear-dds-before.json"
"$NEXIUM_BIN" "$FOJ_NRO" >"$FOJ_EVIDENCE_DIR/guest.log" 2>&1 &
guest=$!
trap 'kill -KILL "$guest" 2>/dev/null || true; wait "$guest" 2>/dev/null || true' EXIT
found=0
for attempt in $(seq 1 35); do
  sleep 1
  if [[ -f "$receipt" && ! -L "$receipt" ]]; then
    found=1
    break
  fi
  state="$(ps -o stat= -p "$guest" 2>/dev/null | tr -d ' ' || true)"
  if [[ -z "$state" || "$state" == Z* ]]; then
    break
  fi
done
if [[ "$found" != 1 ]]; then
  echo "Stage274 native rear-alpha refusal receipt never appeared" >&2
  tail -n 50 "$FOJ_EVIDENCE_DIR/guest.log" >&2 || true
  exit 1
fi
python3 - "$receipt" <<'PY'
from pathlib import Path
import sys
expected=b"FOJ_NATIVE_REAR_ALPHA_REJECT_V1 pre_gpu=1\n"
if Path(sys.argv[1]).read_bytes()!=expected:
    raise SystemExit("Stage274 native pre-GPU rejection marker mismatch")
PY
if [[ -e "$sd/foj-native-sort-pass.txt" ||
      -e "$sd/foj-native-alpha-pass.txt" ]] ||
   compgen -G "$sd/foj-boot-*.txt" >/dev/null; then
  echo "Stage274 unsafe DDS unexpectedly reached sort, state or GPU boot" >&2
  exit 1
fi
# Re-read the ACTUAL DDS after native guest exit/rejection; the positive
# proof requires the same invented single-byte-invalid input throughout.
python3 -m tools.foj_stage274_rear_dds_witness \
  --dds "$sd/material2.dds" \
  --manifest "$FOJ_EVIDENCE_DIR/generated-input.json" \
  --phase after \
  --output "$FOJ_EVIDENCE_DIR/rear-dds-after.json"
cp -- "$receipt" "$FOJ_EVIDENCE_DIR/native-rear-alpha-reject.txt"
echo "Stage274: native NRO rejected generated rear DDS before GPU boot"
