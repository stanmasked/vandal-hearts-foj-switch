#!/usr/bin/env bash
# Run one invented invalid actor in the real NeXium guest.
# Success requires a NEW exclusive SD marker authored by the guest NRO
# before GPU initialization. Absence or extra boot journal fails closed.
set -euo pipefail
: "${NEXIUM_BIN:?}"
: "${FOJ_NRO:?}"
: "${NEXIUM_DATA_ROOT:?}"
: "${FOJ_EVIDENCE_DIR:?}"
: "${FOJ_UNSAFE_CASE:?}"
case "$FOJ_UNSAFE_CASE" in crossing|reversed|coplanar) ;; *) exit 2;; esac
test -s "$FOJ_NRO"
src="$NEXIUM_DATA_ROOT/sdmc/switch/foj/gpu"
receipt="$src/foj-native-unsafe-reject.txt"
for name in actor.fojrm actor.fojmat material0.dds material1.dds material2.dds \
  foj_actor.vert.dksh foj_triangle.frag.dksh; do
  test -f "$src/$name" && test ! -L "$src/$name" && test -s "$src/$name"
done
test ! -e "$receipt" && test ! -L "$receipt" || {
  echo "Refusing pre-existing native rejection marker" >&2; exit 2;
}
# No old boot journals or marker state are permitted in this brand-new root.
if compgen -G "$src/foj-boot-*.txt" >/dev/null; then
  echo "An old native GPU boot journal exists" >&2; exit 2
fi
mkdir -p "$FOJ_EVIDENCE_DIR"
"$NEXIUM_BIN" "$FOJ_NRO" >"$FOJ_EVIDENCE_DIR/guest.log" 2>&1 &
guest=$!
trap 'kill -KILL "$guest" 2>/dev/null || true; wait "$guest" 2>/dev/null || true' EXIT
found=0
for attempt in $(seq 1 35); do
  sleep 1
  if test -f "$receipt" && test ! -L "$receipt"; then
    found=1
    break
  fi
  # A guest process may exit immediately on successful early rejection.
  # An exited process is not proof: the exact marker is still mandatory.
  state="$(ps -o stat= -p "$guest" 2>/dev/null | tr -d ' ' || true)"
  if [[ -z "$state" || "$state" == Z* ]]; then
    break
  fi
done
if [[ "$found" != 1 ]]; then
  echo "No native guest rejection receipt was observed" >&2
  tail -n 70 "$FOJ_EVIDENCE_DIR/guest.log" >&2 || true
  exit 1
fi
# Exit before command list / boot-journal initialization is the intended
# guard contract; the actual guest numeric exit status may not be exposed
# by the graphical NeXium process.
python3 - "$receipt" <<'PY'
from pathlib import Path
import sys
path=Path(sys.argv[1])
assert path.read_bytes()==b"FOJ_NATIVE_UNSAFE_REJECT_V1 exit=8 pre_gpu=1\n", "Wrong native rejection marker"
PY
if compgen -G "$src/foj-boot-*.txt" >/dev/null; then
  echo "A GPU boot journal exists: early-return guarantee violated" >&2
  exit 1
fi
cp -- "$receipt" "$FOJ_EVIDENCE_DIR/native-reject.txt"
echo "Native early-rejection marker observed in NeXium for $FOJ_UNSAFE_CASE"
