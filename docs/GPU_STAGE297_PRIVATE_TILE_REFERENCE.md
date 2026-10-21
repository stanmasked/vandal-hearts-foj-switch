# Stage297 — invented tile order experiments with independent local pixel witness

**Base:** [Stage296 PR #181](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/181), with source SHA-256 and independent expected RGBA-chain SHA-256 in private local directories. Stage293 [PR #178](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/178) already proved real NeXium GPU output **for synthetic conversions only**.

## What this establishes

For explicitly chosen **hypotheses**, the same authenticated local source bytes can be interpreted as tiles and compared, including the complete mip chain, to **separately obtained RGBA reference pixels**. No game asset or digest is uploaded to GitHub.

This is **not** a PlayStation 3 RSX swizzle decoder. The code models exactly two invented *within-tile* layouts (row-major raster and Morton Z-order) for square 4×4 or 8×8 pixel tiles, a row-major ordering **of tiles**, and RGBA or BGRA channel ordering. Each mip uses whole physical tiles even if it has fewer valid pixels, so padded edge pixels are ignored. These choices are **not known to be FoJ formats** and are never automatically chosen.

The owner keeps in separate, private, non-nested, no-symlink local directories:
1. A selected, already extracted source file with a hypothetically compatible 0x02000101/0x85 2D single-image header; size <= 2 MiB.
2. A 0600 private source SHA-256 digest file obtained independently.
3. A different 0600 private reference SHA-256 file covering the concatenated canonical RGBA mip-chain pixels obtained from a **separate reliable tool**.

```bash
python3 -m tools.foj_stage297_private_tile_reference_gate \
  --source-root /PRIVATE/EXTRACTED \
  --relative-file CANDIDATE/TEXTURE.bin \
  --source-digest-root /PRIVATE/SOURCE-SHA \
  --source-digest-file trusted-source.sha256 \
  --reference-digest-root /PRIVATE/REFERENCE-SHA \
  --reference-digest-file independently-captured-rgba.sha256 \
  --tile 8 --in-tile morton --channel bgra
```

The process performs two streamed SHA-256 reads, a third full byte read on the same anchored no-follow source descriptor, compares the caller's owner-held digest and rejects normal race/mutation, traversal, symlink and oversize cases. The original source and expected canonical RGBA reference remain separate. It does not write images, DDS or decoded pixels, does not expose private input identifiers/dimensions/offsets or hashes, and never authorizes original-game conversion.

The declared texture header is only a ***hypothesis***: version 0x02000101, format byte 0x85, 2D, noncube, exactly one image, data at offset 128, exact file extent and declared mip count. The inferred base row pitch must equal the tile-row allocation width. Pixels are reassembled from 4×4 or 8×8 invented tiles, with per-mip tile edge padding. The only accepted result is a privately computed match against the reference SHA-256. Altered padding is acceptable if the expected original source digest was independently updated; pixel changes or incorrect channel/tile/mip orders do not match the independent reference.

## CI coverage and limitations

The 29 generated-only Python unit tests validate tile4/tile8, raster/Morton, RGBA/BGRA, odd dimensions and padded mip tails, tile index bijection, incorrect source order, incorrect reference, altered data, header/file length mismatches, private digest permissions, symlink refusal, parent traversal, and no private identity disclosure. Python 3.11 and 3.13 are tested. This CI does **not** touch original PS3 assets or produce new artifacts.

The real NPEB00148 texture format remains **unverified**. Neither source/header nor matching private digests can prove game provenance, texture semantics or gameplay. Actual source bytes plus a truly independent pixel reference are required for a future local, gated original-resource experiment.
