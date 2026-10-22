# Stage315 — four-page corner RGBA material for a GPU experiment

**Base:** Stage314 Draft PR #199, the independent CPU bilinear reference for
the intersection of four BC1 pages; Stage313 Draft PR #198 established
EAST/SOUTH seam contracts. Stage312's NeXium GPU success concerns a two-page
horizontal seam only, not this new four-page corner.

## New generated-only material

The new C module accepts **four caller-owned RGBA8 decoded 256x256 pages**
ordered NW=(1,1), NE=(2,1), SW=(1,2), SE=(2,2). It extracts the four
true source corner texels at local (255,255), (0,255), (255,0), (0,0).
It produces a 256x256 RGBA8 quadrant material with a split at X=128 and Y=128.
The four texels (127,127), (128,127), (127,128) and (128,128) thus represent
the original four neighboring atlas texels.

A bilinear GPU sample at normalized material U=V=0.5 is **expected** to
mix those four colors, as independently calculated by Stage314. This stage
does not claim the GPU has performed it.

## CI proof

The native test checks all **65,536 output pixels and all four RGBA channels**.
It samples **81 two-dimensional subtexel positions**, comparing Stage314
floating-point output against an independent rational integer oracle with
a single final rounding step. The complete material must remain bytewise
equivalent after a mathematical transpose and swapping NE/SW source pages.

Negative cases reject nulls, missing source pages, wrong lengths, output
aliasing any source, and report aliasing an input/output. Invalid calls must
leave the output, source pages and report unchanged. Four identical source
colors must report zero contrast and no false four-page interpolation witness.

Matrix: optimized GCC, optimized Clang, GCC UBSan, Clang ASan/UBSan.
All tests operate on generated in-memory RGBA8 fixtures. No private PS3
assets, original NPEB00148 game data or emulator logs enter public CI.

## Deliberate limits and next step

The current code builds a CPU-side RGBA8 source material; it neither uploads
a texture nor proves a NeXium framebuffer. The next opt-in deko3d research
NRO can use this material for a four-way gradient. GPU acceptance should
require two distinct real frames; all four page colors, intermediate
horizontal and vertical gradients, and a genuine four-source center;
a native receipt; input identity attestations; and a minimal generated-only
artifact allowlist. Original FoJ UV/material mapping and physical Switch
rendering remain separate investigations.
