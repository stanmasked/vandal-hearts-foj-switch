# Stage 167 — visible DKSH shader boot failures on Switch

**Not physically verified.** This is a shaderless *fallback* screen in
the experimental shader-backed GPU research NRO. It does not turn FoJ
into a playable Nintendo Switch port and does not contain PS3 assets.

## Why this stage exists

Earlier GPU DDS status colors (green/blue/amber and others) only appear
**after** the native shader load, shader validation and texture staging
have progressed far enough to create the normal status command lists.
If vertex or fragment DKSH files are missing or rejected, the prior NRO
could return to Homebrew Menu without showing those DDS colors.

Stage 167 introduces a separate error path that uses existing GPU
device, queue, two framebuffer images, swapchain and command buffer
**without requiring DKSH programs**. It records persistent shaderless
color-clear command lists for both acquired swapchain images and
continues presenting the error color until + or applet exit. Any such
failure returns nonzero exit status **6**, even if color frames were
successfully presented. Generic stderr output is supplemental only;
its visibility depends on the homebrew environment.

## Early shader failure legend

| Full-screen color | Exact class of failure |
| --- | --- |
| Orange | Shader code memory could not be allocated or CPU-mapped |
| Violet/purple | Vertex DKSH file absent, unreadable, unsupported or invalid |
| Amber/yellow | Fragment DKSH file absent, unreadable, unsupported or invalid |
| Red | DKSH slot layout rejected by CPU checks |
| Dark red | deko3d rejected the initialized shader stage(s) |

Only the classes above use the early shader path. Colors **do not prove**
why an individual file could not be read (missing and malformed DKSH
share a generic status), that a compiled Maxwell program ran, or that
GPU scanout was successful on hardware.

Other failures **before the swapchain and command buffer exist**,
including device creation, queue initialization, image allocation or
swapchain creation, cannot be shown through this GPU route and may
still yield a black screen or immediate return. Texture upload or
draw-command failures **after** shader initialization are outside this
specific diagnostic route. If shader initialization succeeds, the
previous stage-164 DDS status colors appear normally.

## Suggested safe manual scenarios

Start from a freshly downloaded successful stage-167
`foj-gpu-native-research` artifact and the synthetic-only stage-165
SD bundle. Do not edit commercial PS3 files or upload private user data.

1. Run the shader-free clear NRO. Expect its alternating colors, not
   stage-167 shader-error colors.
2. Run the unchanged triangle NRO with its two generated DKSH files.
   Expect the existing material0/material1 DDS green/green prelude
   and two synthetic checkerboards if shader creation works on console.
3. On an SD copy **only**, temporarily rename the *synthetic*
   `foj_actor.vert.dksh`. The triangle NRO should show persistent
   violet instead of a blank or silent startup failure.
4. Restore it; temporarily rename the *synthetic*
   `foj_triangle.frag.dksh`. Expect persistent amber.
5. Restore both files and verify the ordinary DDS prelude returns.

These are **expected behaviors, not recorded console observations**.
Use the stage-166 private observation ledger to record only what a
person actually sees. A later audit does not independently verify
real Switch presentation or diagnose system driver faults.

## Validation scope

A pure C test checks five distinct color/status mappings, invalid
inputs, and deterministic selection of an acquired framebuffer over
4,096 synthetic frames for every failure class. The actual NRO source
uses that same color mapper. GCC/Clang C11, NDEBUG, ASan/UBSan, SDK-free
syntax checks and devkitA64/UAM builds run in CI. They establish
internal logic and cross-compilation, **not hardware display**.

The error helper returns on +/applet exit and leaves the enclosing
research NRO with exit code 6. It is not a general boot recovery
mechanism, has no PS3 resource decoding and does not infer game state.
