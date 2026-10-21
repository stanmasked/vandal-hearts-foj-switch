# Stage300 — reconciliation of historical *real* FoJ DDS evidence with the 256px GPU loader

**Date:** October 21, 2026. Branch stacked after [Stage299 PR #184](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/184).

## Correction to the Stage290–299 GTF investigation

The repository already contains **original PS3 resource observations from October 16, 2026**, recorded in [REAL_RESOURCE_SIGNATURES.md](REAL_RESOURCE_SIGNATURES.md) and [REAL_PSARC_NPEB00148.md](REAL_PSARC_NPEB00148.md). The owner-uploaded split ZIP / debug-style PKG was examined *then*; five actual `.tga`-named files from `cdata.psarc` start with genuine classic `DDS ` magic. Two sampled files were **BGRA8 256×256**, and three **DXT1/BC1**, including one **1024×1024**. The five samples were opened and decoded locally with Pillow at that time.

This does **not** establish that all 1,479 `.tga` assets use the same internal DDS formats. Nor is there now an actual user-original PS3 file available in the current runtime for a new direct verification.

**The later 0x02000101 GTF-like experiments are synthetic conjectures, not the leading known source format for the five documented textures.** They should not replace or obscure the evidence we already have.

## Native gap demonstrated with real C code and invented pixels

The old `core/dds_texture.c` accepts **BGRA8 and BC1 up to 4096×4096**, and decodes base mip level 0. The newer strict `gpu/atlas_dds.c` accepts **BGRA8/RGBA8, BC1/BC3 up to only 256×256**, and restricts lengths, DDS header flags and complete mip chains. These are distinct contracts. Calling a file merely 'DDS' does not guarantee it is eligible for GPU slot binding.

Stage300 constructs synthetic DDS files with exactly the **already publicly documented** five dimension/format/file-byte triples, but with completely invented test pixels (not originals). It compiles **both actual C decoders** and compares all 256px output pixels and alpha byte-by-byte, with GCC and Clang; the synthetic 1024px BC1 sample succeeds in the old decoder but is rejected by the newer atlas without modifying caller buffers or metadata.

| Original sample named in previously published report | Documented envelope | Synthesized direct atlas eligibility |
| --- | --- | --- |
| archery_target.tga | 256×256 BGRA8, 262,272 bytes | Eligible by invented canonical DDS envelope |
| avatar_flame_texture.tga | 256×256 BGRA8, 262,272 bytes | Eligible by invented canonical DDS envelope |
| avatar_texture.tga | 1024×1024 BC1, 524,416 bytes | **Blocked: exceeds 256px atlas limit** |
| balastradian_trooper_texture.tga | 256×256 BC1, 32,896 bytes | Eligible by invented canonical DDS envelope |
| bandit_lt_texture.tga | 256×256 BC1, 32,896 bytes | Eligible by invented canonical DDS envelope |

**CRITICAL:** 'Eligible' here means *the native intake accepts a new synthetic DDS with the same dimension/format/length*, **not** that the exact owner-private source bytes, optional DDS caps/metadata, original mip semantics or original game's material binding have been tested in this stage. As before, no original asset was committed. Actual native C outputs were compared, not actual physical Switch GPU frames.

## Recommended next work (Stage301)

1. Adapt the 256px-only **research atlas** to support an alternate carefully bounded 1024px BC1 route, or provide explicit safe texture-region sampling/tiling and a new GPU upload budget; choose an architecture based on measured NeXium memory cost, not assumption.
2. Add owner-local **read-only** acceptance checks for the *real* DDS files when private originals are accessible again, checking exact caps/masks/mips without exporting data.
3. Prove a real model's material→texture mapping, decoded pixel origin and frame output only in a private authorized environment; keep public NRO and GitHub evidence synthetic.

Do not present Stage290–299 guesses as original game format discovery, and do not claim the native 256px loader handles all original textures.
