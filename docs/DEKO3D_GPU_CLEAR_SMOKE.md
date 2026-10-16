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
6. Allocate a 4 KiB GPU-addressable vertex block and write **72 bytes**
   (three generated vertices × six float32 values). Confirm both memory
   accessors succeed, without yet binding or drawing these vertices.
7. Handle Plus to exit and release allocated GPU objects.

This program uses **no shaders**, textures, original FoJ resources,
GPU draw calls, or gameplay systems. It **uploads three generated triangle
vertices into an allocated GPU-addressable buffer**, but does not render
the triangle. It aims to confirm the first
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

## GPU vertex upload milestone — no shaders or draw calls yet

The optional NRO now uses the same
[`FojGpuVertex` XYZW/UV record](../core/gpu_vertex_stream.h) (24 bytes)
as the original model GPU staging path. It creates an **invented triangle**
with three vertices, allocates a CPU-visible/GPU-addressable memory block,
queries `dkMemBlockGetCpuAddr` and `dkMemBlockGetGpuAddr`, and copies
the exact **72-byte vertex payload** into the CPU address.

The buffer is deliberately **not yet bound to a vertex attribute state**
or passed to `dkCmdBufDraw`. The active GPU command lists still *only
clear a framebuffer to a generated color*.

The upstream deko3d API identifies an invalid GPU address with
`DK_GPU_ADDR_INVALID == UINT64_MAX`. The prototype and mock now
check this sentinel (rather than incorrectly using zero), and the
ABI contract asserts the sentinel and 64-bit address representation.

Three more failure paths were added to the host mock:
failure to allocate vertex memory, failure to obtain its CPU address,
and failure to obtain its GPU address. The normal host scenario
byte-compares the entire **72-byte upload** against the generated
vertex array before the first simulated command submission.

**Host test coverage now comprises 14 scenarios** (normal operation,
nine original resource/acquisition failures, Plus exit, and these
three new failures). These new integration paths are committed for
strict C11/ASan/UBSan CI and `host-check`; a full run against the
newest code has **not** been confirmed on GitHub while runner jobs fail
before execution.

The allocation math itself was independently compiled and executed
in the local sandbox under C11 and combined ASan/UBSan:

| Vertex count | Payload bytes | 4 KiB-aligned allocation |
| ---: | ---: | ---: |
| 3 (invented triangle) | 72 | 4,096 |
| 9,066 (original Daldren model capacity) | 217,584 | 221,184 |
| 20,000 (current maximum) | 480,000 | 483,328 |

**The Daldren row is an allocation-size calculation**, not proof that
Daldren's commercial vertex data were transferred to the Switch.

## Host-executed deko3d lifecycle test (new gate)

A **stateful fake of the deko3d and libnx C API** now compiles and runs
the **actual** `gpu/deko3d_clear_main.c` entrypoint on a normal desktop
compiler. The test only substitutes driver/kernel calls via small headers
under `tests/mock_switch_sdk/`; the original optional Switch source is
included unmodified in `tests/test_deko3d_clear_host.c`.

Run without devkitPro or a console:

```sh
make -f gpu/clear.mk host-check
make -f gpu/clear.mk host-mock-sanitized
```

The mock records every allocation, framebuffer binding, scissor region,
command list, acquired slot, submission, presentation and destruction.
It asserts command lists are built for **both swapchain images** and
both generated clear-color modes. Host coverage:

| Test | Expected result |
| --- | --- |
| Normal mock run | **242** complete acquired/submitted/presented frames |
| Buffer slots | Both visited **121** times |
| Color palette A / B | Selected **122 / 120** times |
| Recorded GPU lists | **Four** (2 image slots × 2 color modes) |
| Deliberate setup/acquire faults | **Nine** original recovery paths |
| New vertex GPU allocation / CPU address / GPU address faults | **Three** additional paths |
| Synthetic vertex upload | Byte-for-byte verification of 72-byte triangle |
| User presses Plus after two frames | Normal exit and complete cleanup |
| Expected live allocations after exit | **Zero** across all fourteen scenarios (latest host run pending) |
| Strict C11 host compile | **Passed locally** |
| ASan + UBSan host compile/run | **Passed locally** |

The nine simulated faults cover device creation, graphics queue
creation, each of two image-memory allocations, swapchain creation,
command memory, command-buffer creation, command-list finalization and
image acquisition. A separate scenario simulates pressing Plus after two frames. Three
additional cases validate vertex upload failures and cleanup. These
new cases are committed but remain unverified against the latest full
host executable until a successful test run.

The tests exercise resource lifetime and the C call flow without
emulating actual deko3d command execution. The mock implements only
the public signatures needed by this NRO, matching the upstream
`deko3d.h` at the time of implementation, and **is not a substitute for
compiling against the real SDK**. No hardware/display/color correctness,
GPU memory residency or native API version compatibility is established.

The repository CI calls `host-check` and `host-mock-sanitized`
when runner jobs execute again. The **earlier 11-case** version of these
commands was run successfully; the new 14-case version has yet to run
end-to-end on the official runner.
The GPU workflow also executes `host-check` before attempting its
independent ARM64 build.

## SDK API verification and deterministic toolchain preflight

A cross-check against upstream
[devkitPro/deko3d.h](https://github.com/devkitPro/deko3d/blob/master/include/deko3d.h)
identified two incorrect values in the former **host-only mock**:

| Enum | Previous mock | Verified real deko3d |
| --- | ---: | ---: |
| `DkImageFormat_RGBA8_Unorm` | 37 | **28** |
| `DkImageFlags_UsageRender` | 64 | **256** |

The real NRO source used the *symbolic constants* and was unaffected
by these hardcoded mock values. The mock is now corrected and verifies
that framebuffer images request **both render and present usage**.

[The deko3d ABI contract](../gpu/deko3d_api_contract.h)
contains nine C11 compile-time assertions for render format, flags,
color mask and image memory alignment. It is included by the **real
deko3d source** and, separately, by the host-only test. When the
actual devkitPro cross-compiler works, it will check the real SDK
definitions rather than trusting the fake headers.

The contract was locally compiled using a strict C11 test matching the
verified upstream numerical values. A deliberately wrong RGBA8 value
was rejected at compilation. This is source-level ABI checking, **not**
evidence that the full GPU NRO has linked or run on hardware.

A new standard-library-only
[toolchain checker](../tools/check_switch_gpu_toolchain.py) reports,
in JSON, required/available toolchain paths: devkitA64 GCC,
libnx/deko3d headers and archives, `elf2nro`, `nacptool`, and
optional UAM. It supports `DEVKITPRO`, `DEVKITA64` overrides and
`--require-shaders`. Tests use synthetic SDK directories, and the
independent optional GPU workflow calls the checker before compilation.

Usage:

```sh
python3 -m tools.check_switch_gpu_toolchain
python3 -m tools.check_switch_gpu_toolchain --require-shaders
```

For the current local runtime, devkitA64 GCC, deko3d headers/libraries
and `elf2nro` are absent. Therefore **a real ARM64 NRO build remains
blocked here**, regardless of the success of host-only tests.

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
