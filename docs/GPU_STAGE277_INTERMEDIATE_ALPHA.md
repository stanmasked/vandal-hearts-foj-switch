# Stage277 — Intermediate Per-Texel Alpha 64/192 on the Native GPU

Stage276 completed on its **exact-head 3/3 successful CI** and the original real NeXium ZIP evidence [#12341648728](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39590232869/artifacts/12341648728), showing alpha 0/128 masks swapped inside one invented DDS. Stage277 builds on the same verified NRO **without changing production code or shaders**, but now tests the interpolation of two *non-extreme* levels of alpha **64 and 192** in a single triangle.

## Exact synthetic-only inputs

Two fresh, private-runner-only SD roots each contain the public generated actor, three 64×64 RGBA8 DDS files and the existing public DKSH shaders. The violet near material (`material0.dds`) differs from the uniform-alpha-128 reference in **only 4,096 alpha bytes**, leaving all 16,384 RGB/RGBA pixel data layout and DDS metadata intact.

- `alpha-64-left`: for x=0..47, alpha 64; for x=48..63, alpha 192.
- `alpha-192-left`: the inverse; alpha 192 left, alpha 64 right.

All material RGB channels remain (96,72,201). The warm translucent middle layer remains (232,55,28,128), and the cyan opaque rear remains (21,202,219,255). All material geometry, draw ordering and GPU pass-state settings are fixed and identical to Stage276.

The independently computed CPU source-over result from the Stage266 model is:

| GPU framebuffer probe | Alpha 64 | Alpha 192 |
|---|---|---|
| Overlapping near/middle/rear triangle | RGB **(119,114,143)** | RGB **(104,86,182)** |

The actual NeXium 1280×720 framebuffer must swap these two colors between the left-overlap probe (605,400) and right-overlap probe (675,400), with tolerance no greater than **±8 per channel**, matching at least **75 of 81** pixels per 9×9 region. Real Stage275 and Stage276 GPU captures confirm both probe footprints are safely inside the near triangle and on opposite sides of the 0.75 UV boundary (U roughly 0.574–0.598 left and 0.784–0.808 right). The unchanged rear-only region at (760,400) must remain RGB (21,202,219) throughout.

## Native and NeXium proof

The Python host suite carries **12 Stage277 tests**, including real GCC/Clang compilation of the existing six-module C11 material+DDS decoder, checking every RGBA8 output byte of both new masks, refusing truncated DDS without modifying the output buffer, and synthetic-only evidence attack scenarios (fake uniform 128, missing hash, wrong sort and pass-state receipt, duplicate or swapped frames, refusal markers). The workflow also re-runs the 12 previously passing Stage276 tests and relevant earlier C11 sort/depth/alpha checks.

The dedicated Stage277 CI rebuilds the same Stage275 NRO and DKSH binaries using devkitA64 and attempts **two actual NeXium GPU guests**. Each guest:

1. Creates one new synthetic SD root and independently hashes and byte-verifies the invented near DDS *before execution*.
2. Captures two **real and distinct** 1280×720 GPU frames, requiring the appropriate color pair at both overlap probes and unchanged rear-only RGB.
3. Requires two exclusive, guest-authored native witnesses: `FOJ_NATIVE_SORT_V1 2,1,0` and `FOJ_NATIVE_ALPHA_PASS_V1 2:0:1:1 1:1:1:0 0:1:1:0`; forbids inconsistent rear-alpha or topology rejection.
4. After the guest, independently reads the source DDS again and requires its SHA-256 to be identical. The final auditor regenerates and validates both synthetic DDS digests itself, rather than trusting an input receipt.

**Stage277 is research only.** Unit-test synthetic screenshots cannot count as runtime proof. Do not claim this new alpha-64/192 effect until the exact-head real NeXium CI and archived artifact contents pass. No original PS3 assets are used. This does not demonstrate battle gameplay, user-specific textures or execution on a physical Nintendo Switch.
