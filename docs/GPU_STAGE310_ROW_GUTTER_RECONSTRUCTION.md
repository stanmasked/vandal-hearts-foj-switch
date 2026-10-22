# Stage310 — generalized row-by-row BC1 cross-page gutter, eight-color-pair real GPU regression

## Confirmed baseline

[Stage309 PR #194](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/194) passed GCC, Clang, devkitA64 NRO creation and a real NeXium GPU render of two invented contrasting BC1 page-edge pairs (blue/yellow and red/green). Both frames correctly showed source endpoints and a blended center; the GPU evidence is [Actions 39693705012](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39693705012). This proves a **foreground, CPU-built edge gutter** sampled linearly in the GPU, not bilinear sampling across two separate texture objects.

## Stage310 implementation

Unlike Stage309's deliberately two-color hardcoded research material, the native helper `foj_stage310_build_page_edge_gutter()` accepts **any two already-decoded 256×256 RGBA8 page buffers** and produces an equally sized reconstructed seam texture. At every row, its first 128 columns replicate the left page's final edge texel, and its remaining 128 columns replicate the right page's initial texel. The resulting texture can be sampled with a normal linear sampler by an explicit, narrow foreground quad.

The helper:
- Validates exact caller-reported byte sizes, nonnull arguments, non-overlapping output buffers and absence of overflowed memory ranges.
- Uses Stage308's actual C cross-page bilinear reference to validate a finite center blend for **every one of the 256 rows**, even if some pages' edge pixels happen to match.
- Counts rows with unequal edges and rows where a truly intermediate color is distinguishable from both endpoints.
- Allocates a scratch buffer, commits output and report only after completing the entire operation, and leaves caller data unchanged on refusal. Original decoded page buffers remain immutable.

There are no assumptions about the source pixel colors, image names, game material offsets, PS3 textures or paths.

### Native 1024×1024 generated BC1 test

The new host test creates a legal **invented** BC1 DDS, decodes actual adjacent 256px pages through the production Stage301 C decoder and fills them with eight different color pairings along the vertical axis (32 decoded pixels per band). It compares **all 65,536 pixels of the generated gutter** with the corresponding source edge texels; for every row it validates the Stage308 true midpoint. It exercises mismatched sizes, null pointers, in-place source/destination aliases, preservation of the output on rejection, and two equal-color page edges where a meaningful intermediate color must *not* be claimed.

The opt-in Stage310 Switch NRO uses the same exact Stage309 18-vertex split-page/gutter geometry and reverse-Z ordering, but changes its **source compressed BC1 atlas** to eight synthetic per-row color pairings. It invokes the new generalized builder instead of Stage309's two-color-specific code, checks that all 256 rows have genuine cross-page mixtures, and writes its own distinct guest-authored witness:

`FOJ_NATIVE_STAGE310_ROW_GUTTER_V1 pairs=8 rows=256 strict_mix=256 pages=1,1+2,1 verts=18`

### Actual GPU evidence contract

The real guest scene renders an 18-vertex split rectangle spanning approximately x=270..1010 and y=173..520 of a 1280×720 NeXium framebuffer, with a narrow foreground gutter at x≈640. Independent screenshot checks require each of these eight row bands:

| Band | Left BC1 page | Right BC1 page | Expected GPU gutter at midpoint |
| --- | --- | --- | --- |
| 0 | Blue | Yellow | Grey |
| 1 | Red | Green | Olive |
| 2 | Green | Blue | Cyan-green intermediate |
| 3 | Yellow | Red | Orange-yellow intermediate |
| 4 | Magenta | Cyan | White-ish intermediate |
| 5 | Cyan | Magenta | White-ish intermediate |
| 6 | White | Black | Grey |
| 7 | Black | White | Grey |

Each pair is generated in native BC1 and verified against the actual decompressed page bytes in host C. Frame acceptance uses **eight 7×7 left/right color probes** and **eight 5×7 seam center probes** per actual screenshot, in **two distinct guest background-clear phases**. The center must be an interior color distinct from both endpoints; neither an uncorrected clipped page, a wrong row mapping, nor a single unchanged screenshot may pass.

The combined public result is confined to an exact **eight-file generated-only allowlist** with two real GPU PNGs, native guest marker, unchanged Stage293 synthetic before/after identities, NeXium binary archive SHA-256 and a fresh independent report. No original PS3 NPEB00148 resources are exposed.

## Explicit scope and limitations

This verifies **row-varying edge gutter construction and GPU interpolation** for an opt-in generated material scene. It is **not** a general shader that samples arbitrary atlases across differently paged textures, a turnkey FoJ scene importer, a restoration of the original game, or proof on physical Nintendo Switch. Screen-space placement is tuned to the tested research geometry; arbitrary triangle clipping and perspective-correct UV derivation require future tests.

A next stage can generalize the gutter **placement and affected mesh topology** to multiple seams, using actual atlas UV boundaries while keeping original game assets local and private.
