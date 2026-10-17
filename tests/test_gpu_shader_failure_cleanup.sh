#!/usr/bin/env bash
# Verify the actual UAM Makefile deletes rejected shader targets.
set -euo pipefail
cd "$(dirname "$0")/.."
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/gpu/shaders" "$tmp/tools"
cp gpu/Makefile "$tmp/gpu/Makefile"
for source in foj_actor.vert foj_actor.frag foj_triangle.frag; do
    printf 'synthetic shader source\n' > "$tmp/gpu/shaders/$source"
done
cat > "$tmp/fake-uam" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
while (($#)); do
    if [[ "$1" == "-o" ]]; then
        printf 'called\n' >> compiler-invocations.log
        printf 'invalid-dksh\n' > "$2"
        if [[ "${FAKE_UAM_FAIL:-0}" == "1" ]]; then
            exit 17
        fi
        exit 0
    fi
    shift
done
exit 2
EOF
chmod +x "$tmp/fake-uam"
cat > "$tmp/tools/validate_dksh.py" <<'EOF'
from pathlib import Path
Path('validator-invocations.log').open('a').write('called\n')
import os
raise SystemExit(0 if os.getenv('FAKE_VALIDATE_PASS') == '1' else 1)
EOF
touch "$tmp/tools/__init__.py"
cd "$tmp"
for shader in foj_actor.vert foj_actor.frag foj_triangle.frag; do
    rm -f validator-invocations.log
    target="gpu/build/$shader.dksh"
    if PYTHONPATH="$tmp" make --no-print-directory -f gpu/Makefile "$target" UAM="$tmp/fake-uam" >"$tmp/build.log" 2>&1; then
        echo "FAIL: malformed DKSH unexpectedly passed validation" >&2
        exit 1
    fi
    if [[ -e "$target" ]]; then
        echo "FAIL: validator-rejected DKSH remains on disk" >&2
        exit 1
    fi
    grep -q "Deleting file" "$tmp/build.log" || {
        echo "FAIL: make did not report failed target cleanup" >&2
        cat "$tmp/build.log" >&2
        exit 1
    }
    if [[ ! -f validator-invocations.log ]] || [[ $(wc -l < validator-invocations.log) -ne 1 ]]; then
        echo "FAIL: validator was not invoked exactly once" >&2
        exit 1
    fi
    # Also reject a compiler that writes an output and then fails.
    if FAKE_UAM_FAIL=1 PYTHONPATH="$tmp" make --no-print-directory -f gpu/Makefile "$target" UAM="$tmp/fake-uam" >"$tmp/compiler-failure.log" 2>&1; then
        echo "FAIL: simulated UAM failure unexpectedly passed" >&2
        exit 1
    fi
    if [[ -e "$target" ]]; then
        echo "FAIL: compiler-failed DKSH remains on disk" >&2
        exit 1
    fi
    grep -q "Error 17" "$tmp/compiler-failure.log" || {
        echo "FAIL: fake UAM did not exit with its intended compiler error" >&2
        cat "$tmp/compiler-failure.log" >&2
        exit 1
    }
    grep -q "Deleting file" "$tmp/compiler-failure.log" || {
        echo "FAIL: make did not remove compiler-failed DKSH" >&2
        cat "$tmp/compiler-failure.log" >&2
        exit 1
    }
    if [[ $(wc -l < validator-invocations.log) -ne 1 ]]; then
        echo "FAIL: validator incorrectly ran after UAM compiler failure" >&2
        exit 1
    fi
done
# Successful compile and validation must preserve a usable output.
for shader in foj_actor.vert foj_actor.frag foj_triangle.frag; do
    rm -f validator-invocations.log compiler-invocations.log
    target="gpu/build/$shader.dksh"
    FAKE_VALIDATE_PASS=1 PYTHONPATH="$tmp" make --no-print-directory -f gpu/Makefile "$target" UAM="$tmp/fake-uam" >"$tmp/success.log" 2>&1 || {
        cat "$tmp/success.log" >&2
        echo "FAIL: successful synthetic shader build was rejected" >&2
        exit 1
    }
    [[ -s "$target" ]] || { echo "FAIL: successful DKSH was deleted" >&2; exit 1; }
    [[ $(wc -l < validator-invocations.log) -eq 1 ]] || {
        echo "FAIL: validator did not accept shader exactly once" >&2
        exit 1
    }
    [[ $(wc -l < compiler-invocations.log) -eq 1 ]] || { echo "FAIL: UAM invocation count after first build" >&2; exit 1; }
    FAKE_VALIDATE_PASS=1 PYTHONPATH="$tmp" make --no-print-directory -f gpu/Makefile "$target" UAM="$tmp/fake-uam" >"$tmp/incremental.log" 2>&1 || exit 1
    [[ $(wc -l < validator-invocations.log) -eq 1 ]] || {
        echo "FAIL: already-built shader unexpectedly revalidated" >&2
        exit 1
    }
    [[ -s "$target" ]] || exit 1
    [[ $(wc -l < compiler-invocations.log) -eq 1 ]] || { echo "FAIL: unchanged shader was recompiled" >&2; exit 1; }
    # Advancing the source timestamp must rebuild the previously valid DKSH.
    touch -t 203001010000 "gpu/shaders/$shader"
    FAKE_VALIDATE_PASS=1 PYTHONPATH="$tmp" make --no-print-directory -f gpu/Makefile "$target" UAM="$tmp/fake-uam" >"$tmp/rebuild.log" 2>&1 || {
        cat "$tmp/rebuild.log" >&2
        exit 1
    }
    [[ $(wc -l < compiler-invocations.log) -eq 2 ]] || { echo "FAIL: edited shader did not recompile" >&2; exit 1; }
    [[ $(wc -l < validator-invocations.log) -eq 2 ]] || { echo "FAIL: edited shader was not revalidated" >&2; exit 1; }
    [[ -s "$target" ]] || { echo "FAIL: rebuilt DKSH is missing" >&2; exit 1; }
done
echo "UAM Makefile all three shader targets: compiler and validator cleanup, reuse and source-triggered rebuild PASS"
