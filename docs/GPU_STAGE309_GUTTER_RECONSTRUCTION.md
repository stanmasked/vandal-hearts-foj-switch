# Stage309 — native edge gutter reconstructs a differing-color BC1 page boundary on NeXium GPU

**Prerequisites:** Stage306 passed actual eight-band GPU UV interpolation; Stage307's immutable previous guest capture replay succeeded after correcting viewport-offset sample positions. Stage308 added a CPU-only cross-page bilinear reference for contrasting edge texels (blue/yellow and red/green). Stage308's four-job native CI must be checked separately; this Stage309 GPU experiment does not automatically establish upstream native green status.

## Concrete GPU strategy

The normal deko3d texture sampler independently clamps each 256×256 page. At atlas x=511/512, the real bilinear mix cannot be recovered by sampling only one independent page. Stage309 tests one **explicit edge-gutter technique**, not transparent automatic behavior. A third 256×256 RGBA8 material is constructed in CPU RAM strictly from the two already Stage301-decoded BC1 pages. For every page-local row:

- Columns 0..127 contain the RGBA pixel copied from the left page's last texel (local x=255).
- Columns 128..255 contain the RGBA pixel copied from the right page's first texel (local x=0).

For each row, the native Stage308 C reference independently confirms what bilinear color is expected at atlas U=0.5. Only after verifying the decoded contrasting endpoints and their true interior mixed color does the scene replace the three original *generated-only* Stage293 material buffers.

The test NRO renders two adjacent page-local quads occupying [-0.6,0] and [0,0.6] in clip-space X (one page texture each) and a narrow **foreground seam quad** occupying [-0.03,+0.03]. The seam patch uses a **linear deko3d sampler** and varying page-local texture U from 127.5/256 to 128.5/256; at screen-center X it samples precisely halfway between adjacent colors stored in its own third texture. That patch is closer in depth than the base rectangles (z=0.68 vs 0.55), so the existing fixed three-material pass order draws the bridge last.

All 18 vertices, three 256×256 RGBA8 material buffers and the synthetic 1024 BC1 source are generated in the NRO; no real NPEB00148 texture or original-game UV data is loaded. The standard Switch NRO is unchanged; the Stage309 build is opt-in.

## Independent frame proof

The host GCC/Clang test must pass for actual native C page decoding, patch pixel provenance, every row, midpoint, geometry and rejection of modified inputs. devkitA64 must produce the real research NRO, not just Python agreement.

The live NeXium guest must then display BOTH contrasting edge-color pairs in the same actual 1280×720 GPU frame, once in each of two different background-clear phases:

| Screen row | Left page | Right page | Reconstructed seam center |
| --- | --- | --- | --- |
| upper, y≈280 | Blue (0,0,255) | Yellow (255,255,0) | Grey (128,128,128) |
| lower, y≈460 | Red (255,0,0) | Green (0,255,0) | Olive (128,128,0) |

The independent frame checker requires 45/49 pixels near each left/right/center reference color, refuses a center matching either page's clamped endpoint, and verifies nearby interior pixels are not single-page endpoint colors. The tolerated central RGB error is ±22 due to screenshot sampling/rasterization. A genuine guest-written native marker and Stage293 before/after source attestations are mandatory; only an eight-file generated-only allowlist including two framebuffer PNGs can be published.

**Limits:** This is a *separate, explicit CPU-assembled gutter geometry texture* reconstructed and linearly sampled on the GPU. It is NOT arbitrary GPU bilinear reconstruction across two independently bound texture objects and not a shader handling all triangle/page crossings. The exact seam border rasterization rule is not proven for arbitrary game geometry, and original PS3 textures/UVs and physical Switch execution remain unverified. Stage310 can explore a shader-aware multi-page sampler or generalized mesh splitting with per-edge gutters, subject to actual game-source validation privately.
