# Stage306 — eight BC1 color bands prove nonconstant GPU UV interpolation

**Base:** [Stage305 Draft PR #190](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/190). Stage305's actual NeXium run verified two separate 256×256 BC1 pages in one screen-space split rectangle, with 81/81 correct pixels for each side in two distinct guest frames. Stage306 makes both halves nonuniform and their sampled local UV coordinates varying.

## Stage306 native GPU experiment

In an opt-in research NRO, the native C code checks all three incoming DDS/material fixtures against the precise original-free synthetic Stage293 RGBA bytes, camera-produced 9-vertex source topology and metadata. It allocates an **invented** 1024×1024 BC1 DDS with four horizontal, 64-texel-wide bands within each selected 256×256 page. Stage301's actual C decoder extracts pages (1,1) and (2,1), and the host checks **every pixel** against the expected RGB565-expanded byte values.

| Page | Horizontal BC1 band 0 | Band 1 | Band 2 | Band 3 |
|---|---|---|---|---|
| Left (1,1) | Red (255,0,0) | Orange (255,130,0) | Blue (0,0,255) | Cyan (0,255,255) |
| Right (2,1) | Cyan (0,255,255) | Magenta (255,0,255) | Green (0,255,0) | Yellow (255,255,0) |

Both halves share the **same cyan edge color** at the x=640 GPU seam. All other atlas pages are painted red, while the sample audit uses eight differently located colors: the wrong page, reversed UV, constant UV, or wrong band is observable.

The scene still uses 15 clip-space vertices. Two adjacent page-local quads each cover half of one 768-pixel rectangle (screen x=256..640 and x=640..1024). Unlike Stage305, their vertex U varies **0 to 1 across each half** and V varies **0 to 1 vertically**. The existing deko3d shaders perform actual interpolated texture sampling. The material0 diagnostic triangle remains far from the seam.

Host-side GCC and Clang exercise actual Stage306 C code. The actual devkitA64 build links the C generator and produces a separate NRO, without changing the default research executable.

## Actual NeXium acceptance

The Stage306 guest drive first excludes diagnostic-only frames and accepts a framebuffer **only if all eight** 9×9 regions at screen x=304,400,496,592,688,784,880,976 and y≈400 show their expected native-decoded RGB values. At least 78 of 81 pixels must match within ±3 per channel per band. It also checks cyan RGB continuity at x=629..638 and x=642..651, adjacent to but excluding the two exact boundary columns with potentially rasterizer-specific top-left coverage rules. A second framebuffer with an independently observed background clear-color phase change must repeat all these color tests.

The native NRO emits an exclusive **Stage306** marker identifying the invented band/page/vertex experiment. An independent evidence auditor verifies that marker, the two true NeXium frame pixels, strict before/after synthetic DDS source attestation, and no unknown public files. Only eight explicitly allowlisted generated files are published, including two screenshots; original NPEB00148 resources, raw guest logs and private source data are not included.

Mock PNG tests are used **only to show that fake, swapped, static, incorrect, or cracked surfaces are refused**. The passing host/mock tests alone do not establish that NeXium actually drew the bands; only the live `nexium` job can establish that.

## What is NOT established

A visually continuous cyan area across the seam provides evidence of correct nearest/ordinary page-local sampling for this specially matched-edge synthetic texture, **not** an independent hardware bilinear border-reconstruction proof. The exact boundary columns, derivatives, anisotropic filtering, automatic polygon splitting, game-native material/UV data, owner-local source DDS headers and a real physical Nintendo Switch are **not** verified. The default sampler has clamp-to-edge and an SDK-default filter setting. Stage307 should examine measurable filtered transitions using high-contrast gradients/edge texels and explicit sampling settings, not assume the current screenshot proves arbitrary original texture seams.
