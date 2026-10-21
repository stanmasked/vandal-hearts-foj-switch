# Stage307 — explicit nearest/linear deko3d filter proof on generated BC1 pages

Stage306 [PR #191](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/191) verified 8 BC1 color bands in **one actual NeXium GPU screenshot**, using a synthetic 1024×1024 DDS atlas split into two 256px native decoded pages. Real GPU clips proved 81/81 sampled pixels per band in each of 2 frames and continuous cyan interior bands near the join. It did NOT verify filtering mode or generic cross-page bilinear seams.

## Engineering change

Stage307 uses the same exact generated-only texture and 15-vertex split-quad scene, but builds **two different native Switch NROs** from `gpu/stage307_filter_compare.mk`. The standard renderer remains untouched in builds without `FOJ_GPU_STAGE307_FILTER`.

| Build flag | Native `DkSampler` minFilter | magFilter | UV wrap |
| --- | --- | --- | --- |
| `STAGE307_FILTER=0` | `DkFilter_Nearest` | `DkFilter_Nearest` | ClampToEdge |
| `STAGE307_FILTER=1` | `DkFilter_Linear` | `DkFilter_Linear` | ClampToEdge |

deko3d permits explicit `DkSampler` min/mag filter control, according to [devkitPro's deko3d Primer](https://github.com/devkitPro/deko3d/blob/master/Primer.md). Both NROs write a distinct **native guest-authored** receipt after sampler descriptor initialization: `FOJ_NATIVE_STAGE307_FILTER_V1` with exact selected min/mag mode. Such a marker on its own does **not** establish GPU filtering; it just ties an actual native code path to the generated scene.

The 1024 BC1 pixel data, stage293 synthetic input gate, vertex data, GPU shader, page selection and renderer setup are identical for both variants. This isolates explicit sampler mode as the intended independent variable.

## Real NeXium evidence gate

CI compiles both NROs with devkitA64, runs native C-generated atlas verification and host negative tests on GCC and Clang, then launches **two distinct real NeXium guests**, one NRO per mode. Each guest independently captures two non-identical background-phase 1280×720 framebuffer PNGs and revalidates the Stage306 eight-band signature plus DDS before/after attestations and native filter-mode marker.

A final CI job compares **all four actual GPU PNGs**, at 12 screen sample points straddling the six **within-page** BC1 band transitions: x=351/352, 447/448, 543/544, 735/736, 831/832, 927/928; y=400. These are known adjacent 64-texel color bands of the decoded pages, rasterized over 96 screen pixels each. The nearest sampler must report the appropriate single RGB565 endpoint at every sample with tolerance 4/channel. The linear sampler must keep every channel within the neighboring texels' value range with ±8 allowance, and at least 8 of 12 transition samples must differ by ≥14/channel from nearest for **each** clear-color phase. Equal or swapped mode outputs fail closed.

Mock PNG tests intentionally generate intermediate-color samples to test failure behavior; mock passes are never accepted as proof of actual GPU rendering. Native receipts, unmodified generated-only source files, PNG provenance, and a strict **9-file public allowlist per mode** are independently required. Original game assets, raw guest log, private source paths or owner manifest are not exported.

## What this cannot demonstrate

- Transition smoothing is tested **inside each independently sampled 256px page**. At the **cross-page** screen seam, both source edges are intentionally cyan, so images cannot distinguish alternative bilinear reconstruction algorithms across two different pages.
- No automatic triangle division, atlas UV derivative normalization, anisotropy, genuine FoJ material UV mapping, original NPEB00148 source headers, PS3 textures, or physical Nintendo Switch hardware has been verified.
- NeXium uses software Vulkan/Mesa graphics; its success is not a substitute for physical-device verification.

Stage308 should introduce differing colors on the two **opposite atlas-edge texels** and explicitly choose an edge treatment (stitching via padded gutters, shader-aware cross-page sampling, or controlled seam suppression), backed by generated-only GPU frames. Avoid claiming cross-page bilinear continuity based on the same-cyan setup.
