# Stage317 — generalized native BC1 atlas bilinear page routing

**Base:** Stage316 Draft PR #201, which passed all four GitHub Actions
jobs including two genuine NeXium GPU frames for a fixed four-way
synthetic corner. Stage315 proved the quadrant texture source material.
Stage317 is deliberately a separate CPU reference, not a GPU claim.

## Scope of generalized sampling

Stage316 sampled the specific atlas junction between pages (1,1), (2,1),
(1,2) and (2,2). A 1024×1024 atlas divided into 4×4 pages has nine
internal four-way intersections as well as three horizontal and three
vertical sets of page seams. The original game can potentially sample
any such region.

The new API foj_stage317_sample_atlas takes 16 independent caller-owned
256×256 RGBA8 pages in row-major order and normalized atlas UV in [0,1].
It resolves four original atlas texels via the Stage303 verified atlas
integer-texel mapper, then applies genuine bilinear interpolation in
both axes with a single final rounding. It returns the four resolved
atlas/page/local texel locations, number of distinct source pages,
and whether the sample crosses any vertical and/or horizontal boundary.

Unlike a fixed junction shader, this reference correctly selects the
corner pages at every legal coordinate, clamps the outer atlas edges,
and validates all 16 non-overlapping page input buffers. It rejects
nulls, duplicate material pages, wrong sizes, nonfinite or out-of-range
UVs, output overlaps, and report overlaps without modifying caller
output or report on failure.

## Native generated tests

Every pixel of the 16 source RGBA pages has a coordinate-dependent
synthetic color, including variable alpha. Nine four-way junctions ×
25 UV positions = **225 four-way reference samples**, validated against
independent exact integer-rational RGBA8 arithmetic and full Stage303
coordinate reports.

Additional tests validate three horizontal and three vertical page-seam
families with independent midpoint arithmetic, all four outer clamped
atlas corners, an ordinary interior sample and source immutability by
hash. Negative tests exercise malformed page arrays, NaN/Inf/outside
UVs, wrong dimensions, aliased pages, aliased output and aliased report.

CI: optimized GCC, optimized Clang, GCC UBSan, Clang ASan/UBSan.
These are compiled C tests rather than a Python simulation.

## Research boundaries

This is a mathematical reference for caller-owned decoded synthetic
atlas pixels. It does not split original FoJ mesh triangles, determine
original game UVs or texture formats, or claim that GPU sampling automatically
crosses separately bound textures. No original NPEB00148 files, private
assets or raw emulator logs are published. Remain Draft until CI completes.
