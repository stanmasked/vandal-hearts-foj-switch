# Experimental Switch GPU smoke tests — stage 140

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

Archived stage 135 artifact `foj-gpu-native-research`:
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

Archived stage 136 artifact `foj-gpu-native-research`:
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

Archived stage 137 artifact:
https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39035732156/artifacts/12102067683

Host GCC/Clang tests (including normal, NDEBUG and ASan/UBSan pixel
regressions), Research tools tests and native GPU NRO/DKSH CI all passed.
**This does NOT prove GPU sampling, orientation, copy synchronization or
presentation on real Switch hardware.**

## Stage 138 — original uncompressed DDS-only build (historical)

GitHub Actions native build run **39036526057** (PR #21) compiled and
validated two real devkitA64 ARM64 NRO files plus three UAM DKSH modules.
The research NRO can now optionally load a private DDS for each material,
while keeping the original two synthetic RGBA8 images when no files exist.
The cross-compiled GPU NRO is **290872 bytes**, same aligned NRO size as
stage 137; the independent clear NRO remains **262200 bytes**.

Stage 138 artifact:
https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39036526057/artifacts/12102068939

Optional paths, local to the user's own SD card:

```text
sdmc:/switch/foj/gpu/material0.dds
sdmc:/switch/foj/gpu/material1.dds
```

**Stage 138 supported subset** (superseded by stage 139):
- Classic 128-byte `DDS ` header (`dwSize=124` and `DDS_PIXELFORMAT.dwSize=32`)
- Uncompressed 32-bit pixels in **RGBA byte order** (`R=0x000000ff`,
  `G=0x0000ff00`, `B=0x00ff0000`, `A=0xff000000`)
- Width **8–256**, a multiple of 8; height **1–256**
- Pitch = width × 4, one image, at most one mip level, no extra file bytes
- No BC1/BC3/BC5/BC7, DXT, DX10, compressed formats, mip chains, cube maps
  or PS3-specific tiling/swizzling. The common commercial-game DDS formats
  will therefore often require a separate **local, user-controlled**
  conversion step before they become compatible.

A missing optional DDS uses the internal synthetic texture for that
material. A DDS that exists but is malformed or unsupported **causes the
research NRO to reject startup** rather than silently interpreting data
as pixels. The DDS reader is bounded to 256 KiB pixel data per material
and host tests check that failures do not modify caller buffers.

These are the research material IDs 0 and 1 only; this is **not**
automatic import of the original FoJ materials or geometry. Do not
publish original PS3 assets or place them into this repository.

Host checks: run **39036526010**, GCC/Clang ordinary, NDEBUG, ASan/UBSan
all successful. Research tests run **39036526025** successful.

**Physical Nintendo Switch read/copy/sample/display is NOT verified.**

## Stage 161 — two private classic DDS slot preflight

Before manually copying your own classic DDS into `sdmc:/switch/foj/gpu/material0.dds` or `sdmc:/switch/foj/gpu/material1.dds`, run locally:

`python3 -m tools.foj_gpu_local_dds_preflight /path/to/private/dds-slots`

A missing slot explicitly uses the existing synthetic fallback. A malformed or unsupported existing slot fails; the tool does not attempt to convert or extract PS3 game data. No source bytes, private paths, or filenames are emitted into the report. The acceptance conditions are compared with the actual C atlas decoder using synthetic tests. Neither successful host tests nor a devkitA64 build proves presentation on real Switch hardware. Full limitations: `docs/FOJ_TEXTURE_RESOURCE_RECON.md`.

## Stage 139 — BC1/DXT1 and BC3/DXT5 classic DDS decoding

The newest research NRO also accepts **classic DDS with DXT1 (BC1) or
DXT5 (BC3)** FourCC compression. The input blocks are decoded entirely
in host/CPU memory into tightly packed RGBA8 before the existing deko3d
image-upload path. GPU texture binding and material IDs 0/1 are unchanged.

Stage 139 verified native build: GitHub Actions run **39037261317**, PR #22.
- `foj-deko3d-triangle-research.nro`: **294968 bytes**
- `foj-deko3d-clear-smoke.nro`: **262200 bytes** (unchanged)
- Three UAM-compiled and stage-validated DKSH files included

Stage 139 artifact:
https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39037261317/artifacts/12102557872

Accepted private atlas formats:
- Classic DDS without DX10, extended headers, mip chains or cubemaps
- Existing **uncompressed RGBA8**: width 8–256 (multiple of 8), height 1–256,
  exact 32-bit RGBA channel masks, pitch = width×4
- **DXT1 / BC1**: FourCC `DXT1`, 8-byte blocks per 4×4 pixels, including
  three-color transparency when BC1 color endpoint 0 ≤ endpoint 1
- **DXT5 / BC3**: FourCC `DXT5`, 16-byte blocks per 4×4 pixels, with
  interpolated alpha (both endpoint orderings supported)
- For compressed files: width 8–256 and multiple of 8; height 4–256 and
  multiple of 4; `dwPitchOrLinearSize` is the **total compressed data size**
- Exact file length, one image, at most one mip level; max decoded output
  **256 KiB per material**, with the same SD filenames as stage 138

Stage 139 did NOT support: BC2/DXT3, BC4/BC5/BC6/BC7, DX10/DXGI variants,
mipmaps, swizzled/tiled PS3 GPU textures, nonmatching channel masks,
odd block dimensions and DDS files with trailing proprietary data. Some
real game assets will require additional analysis or local conversion.

Independent **GPU host regression run 39037261332 SUCCESS** for GCC and
Clang, normal/NDEBUG and ASan/UBSan. Tests verify BC1 palette and one-bit
transparency; BC3 color palette and two alpha modes; invalid FourCC,
truncated/padded data, malformed headers and local BC3 test file intake.
**Research tools tests run 39037261302 SUCCESS**.

As in all previous stages, these CI results confirm CPU decoding and
native compilation but **do NOT prove correct sampling, compositing or
presentation on a physical Nintendo Switch**. Do not distribute private
PS3 data with the build.

## Stage 140 — BGRA byte order and complete DDS mip-chain validation

The latest optional research GPU NRO accepts one more classic uncompressed
pixel layout: **BGRA8**, with the 32-bit masks
`R=0x00ff0000, G=0x0000ff00, B=0x000000ff, A=0xff000000`.
It swaps red and blue channels on the CPU to produce the existing RGBA8
GPU upload format; classic RGBA8, DXT1/BC1 and DXT5/BC3 remain supported.

DDS files may now contain a **complete, contiguous mip chain**, including
the canonical DDS mip-count flag and `DDSCAPS_TEXTURE|COMPLEX|MIPMAP`.
The loader validates the exact bytes of every mip level (for BC1/BC3,
using at least one compressed block as dimensions shrink), rejects
truncation/trailing bytes, and decodes **only level 0**. It does *not*
create GPU mip levels, enable mip filtering, or make the native renderer
sample lower-resolution mipmaps.

Dimensions still: base width 8–256 and divisible by 8; base height 1–256
for uncompressed or divisible by 4 for BC1/BC3. Full mip chains may shrink
to 1×1; at most nine levels. Peak input file cap is **384 KiB** and
decoded level-0 RGBA8 is still capped at **256 KiB per atlas**.
Incomplete mip chains are accepted only if their advertised level count
and supplied bytes match exactly, with valid DDS flags and caps.
DX10 headers, BC2/BC4/BC5/BC6/BC7, cubemaps, volumes, arrays,
swizzled/tiled PS3 resources and proprietary extra bytes remain
unsupported.

**Latest verified build**: PR #23, native devkitA64/UAM GitHub Actions run
**39037930630**. Native GPU NROs and DKSH shaders built successfully:
- `foj-deko3d-triangle-research.nro`: **294968 bytes**
- `foj-deko3d-clear-smoke.nro`: **262200 bytes**

Download the current seven-day CI artifact:
https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39037930630/artifacts/12103085997

GPU host regressions run **39037930668** passed both GCC and Clang
under strict C11, NDEBUG, and ASan/UBSan, including synthetic BGRA,
RGBA8/BC1/BC3 mip tails, corrupt mip counts/caps, and a local
256×256 nine-level DDS file test. Research tools run **39037930657**
also passed.

**No on-console image readback or GPU presentation has been confirmed.**
None of these tests establishes compatibility with any specific FoJ PS3
atlas; the SD cards must contain only user-owned, locally prepared files.

## Stage 163 — DDS descriptor checks and safe manual diagnostics

The shader-backed research NRO now emits a generic DDS intake result for
each synthetic material slot to stderr if the homebrew environment
provides it. The messages do not contain the private filename or image
data. A missing DDS keeps the synthetic fallback; present symlinks,
directories, unsupported or changed DDS files cause startup rejection.
The native code uses descriptor/stat checks and `O_NOFOLLOW` where the
platform provides that flag. This is not a complete defense against
malicious replacement of an ancestor directory, nor evidence of correct
texture sampling on real hardware. Follow the stage-162 A–E observation
matrix in `docs/GPU_STAGE162_SD_SMOKE.md`.

## SD card layout for a user-authorized homebrew Switch

The NROs may be placed in a homebrew-launcher-readable folder, for example:

```text
sdmc:/switch/foj/foj-deko3d-clear-smoke.nro
sdmc:/switch/foj/foj-deko3d-triangle-research.nro
sdmc:/switch/foj/gpu/foj_actor.vert.dksh
sdmc:/switch/foj/gpu/foj_triangle.frag.dksh
# Optional, user-owned DDS in the strict supported format:
sdmc:/switch/foj/gpu/material0.dds
sdmc:/switch/foj/gpu/material1.dds
```

The triangle program loads its DKSH files from **exactly** those two GPU
shader paths; this is hardcoded in `gpu/deko3d_clear_main.c`. The third
artifact, `foj_actor.frag.dksh`, belongs to the separate actor-shader
experiment and is not needed by the triangle NRO. The clear NRO does not
require DKSH files.

## Hardware test checklist (NOT YET EXECUTED)

For the new stage-162 two-DDS protocol (no original game assets), see
`docs/GPU_STAGE162_SD_SMOKE.md`. The host/native builds do not replace
on-console observations.


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
