# Stage314 — four-way BC1 page-corner interpolation contract

Base: Stage313 PR #198, normalized EAST/SOUTH edge gutter API verified by GCC, Clang and sanitizers. Stage312 PR #197 independently confirmed true horizontal NeXium GPU frames in workflow 39802531749. Neither straight-edge mode automatically solves a junction of four different page textures.

## Why this matters

Stage310 and Stage311 each blend a pair of adjacent decoded BC1 pages along a straight edge. Where four pages meet, correct bilinear filtering must fetch all four original texels and interpolate in both normalized atlas axes. Blending only one horizontal or vertical page pair can produce a central artifact.

Stage314 introduces foj_stage314_four_page_bilinear(), a separately compiled C reference for the synthetic 1024x1024 atlas junction. Source pages must be supplied in this order: NW page (1,1), NE (2,1), SW (1,2), SE (2,2). It verifies Stage303's mapping of integer atlas texels (511,511), (512,511), (511,512), (512,512) to page-local edge coordinates before reading. It permits only normalized atlas U and V in [511.5/1024, 512.5/1024] inclusive. Values are weighted in floating point over both axes and rounded only once after the complete four-source blend, for every RGBA channel.

A separate foj_stage314_requires_four_page_mix() conservatively checks the result differs from each corner and every two-page edge midpoint and lies within the channel extrema of its sources. It is a mathematical witness, not evidence of automatic cross-page deko3d filtering.

## Actual native synthetic BC1 tests

The test builds a strict canonical 1024x1024 DDS DXT1 block atlas with four colored pages: NW red (255,0,0,255); NE green (0,255,0,255); SW blue (0,0,255,255); SE white (255,255,255,255). Each page is decoded through Stage301's native C BC1 decoder and checked across all 65,536 RGBA texels.

The sampler is evaluated at 25 positions on a 5x5 subtexel grid. The exact four-source midpoint is (128,128,128,255), different from each individual corner and two-page edge interpolation. The test also varies four source-edge alpha bytes to 0,64,192,255 and checks 128 at the midpoint with one final rounding step.

The negative matrix checks NaN/infinite/out-of-window UVs, null pointers/output, invalid page lengths and output aliasing each of the four source buffers, while asserting all original data remains unchanged. GCC optimized, Clang optimized, GCC UBSan and Clang ASan/UBSan run the same real native C test, with only invented data.

## Scope and follow-up

CPU numerical validation only. This PR does not prove a four-page GPU junction, original PS3 game UV parity, arbitrary meshes, or physical Nintendo Switch execution. The next step is an opt-in four-page junction scene with genuine NeXium GPU framebuffer proof and strict generated-only evidence controls. No private NPEB00148 bytes or original game textures are included.
