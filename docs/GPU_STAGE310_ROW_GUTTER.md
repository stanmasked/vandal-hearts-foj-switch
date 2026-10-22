# Stage310 — row-varying native BC1 cross-page gutter and real NeXium proof

**Base:** Stage309 [Draft PR #194](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/194) verified actual GPU reconstruction of two contrasting page-edge color pairs using an explicit third RGBA8 gutter and a linearly filtered 18-vertex scene. This does not imply that independently clamped GPU samplers automatically bridge pages.

## Generalized helper (no fixed game colors)

`foj_stage310_build_page_edge_gutter()` takes **any two** already decoded 256×256 RGBA8 page buffers, their exact sizes, and a distinct caller-owned 256×256 output. It copies the *last column* of the left page to gutter columns 0..127 and the *first column* of the right page to gutter columns 128..255, row by row. It computes the matching theoretical bilinear seam midpoint using the Stage308 native C reference for **every row** and counts rows with contrasting endpoints and genuine intermediate colors. It never reads files, publishes original PS3 data, or changes the usual loader.

Inputs must have precisely 256×256×4 bytes. The helper rejects nulls, short/oversize buffers and output aliases with either input or report. A temporary output is assembled before any caller output bytes or report are changed. Inputs remain unmodified, and rejected calls leave outputs untouched.

## Synthetic 1024 BC1 stress atlas

A separate opt-in NRO builds a generated-only canonical 1024×1024 BC1 atlas. It decodes adjacent pages (1,1) and (2,1) with the actual Stage301 C decoder. The pages contain **eight distinct 32-pixel-high horizontal stripes** spanning every row; across each stripe boundary, both page-edge colors change.

| Stripe | Left page | Right page | Desired midpoint |
|---|---|---|---|
| 0 | Blue | Yellow | Grey |
| 1 | Red | Green | Olive |
| 2 | Green | Blue | Teal |
| 3 | Yellow | Red | Orange |
| 4 | Magenta | Cyan | Grey |
| 5 | Cyan | Magenta | Grey |
| 6 | White | Black | Grey |
| 7 | Black | White | Grey |

The native scene retains Stage309's 18 vertices, three independent 256×256 textures, reverse-Z `Greater` depth ordering (foreground gutter z=0.68; pages z=0.55), explicitly linear deko3d sampling and narrow seam strip. The **generated-only** Stage293 material input gate remains strict. A distinct Stage310 guest-written receipt requires 256 processed rows and 256 true mixed rows.

## Verification

Host GCC and Clang run two actual-C test executables: (1) Stage301 BC1 decode → Stage310 generic 256-row gutter → Stage308 cross-page midpoint, with exhaustive row/pixel and rejected-overlap checks; (2) complete generated 18-vertex scene in Stage310 mode. Python host mock negative tests reject wrong palette, missing/reordered stripe, one-page-only clamp, forged receipt, stale source provenance, unsafe symlinks and extra private files. Fabricated PNGs are **never** accepted as live GPU proof.

A true NeXium GPU run must capture two distinct framebuffer phases with all eight stripes in increasing vertical order in **each screenshot**. For every stripe, the independent auditor searches for a continuous run of 12 or more rows with simultaneously matching left RGB, right RGB and an intermediate seam color. A 5×5 probe near the center of each stripe must match 22/25 or more pixels. All eight rows must appear in the correct order and there must be no page-endpoint leak into the narrow seam. The auditor checks native marker, unmodified synthetic DDS manifests and two separate guest frames. It exports only eight explicitly allowlisted generated-only files, excluding raw logs and game assets.

## Scope and next stage

This is a **demonstration of explicit CPU-built seam gutters used by a GPU**, now under changing texture colors along the seam. It is not general automatic bilinear across independently bound textures, not original-game UV mapping, and not a physical Switch test. Subsequent work should generalize seam geometry, handle multiple differently oriented atlas page crossings and inspect original texture topology privately before claiming parity.
