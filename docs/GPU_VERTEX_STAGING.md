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

The optional `gpu/Makefile` invokes UAM, separately from the nine
existing research NRO builds:

```sh
make -f gpu/Makefile check-tool
make -f gpu/Makefile
```

This requires an actual installation of UAM; the current local workspace
does **not** have `uam`. Shader compilation and DKSH compatibility are
therefore **not claimed as tested**.

## Portable CPU-to-GPU vertex staging

The new source is
[core/gpu_vertex_stream.c](../core/gpu_vertex_stream.c) and its
[header](../core/gpu_vertex_stream.h).

It accepts deformed original model XYZ+UV vertices, the existing
per-section atlas indices, an orthographic research camera, and the
destination image dimensions. It outputs:

- six float32 values per GPU vertex (NDC XYZW and atlas UV);
- ordered `first_vertex`, `vertex_count`, `texture_index` draw batches;
- an explicit summary of vertices and batches written.

Bounds: up to 20,000 triangle-soup vertices, 64 shape batches, 8 DDS
atlases, and at most a 2048×2048 viewport. It validates all shape
coverage, numeric coordinates, output buffer capacities and texture slots
**before modifying any caller buffers**.

**Coordinate warning:** output position projection intentionally matches
the current **experimental orthographic CPU renderer**, not the original
PS3 projection. GPU depth-range and handedness conventions are not yet
calibrated: deko3d depth configuration, shader compilation, texture
creation, command submission and display must be implemented and tested
before declaring the stream render-ready.

## Tests and original-user-data compatibility

Synthetic C11 tests in
[tests/test_gpu_vertex_stream.c](../tests/test_gpu_vertex_stream.c)
check two material draws, XY/UV projection, flipped texture V, missing
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
