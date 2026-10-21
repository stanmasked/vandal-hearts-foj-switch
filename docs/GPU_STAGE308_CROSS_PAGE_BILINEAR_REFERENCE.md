# Stage308 — two different BC1 page-edge texels and true cross-page bilinear reference

**Base:** Stage307 [PR #192](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/192). The Stage307 NeXium guest successfully captured generated-only nearest and linear images in separate runs, but the first cross-run comparator failed because it used projected screen coordinates instead of a small actual guest viewport offset. A bounded step-finding correction and a real-GPU evidence replay were added upstream; their CI acceptance is independent of Stage308.

## Missing guarantee

A 1024×1024 BC1 atlas split into independent 256×256 GPU texture pages is not automatically bilinearly equivalent to the original **single** 1024 atlas at a page boundary. The existing Stage306/307 generated source colors both boundary bands cyan, which cannot expose the difference.

For normalized atlas U around `0.5` at the boundary between atlas texels **511** and **512**, a true bilinear atlas sample combines the **last texel of page (1,1)** and the **first texel of page (2,1)**:

`C(t) = round_nearest((1-t) * left[255,y] + t * right[0,y])`, where `t = u*1024 - 511.5` and `u` lies between their centers `511.5/1024` and `512.5/1024`.

Existing independently clamped samplers see **only one page's** edge texel. Their output cannot produce this mixed color when the two page-edge colors differ. Passing Stage307 nearest/linear tests *inside* each page is not proof of this property.

## Stage308 native C reference

New research-only helper `foj_stage308_cross_page_bilinear()` takes two **already decoded** 256×256 RGBA buffers (caller-owned), a page-local row and one normalized U restricted to the seam texel-center interval. It uses the existing **actual Stage303 UV resolver** to verify page (1,1), local x=255, and page (2,1), local x=0; then returns the four-channel linear blend with deterministic rounding. It never reads a file, accepts a PS3 asset, changes the deko3d sampler, creates a GPU NRO, or publishes any pixel data. It refuses NaN/infinity, out-of-range U, page row outside 0..255, and null pointers; output is unchanged on rejection.

A second function `foj_stage308_requires_two_pages()` rejects trivial cases where a purported seam blend is equal to either independent page's clamp-to-edge output or outside either endpoint. It is an explicit **negative witness** for the current two-page drawing model, not an installed GPU fix.

### Generated-only independent test

The host C test generates a canonical 1024×1024 BC1 DDS **from invented pixels**, decodes its left and right pages using the actual Stage301 `foj_bc1_1024_decode_page()`, then compares edge texels and expected blends:

| Row in page | Left edge | Right edge | Midpoint at atlas U=0.5 |
| --- | --- | --- | --- |
| 0..127 | Blue (0,0,255,255) | Yellow (255,255,0,255) | Grey (128,128,128,255) |
| 128..255 | Red (255,0,0,255) | Green (0,255,0,255) | Yellowish (128,128,0,255) |

It also tests exactly centered, quarter and three-quarter positions between the edge texel centers, several rows, invalid numeric positions, null buffers, and absence of writes when rejecting input. The workflow compiles actual C code under GCC, Clang, UBSan and ASan/UBSan. No original game data, private paths, game texture sizes other than the historical public hypothesis, SHA-256 of game resources, or preview images are uploaded.

## Boundary and next implementation stage

Stage308 establishes a **CPU mathematical baseline** and demonstrates the gap in independent GPU `ClampToEdge` page sampling. It does **not** make the current research scene bilinearly seamless. The next stage should select a concrete GPU implementation: e.g., a fragment shader that samples both page edge texels using separately bound textures at the seam, or expanded edge gutters with a texture/page layout that fits GPU constraints. Then validate **both different edge colors and the actual mixed RGB** on real NeXium screenshots. Replaying real Stage307 evidence and confirming its independent CI remains a prerequisite for closing upstream Stage307.

No owner-held PS3 `NPEB00148` original data is committed or uploaded. Real FoJ UV layout and physical Nintendo Switch execution remain unverified.
