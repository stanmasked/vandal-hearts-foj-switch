# First shader-backed deko3d triangle: experimental Switch NRO

**Status: 2026-10-16 — source implementation only.** The new optional
program has shader module loading, GPU-resident generated vertices,
vertex attribute binding and an actual **`dkCmdBufDraw`** call in its
source. The native NRO and UAM shaders **have not yet compiled successfully
in this environment**, nor has a physical Nintendo Switch displayed a
GPU triangle. Current GitHub Actions jobs fail at startup with no steps.

This is entirely clean-room **synthetic GPU research**. It contains
no commercial FoJ BMODEL/BANIM/DDS assets or original game data. Nine
previous CPU research NRO targets remain unchanged.

## What was implemented

The existing shader-free
[`gpu/deko3d_clear_main.c`](../gpu/deko3d_clear_main.c) compiles
a separate **triangle mode** when `FOJ_GPU_DRAW_TRIANGLE=1` is defined.

That mode:

1. Allocates the previous double-buffered 1280×720 RGBA8 deko3d
   render targets, queue and persistent command lists.
2. Allocates **4 KiB** of CPU-visible/GPU-addressable memory and
   uploads **three generated `FojGpuVertex` entries** (XYZW+UV,
   24 bytes each, 72 bytes total).
3. Allocates a **256 KiB executable GPU-code block**, with
   `DkMemBlockFlags_Code`, and loads two user-provided DKSH
   modules into independent **128 KiB slots**, leaving sufficient
   room for the deko3d 1 KiB unusable code-memory tail.
4. Rejects missing, oversized, wrong-stage or structurally corrupt
   DKSH files before calling `dkShaderInitialize`.
5. Binds the vertex and fragment shaders, an orthographic
   full-screen viewport, two float vertex attributes, the one
   24-byte-stride vertex buffer, rasterizer state and color state.
6. Records **`dkCmdBufDraw(cmd,DkPrimitive_Triangles,3,1,0,0)`**
   in the pre-recorded per-frame GPU command list.
7. Presents a generated two-color background and a UV-colored
   triangle **if** actual Switch compilation, shader compilation,
   GPU driver setup and physical display all work.

The vertex shader is
[`foj_actor.vert`](../gpu/shaders/foj_actor.vert), which passes the
test XYZW position and UV coordinates. The new
[`foj_triangle.frag`](../gpu/shaders/foj_triangle.frag) produces
a UV gradient **without sampling a DDS atlas**.

## Separate optional native cross-build

```sh
# First run prerequisite checks, including local SDK paths.
python3 -m tools.check_switch_gpu_toolchain

# Once a real devkitPro/deko3d installation is available:
make -f gpu/clear.mk verify       # old shader-free color clear test
make -f gpu/triangle.mk verify    # NEW opt-in triangle-draw NRO

# Compile test shaders with the separately required UAM compiler.
make -f gpu/Makefile triangle-verify
```

The two separate native NRO targets should be:

- `build/foj-deko3d-clear-smoke.nro` — GPU color clear only;
- `build/foj-deko3d-triangle-research.nro` — GPU triangle draw,
  if external DKSH modules are supplied at runtime.

The existing nine CPU/research NRO builds do not depend on either.

## Prepare generated shaders for your own SD card

The optional triangle NRO searches **exactly**:

```text
/switch/foj/gpu/foj_actor.vert.dksh
/switch/foj/gpu/foj_triangle.frag.dksh
```

After **real** UAM compilation, prepare a new folder:

```sh
mkdir -p local-gpu-sd
python3 -m tools.prepare_gpu_triangle_sd \
  gpu/build/foj_actor.vert.dksh \
  gpu/build/foj_triangle.frag.dksh \
  --output-dir local-gpu-sd
```

This copies only validated UAM shader modules to:

```text
local-gpu-sd/switch/foj/gpu/foj_actor.vert.dksh
local-gpu-sd/switch/foj/gpu/foj_triangle.frag.dksh
```

Copy `local-gpu-sd/switch/` to the user's SD root. Never upload
original game resources; no original assets are required here.

The preparation tool refuses existing output files and verifies
the module's 24-byte header, 64-byte program table entry, 256-byte
section alignment, code references, exact shader type and 126,976
byte per-slot limit.

## Reproducible first-frame pixel reference

An additional **generated-only CPU reference** is available at
[tools/gpu_triangle_reference.py](../tools/gpu_triangle_reference.py).
It uses the exact three hardcoded test positions and UVs in
`gpu/deko3d_clear_main.c` and the `vec4(U,V,0.30,1)` formula from
`foj_triangle.frag`. There are no PS3 assets and no claim that the
Nintendo Switch GPU has produced an image.

Generate five representative pixel probes:

```sh
python3 -m tools.gpu_triangle_reference --frame 0
python3 -m tools.gpu_triangle_reference --frame 120
python3 -m unittest tests.test_gpu_triangle_reference -v
```

Expected theoretical geometry under the chosen viewport mapping:

| Point | Pixel position |
| --- | --- |
| Triangle left/bottom | (256, 558) |
| Triangle right/bottom | (1024, 558) |
| Triangle top | (640, 126) |
| Triangle centroid | approximately (640, 414) |

At the centroid, the expected **synthetic fragment color** is
approximately `RGBA=(0.500, 0.333, 0.300, 1.000)` before framebuffer
quantization. An outside pixel such as (0,0) has background
`RGBA=(0.210, 0.120, 0.230, 1)` at frame 0 and
`RGBA=(0.440, 0.570, 0.430, 1)` at frame 120.

The reference uses a comparison tolerance of **0.02 per color
channel** as an initial hardware acceptance threshold, excluding
triangle-edge pixels where coverage rules may differ. Both winding
and Y-axis behavior still require a real Switch screenshot.

The four [generated-data Python unit tests](../tests/test_gpu_triangle_reference.py)
**passed locally**. This constitutes geometry and shader-formula
verification only; no native DKSH/GPU frame is demonstrated.

### Host shader-mode source syntax checks

`make -f gpu/clear.mk host-triangle-check` now checks the *actual*
shader-backed C source with strict C11 using a focused host-only
deko3d declaration mock. The source uses explicitly named vertex
attribute fields and compile-time checks of the 24-byte
`FojGpuVertex` stride and byte offsets 0/16.
An independent local strict-C11 compilation of the attribute and
bitfield layout succeeded. The complete source-only syntax target
is wired into CI but **has not been confirmed executing on GitHub**.

## Verification and limitations

- **Verified locally:** standalone
  [C11 DKSH loader tests](../tests/test_dksh_module.c), including
  generated vertex/fragment modules, invalid file lengths, stage
  mismatch, truncated reads and bad GPU code offsets. Strict
  C11 and combined AddressSanitizer/UndefinedBehaviorSanitizer
  versions passed.
- **Added but GitHub execution pending:**
  [Python DKSH format tests](../tests/test_validate_dksh.py) and
  [SD packaging tests](../tests/test_prepare_gpu_triangle_sd.py).
  The repository workflow now includes the DKSH C regression.
- **Not verified:** actual UAM DKSH compilation, native devkitPro
  cross-compilation of the optional triangle NRO, GPU shader binding,
  actual `dkCmdBufDraw` execution, frame rate or visual correctness.
  The current Actions failure is a zero-step runner problem;
  this is not a confirmed C/SDK compile failure.
- **Still required for Vandal Hearts:** stable deko3d triangle
  rendering on physical hardware, correct depth/texture orientation,
  proper DDS GPU uploads, original Daldren's six draw batches and
  two atlas bindings, matching PS3 animation/material appearance,
  tactical gameplay and campaign reconstruction.

**A presentable GPU triangle must be observed on physical hardware
before this task can be considered implemented end-to-end.**
