# Stage292 — deterministic GTF-like BGRA → native DDS round-trip

**Stack:** [Stage291 Draft PR #176](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/176) → [Stage290 PR #175](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/175) → [Stage289 PR #174](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/174).

## Verified objective

This is **not a PS3 GTF decoder**. It is the first **invented, deterministic** texture translation experiment, designed to prove that our output DDS construction and selected channel-order/mipmap rules can be verified against **the actual C11 Switch-side DDS decoder** in `gpu/atlas_dds.c`, compiled natively with both GCC and Clang.

The source is an invented single-image GTF-*like* header with version bytes `02 00 01 01`, synthetically specified image metadata and an unmistakable `FOJ_STAGE292_SYNTHETIC_ONLY_V1` tag. The tag and **every generated pixel byte** must match the test generator. This completely forbids ordinary original PS3 bytes from being accepted by the converter. The byte layout is an experimental hypothesis, not a FoJ provenance claim.

## Conversion model under test

The *invented* source describes a linear BGRA8 payload, tightly packed with a base-row pitch of `width×4`. The deterministic generator produces distinct red, green, blue and alpha components for each pixel at each mip level. Only this generated data is eligible for conversion.

- Validate exact invented 128-byte header, synthetic marker, one texture, linear-format hint `0xA5`, 2D geometry, bounded pitch/payload and exact total bytes.
- Validate width 8–256 (multiple of 8), height 1–256 and no more than 9 legal mip levels. Odd heights and mip tail sizes are tested.
- Convert BGRA channel bytes to canonical RGBA8 for **every** mip, preserving alpha without premultiplication.
- Assemble canonical classic DDS: RGBA masks, pitch, mip flags and caps, full length with no trailing data.
- Require `classify_classic_dds` to accept the result. Separately exercise **actual compiled `foj_atlas_dds_decode` C code** and compare every output level-0 pixel byte against the independent deterministic RGBA reference. Test unchanged outputs and metadata on native rejection.
- Never serialize a DDS, source texture, private path, hash or screenshot to public CI. The CLI prints only a synthetic metadata receipt.

## Reproduce (invented data only)

```bash
python3 -m tools.foj_stage292_synthetic_gtf_dds_roundtrip --width 24 --height 13 --mips 3
```

No `--input` or output-path argument exists. In CI, the same Python regressions compile and call the real native C decoder with **GCC and Clang**, against Python 3.11 and 3.13.

## Not yet established

Even a successful C byte-for-byte comparison does **not** demonstrate the source PS3 title uses this GTF version, this channel ordering, a linear pixel layout, these format bits, this pitch structure, the same mip organization, or these materials. No original `NPEB00148` assets are decoded, and no guest GPU or physical Switch verification is claimed by this stage.

Real conversion remains disabled until private local source-forensic observations establish the precise source layout; swizzled/tiled textures, PS3-specific endian rules, compressed BC images and original-game material IDs need independent investigation.
