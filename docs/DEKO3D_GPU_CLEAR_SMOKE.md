# Native deko3d first-GPU-frame gate (optional NRO)

**Research status: 2026-10-16.** An isolated GPU smoke-test NRO
source and build target have been added to this repository. **Compilation
and execution of this new NRO have not been verified.** GitHub Actions
continues to fail at job startup without step data or build logs, so it
would be inaccurate to call this a successful GPU renderer.

## Exactly what was implemented

[deko3d_clear_main.c](../gpu/deko3d_clear_main.c) uses the upstream
[deko3d C API](https://github.com/devkitPro/deko3d/blob/master/Primer.md)
to:

1. Create a device with **Z clip depth 0..1**, upper-left image origin
   and positive-up screen Y — matching our current vertex staging.
2. Create a graphics queue and a double-buffered **1280×720 RGBA8**
   swapchain backed by deko3d image memory blocks.
3. Allocate a GPU-visible command-memory block and command buffer.
4. Pre-record **four immutable GPU clear command lists**: two RGBA8
   framebuffer slots × two generated color palettes. Each list explicitly
   binds a render target and sets a full-screen scissor region.
5. Acquire one presentation image, submit its matching pre-recorded list,
   then present it. Colors alternate every 120 frames. The program waits
   for the graphics queue to become idle before releasing any resources.
6. Handle Plus to exit and release allocated GPU objects.

This program uses **no shaders**, textures, original FoJ resources,
triangle vertices, or gameplay systems. It aims to confirm the first
native **GPU-cleared/presented frame** in isolation. The existing nine
research NROs still use their prior paths and are not modified by this
new target.

The command-list and swapchain sequence was revised against upstream
[switchbrew's deko_basic example](https://github.com/switchbrew/switch-examples/blob/master/graphics/deko3d/deko_basic/source/main.c)
and [Example01_SimpleSetup](https://github.com/switchbrew/switch-examples/blob/master/graphics/deko3d/deko_examples/source/Example01_SimpleSetup.cpp).
Persistent lists remain valid until shutdown. No per-frame list-memory reset
or GPU idle wait is required; shutdown waits for queue idle before freeing
buffers. This is still an unverified GPU application, **not** a benchmark
or HD remake.

## Separate build command

With a correctly installed devkitPro `switch-dev` toolchain and
`DEVKITPRO=/opt/devkitpro`:

```sh
make -f gpu/clear.mk host-check  # C11 host test, no devkitPro necessary
make -f gpu/clear.mk preflight   # requires devkitPro
make -f gpu/clear.mk verify      # optional native NRO build
```

Expected output if compilation succeeds:

```text
build/foj-deko3d-clear-smoke.nro
```

This intentionally uses the **debug validation build** of deko3d,
`libdeko3dd.a`. After validating startup and rendering, release
library `libdeko3d.a` may be selected:

```sh
make -f gpu/clear.mk clean
make -f gpu/clear.mk verify GPU_LIB=deko3d
```

The upstream
[deko3d Makefile](https://github.com/devkitPro/deko3d/blob/master/Makefile)
installs headers and libraries in the **libnx** prefix, so the
independent build checks `/opt/devkitpro/libnx/include/deko3d.h`
and `/opt/devkitpro/libnx/lib/libdeko3dd.a`.

## Locally verified portable GPU smoke math

`gpu/smoke_plan.c` provides the exact allocation rounding and color-mode
selection used by the GPU smoke program. It rejects null outputs,
invalid/non-power-of-two image alignment, overflowing allocation sizes
and unsupported palette indices **without modifying caller outputs**.

`tests/test_gpu_smoke_plan.c` checks 1280×720 RGBA8 allocation sizes,
alignment escalation, overflow failure, palette values, and frames
119/120/239/240 where the clear color changes.

**Executed locally on 2026-10-16:** strict host C11 compile and run,
UBSan, and combined ASan/UBSan all passed. This confirms only CPU-side
arithmetic/decision logic, not the GPU driver, swapchain or video output.

## GitHub Actions

The separate
[Optional FoJ deko3d GPU smoke](../.github/workflows/gpu-clear-smoke.yml)
workflow runs on manual dispatch and changes to its own source/build
files. It checks SDK files, calls `make -f gpu/clear.mk verify`, and
optionally tries UAM shader compilation if `uam` is installed.
It does not alter the legacy CPU-NRO workflow or embed original PS3 data.

**First attempted run:**
[GitHub Actions #38948667056](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/38948667056).
Result: failed with **zero executed step records**, identical to
failures in unrelated Python/C workflows. There are no compiler
diagnostics from that run. This is *not proof of a source-level error*.
See [issue #15](https://github.com/stanmasked/vandal-hearts-foj-switch/issues/15).

## Actual hardware acceptance checklist

- [ ] Obtain a full devkitA64 + deko3d debug-build log, including
      cross-compiler and linker exit status.
- [ ] Produce and structurally validate the optional GPU NRO.
- [ ] Boot on a physical homebrew-enabled Switch and see a smooth change
      in the background color.
- [ ] Press Plus to exit; verify safe cleanup, no GPU error or crash.
- [ ] Repeat in handheld and docked mode; note console firmware and
      toolchain versions.
- [ ] Add shader/module loading and render **generated GPU triangles**
      before testing original Daldren geometry and DDS materials.
- [ ] Keep commercial BMODEL/BANIM/DDS assets in private user-local files.
- [ ] Reconcile NDC-Z, texture origin, two atlas bindings and scene
      depth against the verified CPU rasterizer.

**Only a successful native GPU build plus an observed console frame
can establish the first completed GPU-rendering milestone.**
