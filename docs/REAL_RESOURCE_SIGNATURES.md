# First direct texture / model / shader signature observations

**Date:** 2026-10-16. Data sampled directly from the user's original NPEB00148
PKG → cdata.psarc in a local environment. No commercial bytes included here.

## Five sampled texture assets

The files have **.tga filenames but DDS containers**. Their 128-byte DDS
header is little-endian, followed by raw texture payloads.

| Asset (within data/actors/npc) | Width × height | Declared pixel format | File size |
| --- | --- | --- | ---: |
| archery_target.tga | 256 × 256 | uncompressed BGRA8 (32-bit DDS masks) | 262,272 |
| avatar_flame_texture.tga | 256 × 256 | uncompressed BGRA8 (32-bit DDS masks) | 262,272 |
| avatar_texture.tga | 1024 × 1024 | DXT1 (FourCC DXT1) | 524,416 |
| balastradian_trooper_texture.tga | 256 × 256 | DXT1 | 32,896 |
| bandit_lt_texture.tga | 256 × 256 | DXT1 | 32,896 |

Only **five** of the 1,479 .tga paths were sampled; it would be incorrect
to claim that all 1,479 use these exact layouts without further validation.
DDS metadata and file lengths agree for these five examples.

## Model, animation and shader observations

- Five `.bmodel` samples share leading byte `0B` and contain printable
  material/model identifiers soon after the header. The internal geometry
  schema is not established.
- Five `.banim` samples share leading byte `0D`; animation encoding,
  joints, frame rate and track structure remain unknown.
- Five `.cgelf` shader resources begin with ELF magic (`7F 45 4C 46`),
  indicating PS3-targeted binaries, **not Switch-compatible shaders**.

This is a header reconnaissance milestone, not proof of mesh/animation
decoding or correct material rendering.

## Porting consequences

1. Dispatch texture decoding from **DDS magic** rather than .tga extension.
2. Implement strict DDS header checks and DXT1/BGRA8 decode with synthetic
   fixtures first, followed by local validation on user-owned assets.
3. Decode `.bmodel` vertex layouts and `.banim` skeleton/pose tracks only
   after obtaining a reproducible structure specification.
4. Rebuild portable shaders/render passes for Switch; do not link PS3 Cg ELF
   shader binaries directly into the ARM64 executable.

Nothing from this sample was added to the GitHub source tree.
