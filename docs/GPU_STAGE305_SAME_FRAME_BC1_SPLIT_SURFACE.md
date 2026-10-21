# Stage305 — one generated split surface with two BC1 atlas pages in a single NeXium GPU frame

The previous [Stage304 PR #189](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/189) passed all six CI jobs: two side-specific NROs used the same original-free generated 1024 BC1 source and selected adjacent page (1,1) vs (2,1) across UV=0.5. Four genuine NeXium GPU frames confirmed each page color and a final independent cross-run comparator succeeded.

**Stage305 tests a different property:** both adjacent pages appear in **the same GPU frame** as halves of a contiguous screen-space rectangle, divided by a vertical seam. Unlike Stage304, this is one geometry submission with two separate material draws, not two NRO runs. It still does **not** prove bilinear filtering or automatic splitting of a single original triangle in shader space.

## Native path and scene

The opt-in `gpu/stage305_split_surface.mk` compiles a distinct NRO with `FOJ_GPU_STAGE305_SPLIT_SURFACE`; it does not change the default research NRO. Stage305 first validates the exact three Stage293 generated DDS RGBA images and their known 3×3-vertex input batches (any modified source is refused). It builds a brand-new 1024×1024 compressed, synthetic, single-mip BC1 atlas in native memory, and uses the **actual Stage303 UV mapper** for two centers `u=511.5/1024` and `u=512.5/1024`, `v=384.5/1024`.

The **actual Stage301 C BC1 page decoder** extracts pages (1,1) and (2,1). Pixel-by-pixel checking verifies their chosen solid RGB565 colors. The incoming scene's two invented translucent front triangles are replaced with 15 generated clip-space vertices and three material batches:

| Draw batch | Role | Clip-space X | Vertex count | BC1 page / GPU RGBA |
| --- | --- | --- | ---: | --- |
| Material 0 | Tiny, off-seam diagnostic triangle | +0.88..+0.94 | 3 | Original invented translucent texture |
| Material 1 | Right half of the split rectangle | 0..+0.60 | 6 | (2,1), RGBA (24,203,222,255) |
| Material 2 | Left half of the split rectangle | -0.60..0 | 6 | (1,1), RGBA (16,199,214,255) |

Both halves share the same vertical interval -0.50..+0.50. Two triangles per half use page-local texel-center coordinates (0.5,0.5), because **each page is deliberately solid**. The GPU uploads two separate decoded 256×256 RGBA buffers, preserves the strict maximum texture dimensions and submits the actual material draw batches. Native Stage273 three-triangle dynamic sorting is **deliberately disabled**: its fixed 3/3/3 input expectation is incompatible with this new 3/6/6 geometry; default draw order is opaque material2, then opaque-alpha material1, then off-seam translucent material0.

The native program emits a fresh exclusive receipt identifying generated page coordinates, seam and vertex count before GPU boot. That receipt **alone** does not prove GPU rendering; the CI captures real NeXium frames.

## Acceptance

- GCC/Clang execute the actual Stage305 C scene constructor: correct two different BC1-decoded pages and pixel colors, 15 vertices/three valid draw batches, the matching clip-space seam, exact source validation and no mutations on failure.
- devkitA64 builds the separate Stage305 NRO and real DKSH modules.
- The actual NeXium guest renders **two GPU frames** with different clear-color phases. Each captured 1280×720 screenshot must show *both colors simultaneously* near the centered seam (x=640) with ±2 channel tolerance and at least 78/81 matching 9×9 region pixels on **each side**; a contiguous 19-pixel scan on each side must not contain a crack or third-page leakage. The two screenshots must differ in independently sampled clear-background regions.
- Independent before/after provenance checks tie the scene to exactly the generated Stage293 material inputs and require a native NRO-authored 15-vertex receipt. Only eight allowlisted generated evidence files (including two PNGs) may be published; the raw guest log and game assets remain private.

## Explicit boundaries

The two page-local half-quads deliberately share x=0 in screen space; Stage305 proves **visible surface splitting with no wrong-page area near the seam**, subject to the screenshot resolution. The exact seam rasterization rule for the single boundary column is not asserted. Hardware bilinear reconstruction *across an original game texture page seam* is **not** established; neither is automatic mesh subdivision, original game PS3 UV conventions, actual package source acceptance or a physical Switch run. Original user-owned NPEB00148 resources are not included in generated public CI. The logical next step is UV-varying high-contrast patterns and actual bilinear seam handling, not another uniform-color extrapolation.
