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
if make -f gpu/triangle.mk -n build/foj-deko3d-triangle-research.elf | grep -F -- "$build_command" >/dev/null; then
    echo "FAIL: current triangle ELF should not rebuild" >&2
    exit 1
fi
for header in gpu/dksh_module.h gpu/shader_layout.h gpu/triangle.mk gpu/clear.mk; do
    touch -t 202401010000 "$header"
    if ! make -f gpu/triangle.mk -n build/foj-deko3d-triangle-research.elf | grep -F -- "$build_command" >/dev/null; then
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
if make -f gpu/triangle.mk -n "$nacp" | grep -F -- '--create' >/dev/null; then
    echo "FAIL: current triangle NACP should not rebuild" >&2
    exit 1
fi
for config in gpu/triangle.mk gpu/clear.mk; do
    touch -t 202401010000 "$config"
    if ! make -f gpu/triangle.mk -n "$nacp" | grep -F -- '--create' >/dev/null; then
        echo "FAIL: editing $config did not trigger NACP metadata regeneration" >&2
        exit 1
    fi
    touch -t 202001010000 "$config"
done
# Shader header updates change the ELF, not title/version metadata.
# Check this independently before the NRO packaging fixture below.
for header in gpu/dksh_module.h gpu/shader_layout.h; do
    touch -t 202401010000 "$header"
    plan="$(make -f gpu/triangle.mk -n "$nacp")"
    if [[ "$plan" == *'--create'* ]]; then
        echo "FAIL: changing $header unnecessarily regenerates triangle NACP" >&2
        exit 1
    fi
    plan="$(make -f gpu/triangle.mk -n "$target")"
    if [[ "$plan" != *"$build_command"* ]]; then
        echo "FAIL: changing $header did not rebuild triangle ELF" >&2
        exit 1
    fi
    touch -t 202001010000 "$header"
done
# The packaged NRO depends on both ELF and NACP. Verify changing only
# metadata triggers elf2nro without needing to rerun the ELF compiler.
nro=build/foj-deko3d-triangle-research.nro
touch "$nro"
touch -t 202301010000 "$nro"
nro_command='--nacp=build/foj-deko3d-triangle-research.nacp'
if make -f gpu/triangle.mk -n "$nro" | grep -F -- "$nro_command" >/dev/null; then
    echo "FAIL: unchanged triangle NRO should not be repackaged" >&2
    exit 1
fi
touch -t 202401010000 "$nacp"
if ! make -f gpu/triangle.mk -n "$nro" | grep -F -- "$nro_command" >/dev/null; then
    echo "FAIL: changed NACP does not repackage triangle NRO" >&2
    exit 1
fi
touch -t 202201010000 "$nacp"
touch -t 202401010000 "$target"
if ! make -f gpu/triangle.mk -n "$nro" | grep -F -- "$nro_command" >/dev/null; then
    echo "FAIL: changed ELF does not repackage triangle NRO" >&2
    exit 1
fi
# A shader header edit propagates through ELF into NRO packaging,
# without regenerating NACP. Check the complete resulting target.
touch -t 202201010000 "$target" "$nacp"
touch -t 202301010000 "$nro"
for header in gpu/dksh_module.h gpu/shader_layout.h; do
    touch -t 202401010000 "$header"
    plan="$(make -f gpu/triangle.mk -n "$nro")"
    if [[ "$plan" != *"$build_command"* ||
          "$plan" != *"$nro_command"* ||
          "$plan" == *'--create'* ]]; then
        echo "FAIL: changing $header must rebuild ELF/NRO without NACP" >&2
        exit 1
    fi
    touch -t 202001010000 "$header"
done
# A packaging-only version/title change must regenerate metadata and NRO.
# Since both common and triangle Makefiles also feed the ELF target, a
# configuration change can legitimately rebuild ELF as well; assert that
# both packaging steps remain scheduled, without assuming ELF is unchanged.
touch -t 202201010000 "$target" "$nacp"
touch -t 202301010000 "$nro"
for config in gpu/triangle.mk gpu/clear.mk; do
    touch -t 202401010000 "$config"
    plan="$(make -f gpu/triangle.mk -n "$nro")"
    if [[ "$plan" != *'--create'* || "$plan" != *"$nro_command"* ]]; then
        echo "FAIL: editing $config did not regenerate NACP and repackage NRO" >&2
        exit 1
    fi
    touch -t 202001010000 "$config"
done
# Verify the separate shader-free clear-smoke variant as well.
clear_elf=build/foj-deko3d-clear-smoke.elf
clear_nacp=build/foj-deko3d-clear-smoke.nacp
clear_nro=build/foj-deko3d-clear-smoke.nro
touch "$clear_elf" "$clear_nacp" "$clear_nro"
touch -t 202201010000 "$clear_elf" "$clear_nacp"
touch -t 202301010000 "$clear_nro"
clear_recipe='--nacp=build/foj-deko3d-clear-smoke.nacp'
plan="$(make -f gpu/clear.mk -n "$clear_nro")"
if [[ "$plan" == *'--create'* || "$plan" == *"$clear_recipe"* ]]; then
    echo "FAIL: unchanged clear-smoke NRO should not rebuild" >&2
    exit 1
fi
touch -t 202401010000 gpu/clear.mk
plan="$(make -f gpu/clear.mk -n "$clear_nro")"
if [[ "$plan" != *'--create'* || "$plan" != *"$clear_recipe"* ]]; then
    echo "FAIL: shared Makefile change did not rebuild clear-smoke metadata and NRO" >&2
    exit 1
fi
touch -t 202001010000 gpu/clear.mk
# Editing only a source file must rebuild the ELF and packaged NRO but
# must not regenerate NACP metadata that depends only on build settings.
touch -t 202401010000 gpu/smoke_plan.c
plan="$(make -f gpu/clear.mk -n "$clear_nro")"
if [[ "$plan" != *'-o build/foj-deko3d-clear-smoke.elf'* ||
      "$plan" != *"$clear_recipe"* ||
      "$plan" == *'--create'* ]]; then
    echo "FAIL: clear-smoke source edit must rebuild ELF/NRO, not NACP" >&2
    exit 1
fi
touch -t 202001010000 gpu/smoke_plan.c
# A common C header edit must invalidate the clear-smoke binary, but
# must not change the user-facing NACP metadata.
touch -t 202401010000 gpu/smoke_plan.h
plan="$(make -f gpu/clear.mk -n "$clear_nro")"
if [[ "$plan" != *'-o build/foj-deko3d-clear-smoke.elf'* ||
      "$plan" != *"$clear_recipe"* ||
      "$plan" == *'--create'* ]]; then
    echo "FAIL: clear-smoke header edit must rebuild ELF/NRO without NACP" >&2
    exit 1
fi
touch -t 202001010000 gpu/smoke_plan.h
# All host binaries built by the strict NDEBUG / sanitizer matrix must
# be included in 'clean', otherwise stale executables can survive.
clean_plan="$(make -f gpu/clear.mk -n clean)"
for binary in \
    build/foj-deko3d-lifecycle-host \
    build/foj-deko3d-lifecycle-ndebug \
    build/foj-deko3d-lifecycle-asan \
    build/foj-dksh-layout-integration-ndebug \
    build/foj-dksh-intake-ndebug \
    build/foj-deko3d-shader-layout-ndebug \
    build/foj-gpu-smoke-plan-ndebug \
    build/foj-deko3d-contract-ndebug; do
    if [[ "$clean_plan" != *"$binary"* ]]; then
        echo "FAIL: GPU clean does not remove $binary" >&2
        exit 1
    fi
done
# The two native GPU variants must clean their respective NRO outputs
# without deleting the other variant's build products.
triangle_clean="$(make -f gpu/triangle.mk -n clean)"
for extension in elf nacp nro; do
    if [[ "$triangle_clean" != *"build/foj-deko3d-triangle-research.$extension"* ]]; then
        echo "FAIL: triangle clean leaves stale .$extension output" >&2
        exit 1
    fi
    if [[ "$clean_plan" != *"build/foj-deko3d-clear-smoke.$extension"* ]]; then
        echo "FAIL: clear clean leaves stale .$extension output" >&2
        exit 1
    fi
done
# Materialize representative host outputs: a dry-run listing alone cannot
# prove clean actually removes the NDEBUG and sanitizer executables.
for binary in \
    build/foj-deko3d-lifecycle-host \
    build/foj-deko3d-lifecycle-ndebug \
    build/foj-deko3d-lifecycle-asan \
    build/foj-dksh-layout-integration-ndebug \
    build/foj-dksh-intake-ndebug \
    build/foj-deko3d-shader-layout-ndebug \
    build/foj-gpu-smoke-plan-ndebug \
    build/foj-deko3d-contract-ndebug; do
    touch "$binary"
done
# Guard against overly broad clean rules (for example rm -f build/*).
# Unrelated build assets and a neighboring variant must remain untouched.
sentinel=build/keep-unrelated-gpu-data.bin
printf '%s\n' 'KEEP_GPU_SENTINEL' > "$sentinel"
# Execute the real clean recipes in this disposable fixture as well:
# text-matching a dry-run alone cannot prove that outputs are removed.
make -f gpu/clear.mk clean >/dev/null
for extension in elf nacp nro; do
    if [[ -e "build/foj-deko3d-clear-smoke.$extension" ]]; then
        echo "FAIL: clear clean retained .$extension" >&2
        exit 1
    fi
    if [[ ! -f "build/foj-deko3d-triangle-research.$extension" ]]; then
        echo "FAIL: clear clean deleted triangle .$extension" >&2
        exit 1
    fi
done
for binary in \
    build/foj-deko3d-lifecycle-host \
    build/foj-deko3d-lifecycle-ndebug \
    build/foj-deko3d-lifecycle-asan \
    build/foj-dksh-layout-integration-ndebug \
    build/foj-dksh-intake-ndebug \
    build/foj-deko3d-shader-layout-ndebug \
    build/foj-gpu-smoke-plan-ndebug \
    build/foj-deko3d-contract-ndebug; do
    if [[ -e "$binary" ]]; then
        echo "FAIL: clear clean retained host binary $binary" >&2
        exit 1
    fi
done
if [[ "$(cat "$sentinel")" != 'KEEP_GPU_SENTINEL' ]]; then
    echo "FAIL: clear clean removed or corrupted unrelated build asset" >&2
    exit 1
fi
make -f gpu/triangle.mk clean >/dev/null
for extension in elf nacp nro; do
    if [[ -e "build/foj-deko3d-triangle-research.$extension" ]]; then
        echo "FAIL: triangle clean retained .$extension" >&2
        exit 1
    fi
done
if [[ "$(cat "$sentinel")" != 'KEEP_GPU_SENTINEL' ]]; then
    echo "FAIL: triangle clean removed or corrupted unrelated build asset" >&2
    exit 1
fi
echo "GPU triangle and clear-smoke ELF, NACP and NRO dependencies: PASS"
