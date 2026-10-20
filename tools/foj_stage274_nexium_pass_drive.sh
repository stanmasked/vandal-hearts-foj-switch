#!/usr/bin/env bash
# Stage274 wraps the existing real Stage273 NeXium RGB + native draw-order
# capture, then verifies a *second*, independently guest-written receipt
# of the actual bound texture, blending and depth states.
set -euo pipefail
: "${FOJ_DYNAMIC_CASE:?}"
: "${NEXIUM_DATA_ROOT:?}"
: "${FOJ_EVIDENCE_DIR:?}"
case "$FOJ_DYNAMIC_CASE" in original|reversed) ;; *) exit 2;; esac
sd="$NEXIUM_DATA_ROOT/sdmc/switch/foj/gpu"
marker="$sd/foj-native-alpha-pass.txt"
reject_marker="$sd/foj-native-rear-alpha-reject.txt"
if [[ -e "$marker" || -L "$marker" ||
      -e "$reject_marker" || -L "$reject_marker" ]]; then
  echo "Stage274 refuses pre-existing pass or rear-alpha reject receipt" >&2
  exit 2
fi
bash tools/foj_stage273_nexium_dynamic_gpu_drive.sh
# A successful scene must not produce *both* acceptance and rejection
# witnesses. The negative guest has a separate strict assertion.
if [[ -e "$reject_marker" || -L "$reject_marker" ]]; then
  echo "Stage274 positive NeXium scene emitted rear-alpha rejection" >&2
  exit 1
fi
if [[ ! -f "$marker" || -L "$marker" ]]; then
  echo "Stage274 native NRO did not provide per-pass GPU state" >&2
  exit 1
fi
python3 - "$marker" "$FOJ_DYNAMIC_CASE" <<'PY'
from pathlib import Path
import sys
path,case=Path(sys.argv[1]),sys.argv[2]
expected={
    "original":b"FOJ_NATIVE_ALPHA_PASS_V1 2:0:1:1 1:1:1:0 0:1:1:0\n",
    "reversed":b"FOJ_NATIVE_ALPHA_PASS_V1 2:0:1:1 0:1:1:0 1:1:1:0\n",
}[case]
if path.read_bytes()!=expected:
    raise SystemExit("Stage274 guest-native material/blend/depth marker mismatch")
PY
cp -- "$marker" "$FOJ_EVIDENCE_DIR/native-alpha-pass.txt"
echo "Stage274 bound GPU pass states matched native witness and actual NeXium RGB frames"
