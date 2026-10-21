# Stage303 — nearest-neighbor BC1 atlas UV to page/texel mapping

**Base:** [Stage302 PR #187](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/187), which builds a separate NRO and tests selected-page GPU presentation in NeXium. Stage302's NeXium acceptance must be reported independently when its real CI finishes; Stage303's tests alone do NOT prove a page seam was rendered by a GPU.

## Problem

The Stage301 native C decoder supports 16 distinct 256×256 BC1 pages from a 1024×1024 classic DDS. Stage302 uses page (2,1) for its invented-color rear atlas. Correct coordinate routing is still necessary before a hypothetical FoJ 1024 texture can be rendered with the strict 256px atlas loader. A single fragment at the edge of a page must not accidentally sample an adjacent page or create a wraparound seam.

Stage303 adds **CPU-side nearest-neighbor routing only**, `foj_bc1_1024_resolve_uv` and `foj_bc1_1024_resolve_texel` in `gpu/stage303_bc1_page_uv.h/.c`. It intentionally **does not change shaders, draw calls or material slots**.

## Explicit sampling contract

- Atlas 1024×1024 with 4×4 pages of 256×256; canonical DDS **top-left** texel origin. Integer texels `x,y` in **0..1023** are accepted.
- Normalized `u,v` must be finite in **[0,1]**. Values at exactly `1` clamp to the final atlas texel 1023, **not** wrap to zero. NaN, infinity, overflow and negatives are rejected without output mutation.
- Integer atlas pixel selected by `floor(u*1024), floor(v*1024)`, clamped to 1023 at normalized 1. Each integer coordinate gives `page_x=x/256`, `local_x=x%256` (and analogously for y).
- Local page normalized coordinates are **pixel centers** `(local_x+0.5)/256`, `(local_y+0.5)/256`. These centers protect against crossing a neighbor tile with point/nearest sampling.
- Exact 0.25, 0.50, 0.75 atlas boundaries choose the **right/bottom** page at local pixel 0; the immediately smaller representable float chooses the **left/top** page at local pixel 255.

This is **nearest only** and does not prove correct filtering or screen-space derivatives. Hardware bilinear filtering needs a separate treatment across page borders (duplicated edge texels, multi-page sampling or shader-aware reconstruction). A triangle whose UVs cross several pages must also be split into page-local geometry or use an explicitly validated sampler strategy; none of that is implemented here.

## Independent pixel proof

The isolated Stage303 workflow compiles **the actual C code** with GCC and Clang and runs Python 3.11/3.13 regression matrices. Every input BC1 block is newly generated, with invented page-varying 565 endpoints, index patterns and some BC1 transparent palette blocks, and matches only the publicly known format/size of one earlier sampled FoJ DDS. No original source bytes or extracted images are accessed.

The tests first decode full 1024×1024 via old `core/dds_texture.c`. They then decode the selected page through Stage301's strict `foj_bc1_1024_decode_page`, route atlas texels across all page edges through the real Stage303 C functions, and compare the resolved page RGBA pixel against the corresponding full-image pixel. Additional coverage includes full horizontal scans on 8 boundary rows, 22×22 combinatorial edge probes, immediate IEEE-754 float neighbors around normalized quarter-page seams, clamp of 1.0, invalid inputs with no writes, and page-local pixel-center constraints.

## Gaps and Stage304

This does not show the routing is **yet used by the guest GPU shader**, does not prove bilinear border behavior, and does not verify actual FoJ UV orientation or material maps. Stage304 should supply a generated-only geometry/UV scene crossing page boundaries, make native GPU code explicitly choose the correct pages and verify real NeXium frames. Private original-game assets stay outside public CI and should be individually accepted only through an owner-authorized local workflow.
