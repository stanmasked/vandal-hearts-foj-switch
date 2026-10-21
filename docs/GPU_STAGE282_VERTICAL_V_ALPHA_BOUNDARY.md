# GPU Stage282 — Vertical DDS V-coordinate alpha boundary displacement

**Stacked on:** [Stage281 PR #166](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/166), exact-head [3/3 NeXium CI #39603858489](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39603858489) at `bb6d8911617ed7b3febc75a65a8cb6e87b391bf3`.

Stages280–281 demonstrated U-driven horizontal alpha-edge relocation and the same transition on five adjacent screen rows. Stage282 changes the **source DDS V position** of the split while freezing the 315,448-byte NRO, 512-byte DKSH shaders, nine vertices, XY/UV/Z, camera, native draw sort, pass blend/depth contracts, middle/rear material and RGB values.

## Independent vertical projection and masks

The prediction is derived from the frozen native C11 `foj_gpu_prepare_stream` projection. With a 1280×720 framebuffer, `extent=2`, and camera zoom 1, `ny=.84`; the near-triangle vertices are at world Y=0.69 with UV V=0 and Y=-0.50 with V=1. The native framebuffer coordinates are Y=151.344 at V=0 and Y=511.200 at V=1, so split 40 predicts **Y=376.254** and split 52 **Y=443.727** in the native framebuffer. The actual Stage281 NeXium artifact shows the guest viewport scaled inside the captured 1280×720 window: its game viewport occupies rows **0–693** (694 pixels), with the emulator toolbar starting at row 694. Therefore the screen capture maps native Y to `Y_capture=Y_native*(694/720)`: split 40 predicts Y=**362.667** (target pixel 363), split 52 predicts Y=**427.704** (target pixel 428), about **65.04 pixels apart**. The auditor intentionally checks the captured-window coordinates, not unscaled native framebuffer coordinates. This projection does not assume a sampler mode.

Both generated-only `64×64 RGBA8 DDS` inputs change exactly **4096 alpha bytes** relative to the canonical violet-alpha128 DDS, and **zero header/RGB bytes**:

| New case | Alpha when DDS y is above split | Alpha at/under split | Expected screen crossing |
|---|---|---|---|
| `edge-v40` | 0 | 255 | Y≈363 |
| `edge-v52` | 0 | 255 | Y≈428 |

Only generated `material0.dds` is modified between cases. No PS3 resources, game PKG or original game files are loaded or published. Independently check exact SHA-256 of each full DDS before and after guest.

## Evidence and negative controls

For two real NeXium guest instances/four original RGB frames, check **three X columns 624,630,636**, each with **27 contiguous Y samples**, thus **324 measured framebuffer pixels** over all four images. Control regions around the upper/lower alpha endpoints and the rear-only RGB location must retain expected compositing. For every column:

- Three-channel projection onto the physically possible straight-alpha RGB trajectory, including out-of-envelope/off-curve rejection.
- Monotone clear-top to opaque-bottom progression, allowing both step and filtered transitions **without claiming which sampler mode is configured**.
- Expected half-opacity crossing Y±5; crossings agree across all three columns (range ≤4).
- Y displacement from the 12-texel V shift must be **65±6 pixels** for each sampled column. An unchanged screen-space edge must fail.
- Both frames of a given input mask must retain exactly the same material profiles; genuine background clear phases must differ.

Retain the guest-generated precise sort receipt `2,1,0` and exact blend/depth pass receipt, forbid contradictory GPU refusal markers, and reject duplicate screenshots or mutated source input. Mock Pillow PNGs exercise the **14 new host regressions** but **do not establish GPU execution**.

## CI plan / acceptance

[Dedicated workflow](../.github/workflows/stage282-vertical-boundary.yml) runs inherited native GCC/Clang C11 checks, Stage276–281 tests plus Stage282 host cases, compiles same Stage275 NRO/DKSH with devkitA64, and launches actual NeXium/Vulkan guests to produce four fresh screenshots and one independent `foj.stage282.real_native_vertical_v_edge.v1` receipt.

**Status: Draft until exact-head three-job CI and independent original GitHub ZIP verification.** No assertion about original PS3 DDS textures, arbitrary texture filtering, physical Nintendo Switch execution or playable FOJ port.
