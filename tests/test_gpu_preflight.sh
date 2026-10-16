#!/usr/bin/env bash
# SDK-free tests for GPU native build toolchain preflight.
set -euo pipefail
cd "$(dirname "$0")/.."
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
sdk="$tmp/devkitpro"
mkdir -p "$sdk/devkitA64/bin" "$sdk/tools/bin" "$sdk/libnx/include" "$sdk/libnx/lib"
check_failure() {
    local expected="$1"
    local output
    if output="$(make --no-print-directory -f gpu/clear.mk preflight DEVKITPRO="$sdk" 2>&1)"; then
        echo "FAIL: expected preflight to reject missing $expected" >&2
        exit 1
    fi
    if [[ "$output" != *"$expected"* ]]; then
        printf 'FAIL: expected missing %s, received:\n%s\n' "$expected" "$output" >&2
        exit 1
    fi
}
check_failure "devkitA64 cross-compiler"
touch "$sdk/devkitA64/bin/aarch64-none-elf-gcc"
chmod +x "$sdk/devkitA64/bin/aarch64-none-elf-gcc"
check_failure "elf2nro"
touch "$sdk/tools/bin/elf2nro"
chmod +x "$sdk/tools/bin/elf2nro"
check_failure "nacptool"
touch "$sdk/tools/bin/nacptool"
chmod +x "$sdk/tools/bin/nacptool"
# A path that exists but is not executable must also fail preflight.
chmod -x "$sdk/devkitA64/bin/aarch64-none-elf-gcc"
check_failure "devkitA64 cross-compiler"
chmod +x "$sdk/devkitA64/bin/aarch64-none-elf-gcc"
chmod -x "$sdk/tools/bin/elf2nro"
check_failure "elf2nro"
chmod +x "$sdk/tools/bin/elf2nro"
chmod -x "$sdk/tools/bin/nacptool"
check_failure "nacptool"
chmod +x "$sdk/tools/bin/nacptool"
check_failure "switch.specs"
touch "$sdk/libnx/switch.specs"
check_failure "deko3d.h"
touch "$sdk/libnx/include/deko3d.h"
check_failure "libdeko3dd.a"
touch "$sdk/libnx/lib/libdeko3dd.a"
make --no-print-directory -f gpu/clear.mk preflight DEVKITPRO="$sdk"
echo "GPU SDK preflight diagnostics and complete fixture: PASS"
