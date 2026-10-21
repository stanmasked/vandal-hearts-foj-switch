# Stage298 — inverse tile-layout and ambiguity gate

**Base:** [Stage297 Draft PR #182](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/182) (owner-local tile-size, Morton/raster and independent pixel reference), [Stage296 PR #181](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/181) (linear channel/pitch hypotheses), [Stage295 PR #180](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/180) (independent private source digest).

## Failure mode

**Byte-perfect decoding followed by inverse encoding is *not evidence that we chose the right texture interpretation*.** For every invertible layout and any input, decoded pixels can be reversed into the same bytes. For example, an opaque solid-gray 16×16 image can appear identical under 4×4 or 8×8 tiling, raster or Morton order, and RGBA or BGRA channel assumptions. Matching just one chosen interpretation or a single-color frame would falsely claim the layout was established.

## Gate

For the same one-file, private, separately held source and reference SHA-256 inputs required in Stage297, Stage298:

- Replays the source twice in bounded streaming SHA-256 passes and a third complete, anchored, no-follow read.
- Enumerates **all eight** explicitly supported, invented layout hypotheses: tile size 4 or 8, raster or Morton within-tile, RGBA or BGRA channels. Each candidate still has to satisfy Stage297's bounded mip, pitch and exact-length rules.
- Compares **all decoded mip levels** of every structurally admissible candidate against a *separate* owner-held expected canonical RGBA SHA-256 reference. The independently produced reference must include color distinctions and spatial patterns to distinguish layouts.
- Reconstructs every candidate matching that reference back into the original texture storage positions, **preserving padded tile cells exactly**. Requires exact equality with the source bytes.
- **Fails closed if zero or multiple candidates match**. An opaque flat-color image is deliberately ambiguous even if every candidate roundtrips perfectly.
- Prints only a safe summary of the unique candidate's invented parameters, checks and explicit evidence limitations. No private source path, SHA-256 value, texture pixel, PNG, DDS or game data leaves the local process.

### Owner-local usage

```bash
python3 -m tools.foj_stage298_inverse_tile_ambiguity \
  --source-root /PRIVATE/EXTRACTED \
  --relative-file CANDIDATE/TEXTURE.bin \
  --source-digest-root /PRIVATE/SOURCE-SHA \
  --source-digest-file expected-source.sha256 \
  --reference-digest-root /PRIVATE/INDEPENDENT-REFERENCE \
  --reference-digest-file canonical-rgba.sha256
```

The roots must be independent and nonnested; the two digest files must be 0600-private and contain exactly 64 lowercase hexadecimal SHA-256 characters (optional newline). A correct reference **cannot be generated with the same unverified decoder** without circular evidence.

### Restrictions and next step

This only tests eight **invented** pixel arrangements, not documented RSX swizzle, endian policy, BCn decoding, original GTF descriptor semantics, or association with FoJ materials. A unique match *among these eight* still does not prove the original format. No real NPEB00148 assets were examined or converted, and no physical Switch testing occurs. Original game material conversion stays unauthorized.

Generated-only GitHub CI includes differentiating gradients, full mip tails and distinct RGB/alpha values; a deliberately ambiguous solid gray fixture; inverse padding preservation; wrong-reference and altered-source refusals; symlinks, sensitive hash permissions and path checks. No private files or artifacts are uploaded.

**Stage299 direction:** independently challenge multiple different discriminating witness images/regions with different content before any proprietary source interpretation; prioritize acquiring or privately verifying actual PS3 source resources rather than expanding guesses indefinitely.
