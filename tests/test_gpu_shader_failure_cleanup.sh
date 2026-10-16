#!/usr/bin/env bash
# Verify the actual UAM Makefile deletes rejected shader targets.
set -euo pipefail
cd "$(dirname "$0")/.."
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/gpu/shaders" "$tmp/tools"
cp gpu/Makefile "$tmp/gpu/Makefile"
printf 'synthetic shader source\n' > "$tmp/gpu/shaders/foj_actor.vert"
cat > "$tmp/fake-uam" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
while (($#)); do
    if [[ "$1" == "-o" ]]; then
        printf 'invalid-dksh\n' > "$2"
        exit 0
    fi
    shift
done
exit 2
EOF
chmod +x "$tmp/fake-uam"
cat > "$tmp/tools/validate_dksh.py" <<'EOF'
import sys
raise SystemExit(1)
EOF
touch "$tmp/tools/__init__.py"
cd "$tmp"
target=gpu/build/foj_actor.vert.dksh
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
# Also reject a compiler that writes an output and then fails.
if FAKE_UAM_FAIL=1 PYTHONPATH="$tmp" make --no-print-directory -f gpu/Makefile "$target" UAM="$tmp/fake-uam" >"$tmp/compiler-failure.log" 2>&1; then
    echo "FAIL: simulated UAM failure unexpectedly passed" >&2
    exit 1
fi
if [[ -e "$target" ]]; then
    echo "FAIL: compiler-failed DKSH remains on disk" >&2
    exit 1
fi
grep -q "Deleting file" "$tmp/compiler-failure.log" || {
    echo "FAIL: make did not remove compiler-failed DKSH" >&2
    cat "$tmp/compiler-failure.log" >&2
    exit 1
}
echo "UAM Makefile compiler and validator failure cleanup: PASS"
