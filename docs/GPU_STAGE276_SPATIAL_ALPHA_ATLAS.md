# Stage276 — Real NeXium Proof of Spatial DDS Alpha

This research stage is stacked on the exact-head [Stage275 success](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39559816015) (19/19 green, five real NeXium guests). **Stage275 native C11/deko3d NRO and shaders are rebuilt unchanged**: no production GPU or original PS3 assets are modified in this experiment.

## Why this test is different

Stages 266–275 use mostly uniform 128-alpha generated RGBA8 textures. Stage276 tests whether alpha varies *inside one atlas*, at distinct locations on the **same triangle**. A uniform-texture rendering bug could pass previous source-over checks but must fail this test.

Two fresh generated-only 64×64 RGBA8 DDS files are created by changing **only alpha channel bytes** of the public violet near material 0, with a vertical step at texel coordinate `x = 48`:

- `alpha-left-clear`: texels with U<0.75 have alpha 0; right-side texels retain alpha 128.
- `alpha-right-clear`: right-side texels have alpha 0; left-side texels retain alpha 128.

RGB bytes, DDS headers, all other material atlases, native three-triangle geometry, DKSH shaders and the required draw order `2,1,0` are held constant. No original PS3 image or PKG is read or published. Every SD root must not pre-exist.

## Independent RGB oracle and 4 real frames

The Python CPU oracle computes expected straight-alpha source-over RGB using the existing Stage266 compositing math, with the opaque cyan rear and half-alpha warm middle retained:

| Probe, row 400 | Material 0 alpha=0 | Material 0 alpha=128 |
|---|---|---|
| Near + middle + rear overlap | (127,128,123) | (111,100,162) |

The two spaced overlap probes are at `(605,400)` and `(675,400)`. The projection regression confirms interpolated U coordinates of approximately **0.586** and **0.796** at those centers, with full 9×9-footprint U ranges of **0.574–0.598** and **0.784–0.808**, safely on opposite sides of the 0.75 alpha transition. All **81/81 pixels** at both new probes were independently confirmed to be stable material-overlap pixels in each of the four original **real Stage275 NeXium frames** from [artifact #12328905770](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39559816015/artifacts/12328905770). Those prior frames validate probe placement but do **not** substitute for new Stage276 runtime evidence. The first should switch from alpha 0 to alpha 128 as the generated cases are reversed; the second should switch in the opposite direction. The rear-only probe at `(760,400)` must remain `(21,202,219)`. At each point a 9×9-pixel footprint is tested (at least 75/81 within ±8 RGB channels) to guard against antialiasing/edge artifacts.

Each real NeXium case must present two distinct 1280×720 frames, changing GPU clear-color background while preserving exact material footprint. A static screenshot or synthesized screenshot cannot prove this. The target NRO must write exact `FOJ_NATIVE_SORT_V1 2,1,0` and `FOJ_NATIVE_ALPHA_PASS_V1 2:0:1:1 1:1:1:0 0:1:1:0` receipts. A rear-alpha/topology refusal or other contradiction fails the audit.

Host script `foj_stage276_nexium_spatial_alpha_drive.sh` checks the actual DDS against the public generator **before and after** each guest run, records two SHA-256 snapshots, requires the native receipts and captures both frames. The independent final `foj_stage276_spatial_alpha_check.py` reproduces the alpha mask and composite colors instead of trusting the manifest alone. Host classifier regressions exercise forged witnesses, swapped cases, constant alpha and duplicate frames, but **never count as guest proof**.

## CI gate and limitations

The dedicated [Stage276 workflow](../.github/workflows/stage276-spatial-alpha-atlas.yml) builds the existing Stage275 deko3d research NRO on devkitA64, runs the existing native C11 tests and **12 Stage276 host tests**, including actual GCC/Clang compilation of the production DDS decoder, exhaustive 64×64 per-texel RGBA8 byte-parity checks, truncated-DDS failure without output modification, and synthetic-only screenshot classifiers; it then requires the two real generated-only NeXium sessions with four captured frames and both before/after DDS identities. Stage276 will remain Draft until exact-head dedicated CI passes and its actual artifact ZIPs are independently reviewed.

This tests static single-material per-texel alpha and straight-alpha blending only. It does not establish PS3 material semantics, animations, battle gameplay, physical Switch behavior, or compatibility with arbitrary DDS variants.
