#!/usr/bin/env bash
# SDK-free native GPU Makefile dependency regression.
set -euo pipefail
cd "$(dirname "$0")/.."
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/gpu" "$tmp/core" "$tmp/build"
cp gpu/clear.mk gpu/triangle.mk "$tmp/gpu/"
# Copying Makefiles gives them the current time; normalize timestamps so
# the control case truly has an ELF newer than every dependency.
touch -t 202001010000 "$tmp/gpu/clear.mk" "$tmp/gpu/triangle.mk"
for path in gpu/deko3d_clear_main.c gpu/smoke_plan.c gpu/dksh_module.c \
            gpu/shader_layout.c gpu/dksh_module.h gpu/shader_layout.h \
            gpu/smoke_plan.h gpu/deko3d_api_contract.h core/gpu_vertex_stream.h; do
    touch "$tmp/$path"
    touch -t 202001010000 "$tmp/$path"
done
target="$tmp/build/foj-deko3d-triangle-research.elf"
touch "$target"
touch -t 202201010000 "$target"
cd "$tmp"
# The preflight target is order-only. A current ELF must not be rebuilt.
build_command='-o build/foj-deko3d-triangle-research.elf'
if make -f gpu/triangle.mk -n build/foj-deko3d-triangle-research.elf | grep -Fq -- "$build_command"; then
    echo "FAIL: current triangle ELF should not rebuild" >&2
    exit 1
fi
for header in gpu/dksh_module.h gpu/shader_layout.h gpu/triangle.mk gpu/clear.mk; do
    touch -t 202401010000 "$header"
    if ! make -f gpu/triangle.mk -n build/foj-deko3d-triangle-research.elf | grep -Fq -- "$build_command"; then
        echo "FAIL: editing $header did not trigger the triangle ELF compiler" >&2
        exit 1
    fi
    touch -t 202001010000 "$header"
done
# NACP metadata must be regenerated when title/version build configuration
# changes. Use make -n: no actual devkitPro tool is needed here.
nacp=build/foj-deko3d-triangle-research.nacp
touch "$nacp"
touch -t 202201010000 "$nacp"
if make -f gpu/triangle.mk -n "$nacp" | grep -Fq -- '--create'; then
    echo "FAIL: current triangle NACP should not rebuild" >&2
    exit 1
fi
for config in gpu/triangle.mk gpu/clear.mk; do
    touch -t 202401010000 "$config"
    if ! make -f gpu/triangle.mk -n "$nacp" | grep -Fq -- '--create'; then
        echo "FAIL: editing $config did not trigger NACP metadata regeneration" >&2
        exit 1
    fi
    touch -t 202001010000 "$config"
done
echo "GPU triangle ELF and NACP configuration dependencies: PASS"
