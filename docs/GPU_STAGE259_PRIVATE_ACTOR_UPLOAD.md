# Stage259 — user-local actor GPU vertex and DDS upload

Stage258 only validated four private files then discarded the data.
Stage259 adds a **separate opt-in** experimental Nintendo Switch NRO:

```sh
make -f gpu/private_draw.mk verify
# build/foj-deko3d-private-actor-upload.nro
```

It requires a complete *user-owned* local SD set, in the same four fixed
paths as Stage258 (`actor.fojrm`, `actor.fojmat`, `material0.dds`,
`material1.dds` in `sdmc:/switch/foj/gpu/`). No game binaries or source
assets are embedded in the NRO or uploaded to GitHub.

## Changes

- `foj_gpu_private_bundle_load` retains GPU-ready bind/static-pose
  `FojGpuVertex` and ordered `FojGpuBatch` arrays, plus the two
  independently verified DDS level-0 RGBA buffers. It returns no raw
  FOJRM/FOJMAT/DDS source bytes or private paths in its public report.
- On any invalid/missing input all temporary allocations are freed,
  outputs remain unchanged, and private-mode launch refuses to fall
  back silently to the generated scene.
- At runtime, the Stage259 opt-in NRO copies these private projected
  vertices into its CPU-visible deko3d vertex memory block, uses their
  own validated batch ranges for ordered draw commands, stages both
  decoded DDS images into the two texture descriptors, and releases
  source buffers **only after the GPU queue is idle and destroyed**.
- Ordinary GPU synthetic NRO, shader-free GPU NRO and CPU research
  targets remain independent and keep generated geometry behavior.

## Limits and evidence required

The model is still a **static bind-pose**, generated from FOJRM001 /
FOJMAT01 *research interchange containers*, not raw PS3 file parsing.
Only exactly two material/atlas slots are accepted by this first GPU
research renderer. The existing shader, orthographic projection, clip
depth setup and DDS sampler are still experimental, not original FoJ
render-state replication. Original animations, PS3-style transparency,
depth/culling, battle logic and gameplay are not included.

A successful devkitA64 build proves compiler/toolchain compatibility
but **does not prove rendered pixel output**. CI can use only invented
FOJRM001/FOJMAT01/classic DDS test files. Original FoJ resources never
leave the user's private SD or local machine. Before declaring that
the original character has truly appeared on Switch, separately
capture and inspect GPU frames in NeXium/real hardware using
authorized, private resources, and compare camera/material/UV/depth
behavior to user-owned PS3 captures.

The host fixture checks retained vertex content, 2 material-batch
sections, exact DDS bytes, output-ownership safety, missing source,
symlink rejection and cleanup under GCC/Clang, NDEBUG, ASan and UBSan.
