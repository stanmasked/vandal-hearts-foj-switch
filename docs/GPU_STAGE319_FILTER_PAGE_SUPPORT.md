# Stage319 — bilinear filtering source-page support for UV triangles

## Background

Stage316 passed a real NeXium GPU experiment with a generated four-color
corner patch. Stage317 passed all four native C compiler/sanitizer checks
for atlas texel routing across all 16 BC1 pages. Stage318 implements a
positive-area geometric UV triangle mask across those pages, but a triangle
can be entirely within one page while bilinear sampling near its edge
requires texels from an adjacent page.

The two concepts must remain separate: geometric triangle footprint
must not be mistaken for bilinear texel support.

## Exact half-texel halo rule

On a normalized 1024×1024 atlas, the neighboring sample begins to matter
within one half atlas texel, **0.5 / 1024 = 1 / 2048 UV units**, of a page
boundary. Stage319 computes each page's continuous UV sampling support
by expanding its 1/4×1/4 rectangle by this amount on all four sides,
clamping outer boundaries to [0,1], and clipping the original UV triangle
against it using Sutherland–Hodgman polygon clipping.

Each **positive-area** intersection sets a page bit. Stage319 returns:

- Stage318 geometric positive-area page mask.
- Continuous-domain bilinear filter-support mask, unioned over triangle UVs.
- Halo-only source page mask = filter pages outside geometric coverage.
- Page counts and exact half-texel halo.

A triangle near the northwest corner of a page can have 1 geometric
page but **4 filter-source pages**, even if it does not geometrically
cross either page boundary. A diagonal triangle geometrically covering
only 3 pages can have a fourth page required by bilinear filtering.

This is a conservative continuous-UV prediction. A finite raster may
sample fewer pixels, and zero-weight taps at exact texel centers are not
an independent positive-area source requirement.

## Generated native proof

The C regression validates sixteen safe interior samples, every vertical
and horizontal page boundary from each side, all nine internal 4-way
corners, halo-only pages on diagonal geometry, zero-area boundary
touching, atlas outer-edge clamp, and transpose invariance. Negative
cases reject null, aliasing, NaN, infinity, out-of-range UVs and
degenerate triangles without mutating the output.

Four CI configurations: GCC/Clang optimized, GCC UBSan, Clang ASan+UBSan.

## Limits and privacy

This computes a 16-page *source dependency mask*, not new clipped mesh
triangles, GPU descriptors, UV splitting, shader-based blending, or actual
original Vandal Hearts: Flames of Judgment mesh interpretation. Original
PS3 assets and raw emulator logs remain out of public GitHub. No physical
Switch experiment is claimed. Keep this research PR Draft.

Next: combine Stage318+319 page masks with synthetic triangle batches,
then study original asset topology only in an isolated private environment.
