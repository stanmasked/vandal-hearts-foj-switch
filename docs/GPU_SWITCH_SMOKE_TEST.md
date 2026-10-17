# Experimental Switch GPU smoke tests — stage 137

These are **homebrew research binaries**, not a playable port or a patch for
*Vandal Hearts: Flames of Judgment*. No original PS3 content is embedded.

## Proven build

The official `devkitpro/devkita64:20260219` container produced and
validated both real AArch64 GPU NROs and three UAM DKSH shader modules
in **stage 135**, GitHub Actions run **39028292878** (PR #18).
This updates the shader-backed NRO with a **six-vertex/two-triangle synthetic
surface** generated through the real `foj_gpu_prepare_stream` function,
instead of the earlier single hardcoded triangle. The independent clear NRO
is unchanged. Both host compilers, the native compiler and research tests
passed. There is still no verified hardware runtime.

Download the latest artifact `foj-gpu-native-research` from:
https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39028292878/artifacts/12099815118

Earlier stage 134 build evidence: run `39026793109`, artifact `12099185278`;
that older triangle-mode binary draws just one fixed triangle.

GitHub Actions retains the artifact for seven days. Its absence later does
not invalidate the CI logs or change the fact that a new build is required.

## Stage 136 — newest multi-batch research build

GitHub Actions run **39034956773** (PR #19) built and validated both
real AArch64 NROs and all three DKSH modules with devkitA64/UAM.
The shader-backed experiment now uploads **12 vertices** forming four
triangles in **two separate draw batches**. Both use the same research
UV-gradient shader; the material indexes are not yet real texture binds.
The clear-only NRO is unchanged. GPU host checks and research tests also
passed.

Newest artifact `foj-gpu-native-research`:
https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39034956773/artifacts/12101922180

Do not interpret successful compilation as verified on-console rendering.

## Stage 137 — actual two-texture GPU material research build

GitHub Actions run **39035732156** (PR #20) generated both native ARM64
NROs and all three DKSH modules using devkitA64/UAM. The shader-backed
experiment now generates **two distinct synthetic 8x8 RGBA8 textures**,
copies them into GPU-resident images, prepares one sampler and descriptor
table, and binds a different image handle before each ordered batch draw.
The fragment shader samples those textures, replacing the UV-gradient-only
shader from previous stages.

New native research NRO: **290872 bytes** (validated NRO0 header).
The clear-only NRO is unchanged (**262200 bytes**).

Latest artifact:
https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39035732156/artifacts/12102067683

Host GCC/Clang tests (including normal, NDEBUG and ASan/UBSan pixel
regressions), Research tools tests and native GPU NRO/DKSH CI all passed.
**This does NOT prove GPU sampling, orientation, copy synchronization or
presentation on real Switch hardware.**

## SD card layout for a user-authorized homebrew Switch

The NROs may be placed in a homebrew-launcher-readable folder, for example:

```text
sdmc:/switch/foj/foj-deko3d-clear-smoke.nro
sdmc:/switch/foj/foj-deko3d-triangle-research.nro
sdmc:/switch/foj/gpu/foj_actor.vert.dksh
sdmc:/switch/foj/gpu/foj_triangle.frag.dksh
```

The triangle program loads its DKSH files from **exactly** those two GPU
shader paths; this is hardcoded in `gpu/deko3d_clear_main.c`. The third
artifact, `foj_actor.frag.dksh`, belongs to the separate actor-shader
experiment and is not needed by the triangle NRO. The clear NRO does not
require DKSH files.

## Hardware test checklist (NOT YET EXECUTED)

1. Record Switch hardware model, homebrew environment and date; use a device
   you own and are already authorized to run homebrew on.
2. Launch the **clear-smoke** NRO first. It should present two alternating
   solid-color palettes, switching every 120 presented frames. Confirm that
   the image is visible and changing, not merely that Homebrew Menu returns.
3. Press **+** only after at least one frame has been displayed. Note whether
   the program closes cleanly or throws an error.
4. Launch the **triangle-research** NRO with both DKSH files in the exact
   paths above. Expect **two separated, differently colored textured
   quads** (four triangles, 12 uploaded vertices) over the alternating
   clear colors. Each synthetic 8×8 image uses its own color gradient.
   Neither image comes from FoJ PS3 assets.
5. Note whether an exception, missing shader, black screen, freeze, or
   rendering corruption occurred. Preserve any screenshots/error text
   and a brief description of which test failed.
6. A successful visual smoke test confirms that one specific hardware
   configuration presented frames; it is **not** evidence that the PS3
   renderer, original gameplay, or full Nintendo Switch port is functional.

Do not distribute original proprietary PS3 data with test binaries. No
user-owned FoJ game data is required for these two GPU smoke applications.

## Developer rebuild

With devkitPro devkitA64, libnx, deko3d, the UAM shader compiler and Python 3:

```sh
make -f gpu/clear.mk verify
make -f gpu/triangle.mk verify
make -f gpu/Makefile triangle-verify
make -f gpu/Makefile verify
```

These commands build/validate binaries on the development machine.
They do not execute them on Switch or validate real framebuffer output.
