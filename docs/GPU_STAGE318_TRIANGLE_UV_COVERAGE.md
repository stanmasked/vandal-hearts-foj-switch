# Stage318 — exact positive-area UV triangle coverage of BC1 atlas pages

## Goal

Stage316 verified on real NeXium GPU that one explicit research texture can
blend four neighboring synthetic BC1 texels in both dimensions. Stage317
generalizes CPU texel addressing to all sixteen 256×256 pages in a 1024×1024
atlas, but neither stage maps geometry onto its texture pages.

Stage318 introduces a strictly geometry-only test for triangles whose
normalized UVs cross page boundaries. All fixtures are newly invented;
no original FoJ mesh, NPEB00148 assets or raw emulator logs are used.

## Algorithm

foj_stage318_triangle_page_coverage() receives three finite normalized
UV coordinates in [0,1]. It clips their triangle against each of sixteen
closed page rectangles (left/top/right/bottom lines at multiples of 0.25)
with Sutherland–Hodgman half-plane clipping using double precision. It
measures the positive area of each resulting polygon and returns a 16-bit
row-major page mask, per-page areas, page count and number of crossed
vertical/horizontal grid lines.

Why not simply use bounding boxes? The UV bounding rectangle can cover
four pages even when a diagonal triangle has positive area in only three.
The native regression contains a triangle near the central intersection with
exactly NW, NE and SW positive-area coverage, and excludes SE.

Triangles merely touching a page edge with zero area do not claim ownership
of the neighboring page. Invalid zero-area / near-degenerate geometry,
out-of-range or nonfinite UVs, null pointers and overlapping input/output
buffers are refused without mutating the caller's output.

## Native tests

- Sixteen independently positioned triangles fully inside each atlas page,
  including cyclic reordering of vertices.
- All nine four-way page junctions crossed by synthetic triangles, exact
  expected page-mask tests and preservation of total UV area.
- Three vertical and three horizontal straight page-boundary crossings.
- A diagonal triangle whose bounding rectangle overcounts by one page.
- An exact zero-area edge-touch and a UV=1 outer atlas corner.
- UV transpose metamorphic tests: each area must move to the corresponding
  transposed page, and vertical/horizontal line counts exchange.
- NaN, infinity, negative/greater-than-one UVs, zero-area and minuscule
  triangles, null/aliased output rejection and preservation on all failures.

Four host configurations run in GitHub Actions: GCC optimized, Clang
optimized, GCC UBSan and Clang ASan+UBSan.

## Explicit limitations

The algorithm measures positive geometric UV area, not every texel
that GPU bilinear filtering might fetch near triangle edges. It is not a
full rasterizer, UV unwrapper, page-boundary mesh clipper, or PS3 game asset
importer. It makes no claim of original FoJ UV mapping or physical Switch
hardware. Next investigate candidate page/filter support based on actual
mesh/material metadata privately, then generate explicit page patches where
needed. Keep the PR Draft while CI verification proceeds.
