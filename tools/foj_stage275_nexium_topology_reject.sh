#!/usr/bin/env bash
# Two genuine NeXium guest refusals of invented crossing/coplanar geometry.
# Only the actual Stage275 NRO may create the early topology marker.
set -euo pipefail
: "${NEXIUM_BIN:?}"
: "${FOJ_NRO:?}"
: "${NEXIUM_DATA_ROOT:?}"
: "${FOJ_EVIDENCE_DIR:?}"
: "${FOJ_TOPOLOGY_CASE:?}"
case "$FOJ_TOPOLOGY_CASE" in crossing|coplanar) ;; *) exit 2;; esac
test -s "$FOJ_NRO"
sd="$NEXIUM_DATA_ROOT/sdmc/switch/foj/gpu"
actor="$sd/actor.fojrm"
receipt="$sd/foj-native-topology-reject.txt"
for name in actor.fojrm actor.fojmat material0.dds material1.dds \
            material2.dds foj_actor.vert.dksh foj_triangle.frag.dksh; do
  test -s "$sd/$name" && test ! -L "$sd/$name"
done
for name in foj-native-topology-reject.txt foj-native-sort-pass.txt \
            foj-native-alpha-pass.txt foj-native-rear-alpha-reject.txt; do
  if [[ -e "$sd/$name" || -L "$sd/$name" ]]; then
    echo "Stage275 refuses pre-existing native markers" >&2
    exit 2
  fi
done
if compgen -G "$sd/foj-boot-*.txt" >/dev/null; then
  echo "Stage275 refuses pre-existing GPU boot journal" >&2
  exit 2
fi
mkdir -p "$FOJ_EVIDENCE_DIR"
manifest="$FOJ_EVIDENCE_DIR/generated-input.json"
test -s "$manifest" && test ! -L "$manifest"
# Independently validate the actual actor bytes against the public unsafe
# generator before and after native execution; no PS3 assets are involved.
validate_actor() {
  local phase="$1"
  python3 - "$actor" "$manifest" "$FOJ_TOPOLOGY_CASE" "$FOJ_EVIDENCE_DIR/actor-$phase.sha256" <<'PY'
import hashlib
import json
from pathlib import Path
import sys
from tools.foj_stage271_generated_negative_sd import rejected_actor
from tools.foj_stage273_dynamic_gpu_sd import generated_actor
actor,manifest,case,out=Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3],Path(sys.argv[4])
if actor.is_symlink() or manifest.is_symlink() or out.exists() or out.is_symlink():
    raise SystemExit("Stage275 unsafe geometry input/witness path")
data=actor.read_bytes()
expected=rejected_actor(case)
meta=json.loads(manifest.read_text(encoding="utf-8"))
if (data!=expected or meta.get("topology_case")!=case or
    meta.get("schema")!="foj.stage275.native_unsafe_dynamic_topology.v1" or
    meta.get("actor_sha256")!=hashlib.sha256(expected).hexdigest() or
    meta.get("safe_original_actor_sha256")!=hashlib.sha256(
        generated_actor("original")).hexdigest()):
    raise SystemExit("Stage275 unsafe actor payload or digest mismatch")
out.write_text(hashlib.sha256(data).hexdigest()+"\n",encoding="ascii")
PY
}
validate_actor before
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
  echo "Stage275 native topology rejection witness absent" >&2
  tail -n 60 "$FOJ_EVIDENCE_DIR/guest.log" >&2 || true
  exit 1
fi
python3 - "$receipt" <<'PY'
from pathlib import Path
import sys
expected=b"FOJ_NATIVE_TOPOLOGY_REJECT_V1 pre_gpu=1 unsafe=1\n"
if Path(sys.argv[1]).read_bytes()!=expected:
    raise SystemExit("Stage275 native unsafe-topology witness invalid")
PY
for name in foj-native-sort-pass.txt foj-native-alpha-pass.txt \
            foj-native-rear-alpha-reject.txt; do
  if [[ -e "$sd/$name" || -L "$sd/$name" ]]; then
    echo "Stage275 unsafe actor unexpectedly reached incompatible witness" >&2
    exit 1
  fi
done
if compgen -G "$sd/foj-boot-*.txt" >/dev/null; then
  echo "Stage275 unsafe actor reached GPU boot journal" >&2
  exit 1
fi
validate_actor after
cp -- "$receipt" "$FOJ_EVIDENCE_DIR/native-topology-reject.txt"
echo "Stage275 actual NeXium guest rejected $FOJ_TOPOLOGY_CASE before GPU boot"
