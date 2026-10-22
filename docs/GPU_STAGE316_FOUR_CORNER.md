# Stage316 — genuine NeXium four-page BC1 corner GPU experiment

**Base:** Stage315 Draft PR #200 (native quadrant material), Stage314
Draft PR #199 (four-page bilinear mathematical reference), and Stage312
(real NeXium GPU proof for a *two*-page horizontal edge). This is a distinct
opt-in research scene and does not modify normal game rendering.

## Synthetic end-to-end graphics path

1. Load and authenticate the Stage293 three generated-only DDS fixtures.
   No NPEB00148 data is used or uploaded.
2. Build an in-memory canonical 1024×1024 BC1 atlas with four neighboring
   source colors: NW red, NE green, SW blue, SE white.
3. Decode the four independent 256×256 RGBA8 atlas pages through the real
   Stage301 C decoder; preserve NW and SE as distinct backdrop materials.
4. Invoke Stage315's four-page corner builder. It extracts exactly four
   original texels from page-local corners and constructs a 256×256 RGBA8
   quadrant patch; the Stage314 center oracle must be (128,128,128,255).
5. Draw that patch in front of the two separate backing textures, using
   an opt-in 18-vertex deko3d scene with a **linear GPU sampler** and a
   native guest marker. The central quad spans exactly one patch texture
   texel interval in both axes. Its UV midpoint is (0.5,0.5).
6. Build a separate devkitA64 NRO and DKSH pair; never alter previous
   Stage309/310/312 NROs, nor the main FoJ emulator/porting code path.

## Required proof gates

- Native GCC + Clang host C runs test complete decoded 65,536-pixel source
  material, all 18 vertices, reverse-Z, texel-center UV positions, input
  fixture immutability, and rejection of invalid generated materials.
- Python negative tests independently reject missing source attestations,
  wrong guest markers, missing four quadrant colors, flat center bars,
  missing horizontal or vertical gradient, duplicate frames and extra
  files inserted into public output.
- NeXium must actually render **two different framebuffer phases**;
  neither host-produced PNGs nor a guest marker alone count as GPU proof.
- A bounded native screenshot verifier looks for each of four corner
  colors, coherent central four-source RGB, green increasing left to
  right, blue increasing top to bottom, and a red checkerboard cross-term.
- The Stage293 synthetic DDS hashes must match both *before* and *after*
  guest execution. A strict eight-file public evidence allowlist excludes
  original game bytes, local source fixtures, raw guest logs and private
  binding manifests.

## Scope

The patch is explicitly assembled in native C from four source page
corner texels and sampled with an opt-in GPU material. A successful
NeXium screenshot would prove *this* synthetic four-way corner GPU path,
not automatic filtering across independently bound GPU textures, original
FoJ meshes and UVs, or physical Nintendo Switch hardware.

The full PR should stay Draft until its own GCC/Clang/devkitA64 and live
NeXium matrix completes. It is stacked on Stage315, not merged to main.
