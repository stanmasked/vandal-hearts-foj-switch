# GPU Stage280 — Alpha Boundary Position Follows DDS UV

**Base:** Stage279 [PR #164](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/164), [exact-head NeXium CI #39599900571](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39599900571), verified 3/3. Native NRO (SHA-256 `d23e6fb549be8508895095b58b9cd66caf8e4e36fb137d191517873bc5fb2781`) and public DKSH shaders are **unchanged**.

Stage279 measured an actual hard 0→255 alpha boundary at framebuffer X=659 in both inversion directions, but that single static position could not independently establish **UV-coordinate-driven texture sampling**. Stage280 moves the **source** DDS boundary to two independent texel columns and requires the *native* GPU edge to move accordingly, not remain at the former constant location.

## Generated-only input and projected pixel positions

Each case creates a **fresh generated-only** 64×64 RGBA8 DDS near violet material (`material0.dds`) by changing **only its 4096 alpha bytes**. RGB, DDS header, middle-half-alpha warm material, opaque rear-cool material, all three actor triangles, and camera remain unchanged. Both new masks are alpha 0 left, 255 right; only the split texel column differs.

| Case | Source boundary texel | Source U | Expected projected pixel at row Y=440 |
|---|---:|---:|---:|
| `edge-u40` | 40 | 0.625 | 618 (computed continuous ≈618.08) |
| `edge-u52` | 52 | 0.8125 | 680 (computed continuous ≈680.45) |

These X positions follow the *actual Stage275 actor triangle affine UV projection*. In a prior verified Stage279 real NeXium capture, the intended 27-sample footprints **X=605..631** and **X=667..693** at Y=440 were fully inside drawn overlapping material, with stable correctly composited pixels. Source boundaries should shift by **≈62 pixels**; an identical or unmoved on-screen alpha edge must fail.

## Required CI evidence

[Stage280 GitHub Actions](../.github/workflows/stage280-shifted-boundary.yml) reuses the same verified devkitA64 NRO and DKSH shaders and runs the inherited Stage279 C11/host guard suites, plus **12 new Stage280 host regressions**. Its host tests verify the source masks differ *only in alpha*, the strict production C11 decoder accepts both, truncated DDS fails without altering caller state, and the independent **mock-only** verifier rejects missing hashes, impossible RGB, nonmonotone edges, wrong native state, and repeated GPU frames.

Two **real** NeXium guest sessions must show four distinct 1280×720 screenshots (two per source split) at different GPU clear-color phases with stable material profiles. Every source DDS SHA-256 is checked against fresh canonical generation *before and after guest execution*. Both native guest-created receipts, draw-sort `2,1,0` and exact alpha blend/depth per-pass state, must match. For each of 27 contiguous framebuffer pixels along its case-specific Y=440 scanline, the final verifier estimates alpha from a three-channel physically-valid straight-alpha RGB projection, rejects out-of-envelope and off-curve samples and nonmonotone jumps; it permits a sharp or gradual transition without claiming an unverified filtering mode. It requires each half-opacity crossing to be **within four screen pixels** of its independent predicted location and the two measured crossings to differ by **62±4 pixels**. The old rear-only (760,400) color must stay (21,202,219).

All generated assets are synthetic. **No PS3 original resources or user's PKG are included.** Host mock screenshot tests alone do not prove GPU behavior; this stage is Draft until exact-head CI and independently reviewed original NeXium artifacts pass. Neither stage proves texture filtering mode, physical Switch hardware or playable game.
