# Stage278 — Four-Band Alpha Staircase, Native GPU Research

**Base:** The exact-head [Stage277 CI](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39593452848) passed 3/3 jobs, including actual NeXium GPU renders of alpha 64 and 192. Stage278 keeps the **identical proven 315,448-byte Switch NRO and two DKSH shaders**; production GPU code and previously accepted Stage275–277 branches remain unchanged.

## A new graphics invariant

A single invented 64×64 RGBA8 violet near-material DDS carries **four distinct alpha values at the same time**, not two. The public generated-only actor, its other two DDS materials, camera, geometric sort order and blending/depth settings stay fixed. The four alpha bands have texel X ranges:

| DDS X positions | 0–39 | 40–43 | 44–48 | 49–63 |
|---|---:|---:|---:|---:|
| `staircase-ascending` | 0 | 64 | 128 | 255 |
| `staircase-descending` | 255 | 128 | 64 | 0 |

Alpha changes only; all DDS headers, RGB channels and geometry stay intact. The RGBA8 reference texture is violet with uniform alpha 128. Therefore the unchanged 128-level band must not count as modified bytes. The generator validates an exact alpha-only byte-difference census, and the native C11 decoder is tested on *every* RGBA8 output byte in both examples.

## Four spatial probes in actual GPU pixels

Four selected stable points in the real 1280×720 NeXium scene test the four bands independently:

| Label | Framebuffer pixel | Approximate U | Alpha of ascending case | Independent CPU source-over RGB |
|---|---|---|---:|---|
| Band 0 | (605,400) | 0.586 | 0 | (127,128,123) |
| Band 1 | (630,400) | 0.661 | 64 | (119,114,143) |
| Band 2 | (651,400) | 0.724 | 128 | (111,100,162) |
| Band 3 | (675,400) | 0.796 | 255 | (96,72,201) |

In the descending case the *corresponding RGBs reverse*. An additional rear-only probe (760,400) must stay (21,202,219). Source-over RGB comes from the public Stage266 compositing model, with the same half-alpha warm middle and opaque cyan rear layers.

Each probe uses a 9×9-pixel region with at least 75 of its 81 pixels within ±8 RGB per channel. A new host geometry test asserts **all 81 UVs** lie safely inside the assigned alpha band, including two narrow stripes. Actual Stage277 NeXium artifact [#12342074412](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39593452848/artifacts/12342074412) was independently audited and all four proposed locations are stable material-overlap regions in its four captured frames.

## Fail-closed real guest gate

[Stage278 CI](../.github/workflows/stage278-four-band-alpha.yml) builds the known-good Stage275/277 research NRO under devkitA64 and reruns C11/GCC/Clang sort, material, depth, DDS and inherited Stage276/277 tests. Twelve new Stage278 host test methods verify alpha-only texture construction, four expected colors, native C11 DDS parity, truncated-DDS rejection without caller buffer modification and evidence tamper rejection.

Two actual NeXium guests must independently create the ascending and descending generated-only SD roots. Each must produce two **genuine** and **different** 1280×720 GPU frames; match all five RGB probes; preserve the native GPU sort and depth/blend-state receipts; and fail if any contradictory refusal appears. A byte-exact comparison and SHA-256 of the public near DDS occurs before and after each guest, and the independent evidence verifier recomputes those digests instead of trusting the manifest.

**Status:** Research Draft until the *exact-head* CI and original artifact ZIPs are independently verified. Synthetic screenshot tests cannot establish guest execution. This does not test bilinear filtering *at the band boundaries*: intentionally, these probes are inside constant-alpha bands to isolate correct per-texel sampling. Border filtering and transitions require a separate experiment. No original PS3 textures, PKG, game content or personal data are included; the result cannot establish full gameplay or physical Switch behavior.
