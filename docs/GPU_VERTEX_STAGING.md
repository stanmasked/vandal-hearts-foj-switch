# Gate 2: FoJ original-mesh data path toward Nintendo Switch GPU rendering

**2026-10-16 — data preparation and shader source only. There is no
deko3d GPU-rendered NRO, no proven DKSH compiler result and no verified
physical Switch runtime from this gate.**

This gate builds on the original-data-capable ninth CPU NRO. It avoids
bypassing or duplicating the user's PS3 package: input goes through
the previously implemented private FOJRM001, BANIM and FOJMAT01 loaders.
No publisher asset data is committed to this repository.

## GPU API and shader toolchain

The relevant public Switch homebrew GPU library is
[devkitPro/deko3d](https://github.com/devkitPro/deko3d), a low-level API
for Switch's Tegra X1. Its shaders are **compiled ahead of time** to
DKSH binaries by [UAM](https://github.com/devkitPro/uam), not compiled
inside the NRO.

Experimental source-only shaders:
- [foj_actor.vert](../gpu/shaders/foj_actor.vert): clip-space position
  and UV inputs, locations 0 and 1;
- [foj_actor.frag](../gpu/shaders/foj_actor.frag): bind one user-local DDS
  atlas per material batch at binding 0, alpha cutout.

The optional `gpu/Makefile` invokes UAM and then the new
[DKSH format validator](../tools/validate_dksh.py), separately from
the nine existing research NRO builds:

```sh
make -f gpu/Makefile check-tool
make -f gpu/Makefile
```

This requires an actual installation of UAM; the current local workspace
does **not** have `uam`. Shader compilation and DKSH compatibility are
therefore **not claimed as tested**. Only generated fake DKSH files are
used to unit-test the validator's header, alignment and size checks.

## Portable CPU-to-GPU vertex staging

The new source is
[core/gpu_vertex_stream.c](../core/gpu_vertex_stream.c) and its
[header](../core/gpu_vertex_stream.h).

It accepts deformed original model XYZ+UV vertices, the existing
per-section atlas indices, an orthographic research camera, and the
destination image dimensions. It outputs:

- six float32 values per GPU vertex (NDC XYZW and atlas UV);
- ordered `first_vertex`, `vertex_count`, `texture_index` draw batches;
- an explicit summary of vertices, batches written and observed camera-space depth bounds.

Bounds: up to 20,000 triangle-soup vertices, 64 shape batches, 8 DDS
atlases, and at most a 2048×2048 viewport. It validates all shape
coverage, numeric coordinates, output buffer capacities and texture slots
**before modifying any caller buffers**.

**Depth normalization fixed:** deko3d's default depth clip range is
**[0,1]**. The former raw `cameraZ / extent` could produce negative depth
values and cause geometry to be clipped. The updated stream first scans
the entire model's camera-space Z bounds, then remaps all vertices to
**[0.01,0.99]**. Larger camera-space Z remains closer, consistent with
the CPU depth buffer. The eventual GPU state **must clear depth to 0 and
use comparison GREATER**, not the default LESS. A completely flat
equal-Z shape receives 0.5 depth.

This range is computed independently for one model and frame. It is
**not** appropriate for compositing multiple actors and terrain without
a shared camera near/far projection. The orthographic camera and original
PS3 handedness/material/shader conventions remain unverified. Actual
deko3d rasterization, texture upload and Switch display are still not
implemented. See [the deko3d device depth defaults](https://github.com/devkitPro/deko3d/blob/master/Primer.md).

## Tests and original-user-data compatibility

Synthetic C11 tests in
[tests/test_gpu_vertex_stream.c](../tests/test_gpu_vertex_stream.c)
check two material draws, bounded normalized Z, XY/UV projection, flipped texture V, missing
buffer capacity, invalid texture indices, NaNs and atomic no-write
rejection. Locally executed with:

```sh
cc -std=c11 -Wall -Wextra -Werror -pedantic -Icore \
  tests/test_gpu_vertex_stream.c core/gpu_vertex_stream.c -lm \
  -o /tmp/foj_gpu_stage
/tmp/foj_gpu_stage
```

Also run locally with AddressSanitizer/UndefinedBehaviorSanitizer: passed.
GitHub Actions has a matching new job, but **the recent GitHub Actions
runs have been failing before providing any job steps or logs**. Do not
interpret those statuses as positive or negative build verification of
this new module.

A local, read-only audit of the user's already-prepared authentic
`cape_daldren_stone.bmodel` FOJRM001+FOJMAT01 files verified:

| Metric | Actual observed |
| --- | ---: |
| Original mesh vertices converted | **9,066** |
| Original triangles | **3,022** |
| Original rig bones | **50** |
| Ordered GPU draw batches | **6** |
| DDS atlas slots used | **2** |
| Per-section texture indices | `0,0,0,1,0,0` |
| Packed GPU vertex bytes | **217,584** |
| Packed draw batch bytes | **72** |
| Finite projected vertices | **9,066/9,066** |

**2026-10-16 follow-up with the actual user-local Daldren mesh:** the
new depth-normalized staging was independently run on all **9,066**
original vertices and the same six draw batches. Original camera-space
Z spanned **−3.495997 to +2.875146** for yaw=0.35, pitch=0.15. Every
output Z was finite and within **0.01–0.99**, and the original section
texture indices `0,0,0,1,0,0` remained intact. A new aggregate-only
report `foj_daldren_gpu_depth_v2_audit.json` was produced in the user
conversation. This establishes **CPU geometry staging correctness**, not
deko3d driver, DKSH shader or physical GPU rendering.

No original vertex arrays, skeleton keyframes or DDS bytes were uploaded.
The user-local aggregate audit JSON lives in conversation artifacts, not
in this repository.

## Remaining steps for actual GPU rendering

1. Install and verify UAM in the devkitPro toolchain. Compile the two
   DKSH shaders and validate their module metadata.
2. Implement native deko3d device, queues, command buffers, swapchain,
   GPU vertex buffer upload and texture descriptors. It is not yet done.
3. Submit the six material draws for the already private Daldren example;
   bind distinct DDS textures without resetting depth between sections.
4. Align normalized depth range, origin, winding, alpha cutout and camera
   with the CPU reference, comparing screenshots and pixel checksums.
5. Validate the entire application on physical Switch hardware, including
   frame time, GPU/CPU memory and animation stability.
6. Preserve the separate unsolved problem of accurately reproducing the
   original PS3 bind pose, lighting and materials.

**This document describes real preparation toward GPU rendering, not a
completed native GPU implementation or a playable FoJ port.**
