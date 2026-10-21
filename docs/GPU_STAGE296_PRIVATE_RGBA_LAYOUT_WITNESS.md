# Stage296 — private RGBA layout witness for a single candidate source

**Stack:** [Stage295 Draft PR #180](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/180), [Stage294 #179](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/179). Real guest proof from [Stage293 #178](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/178) concerns **invented**, not original PS3, textures.

## Evidence problem

A header/payload length match does **not** prove the meaning of source pixel bytes, BGRA vs RGBA channel ordering, mip boundaries, or row padding. Stage296 therefore adds a **two-reference witness** without adding an original-game decoder or publishing pixels.

For one owner-selected **local extracted file**, supply:
- A separately held 0600 private SHA-256 file for exact **source bytes**.
- A different, separately held 0600 private SHA-256 file for the complete **independently obtained canonical RGBA mip-chain bytes**, including every level in the same order.
- An explicit hypothesis: `bgra` or `rgba`, with tightly packed rows (alignment `1`) or rows padded to a 16-byte boundary (alignment `16`).

These references should be independently produced by a trusted owner-local capture or other confirmed texture reader. **Deriving a reference with this same hypothesis/decoder is circular** and does not independently validate it.

## Local invocation (no networking or files written)

```bash
python3 -m tools.foj_stage296_private_rgba_layout_witness \
  --source-root /PRIVATE/EXTRACTED \
  --relative-file PATH/TO/CANDIDATE.bin \
  --source-digest-root /PRIVATE/OWNER-HELD-SHA256 \
  --source-digest-file original-expected.sha256 \
  --reference-digest-root /PRIVATE/SEPARATE-RGBA-REFERENCE \
  --reference-digest-file reference-rgba.sha256 \
  --order bgra --row-alignment 1
```

All three roots must be independent, not nested, no symlink ancestors. Digest files require `0600`-compatible private permissions and precisely 64 lowercase hexadecimal chars plus optional newline. Input is a single local regular file, never a PKG or web URL. Source size is capped at 2 MiB, so large files are deliberately rejected.

The script first computes **two complete SHA-256 passes on one anchored no-follow source fd**, compares both to each other and to the owner-held private hash, then performs a third byte-for-byte-consistent read. It strictly checks a **single invented GTF-like 0x02000101 / 0xA5 / 2D / one-image** hypothesis: offset 128, exact source length, declared mip chain, native atlas image bounds (width 8–256 divisible by eight; height 1–256; at most nine levels), explicit base pitch and row alignment. For each mip, it skips potential row padding and applies the selected RGBA/BGRA byte order. It hashes the full private decoded canonical RGBA chain *only in memory* and compares that hash with the separate private reference.

Success prints only a compact set of **boolean conclusions, selected hypothesis labels and limitations**: it does not expose source filenames, source digest, reference hash, original dimensions, pixel bytes, texture data or source offsets. No DDS or PNG is created or uploaded.

### Why this is not an original PS3 texture decoder

- `0x02000101` and descriptor offsets are a **hypothesis**, not proven native FoJ source semantics.
- A digest match with an independent RGBA reference can establish **pixel equality under one declared interpretation** but cannot independently establish original game provenance, original FoJ material association, or rendering correctness on real hardware.
- The test does not interpret RSX tiled/swizzled pixels, BCn blocks, endian-swapped channels, atypical pitch/layout/multicontainer data, or any original game texture not supported by the narrow local comparison.
- Stage296 does not permit original-game DDS conversion; it creates no new source-derived artifact.

## CI acceptance

GitHub Actions runs a synthetic-only set of tests on Python 3.11 and 3.13: invented RGBA and BGRA source pixels, full mip chain including 16-byte-padded tails, mismatched channel order/pixel witness, independently held source hash mismatch, malformed layout/dimensions/pitch/extent, linked files, root nesting and path disclosure refusals. Actual PS3 original assets, private digests, reference pixels and processed source files are never uploaded or printed.

**Actual owner-data validation** remains pending until original extracted NPEB00148 resources and an independently obtained RGBA reference are available in a private runtime. Success on generated assets only does **not** prove the game's source format.
