# Stage313 — Orientation-neutral BC1 edge-gutter adapter

**Base:** Stage312 [PR #197](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/197) horizontal native GPU research. Stage310 established an explicit vertically oriented gutter, and Stage311 separately verified horizontal edge-gutter mathematics. Stage312 NRO has compiled and native GCC/Clang checks passed; the true horizontal NeXium GPU result must be independently checked and not assumed here.

This change removes duplicated *call-site decision logic* while preserving both approved native implementations. A new native C interface `foj_stage313_build_oriented_gutter()` dispatches to the actual Stage310 east/right-neighbor implementation or Stage311 south/bottom-neighbor implementation, with exact RGBA8 page lengths, output alias rejection and normalized row/column counts. The functions accept **only pages already decoded in caller-owned memory**. The adapter never consumes game files or owns a Switch GPU resource.

The orientation is explicit, not inferred by pixel dimensions (both inputs remain 256×256). The caller must provide the correct source ordering. Unknown orientation fails closed and leaves the output buffer and report unchanged. Reports overlapping source pages or output are refused.

## Metamorphic regression

The same two invented RGBA8 source pages are used in two independent operations:

1. Build an east gutter from their last/first pixel **columns** using the actual Stage310 implementation.
2. Transpose both source pages, build a south gutter from their last/first pixel **rows** using the actual Stage311 implementation.
3. Verify, byte for byte, `transpose(east_gutter) == south_gutter` for **all 65,536 output pixels** and all four channels. Normalized counts of 256 processed, contrasted and genuinely mixed source-edge positions must agree. Independently compare both outputs and report counts against calling their original C implementations directly.

The negative matrix checks null pointers, unsupported orientation, missing/extra byte lengths, aliasing the output with either source, report aliasing both source pages or output, unchanged source buffers and unchanged output/report on rejection. It also checks flat identical source pages do not generate false contrast or false mixed-color metrics.

CI matrix: optimized GCC, optimized Clang, GCC UBSan, Clang ASan/UBSan. Every test is C code, not a Python mock and not a GPU screenshot. No private NPEB00148 files, original game textures, raw emulator logs, or physical device claims.

## Remaining boundaries

The unified adapter currently has only two orientations—right and bottom neighbors—at the Stage303 fixed research pages (1,1), (2,1), (1,2). It does not prove arbitrary atlas coordinates, original game UV mapping, diagonal/corner filtering or automatic GPU bilinear across independently bound textures. Future work can build on this interface to select valid gutter orientation when a real mesh crosses pages, after inspecting the owner's real PS3 resource topology privately.
