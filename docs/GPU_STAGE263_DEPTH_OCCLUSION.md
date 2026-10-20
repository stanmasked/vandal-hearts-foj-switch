# Stage263 — true deko3d depth target + independent NeXium occlusion test

Stage260–262 proved generated-only color visibility, projected geometry and
DDS UV mapping in NeXium. They did **NOT** prove depth testing. The existing
research draw path bound **only color targets**, with no GPU depth attachment.
The Stage263 change explicitly addresses that missing functionality.

## Isolated native build

```sh
make -f gpu/depth_draw.mk verify
# build/foj-deko3d-depth-occlusion-proof.nro
```

This is a **separate opt-in NRO** using the same validated local-only
FOJRM001 / FOJMAT01 / dual-DDS path as the Stage259 actor renderer.
Its new `FOJ_GPU_DEPTH_PROOF` compile flag (which requires private
actor input) creates **one Z24S8 depth image per swapchain slot**,
each as a render-only GPU image with separately owned image memory.
Both pre-recorded frame phases bind the matching depth view and clear
depth to **0.0 each time**; rasterization enables depth test and
writes with **DkCompareOp_Greater**, matching our clip-depth mapping in
`foj_gpu_prepare_stream` (nearer camera +Z means larger GPU depth).

The normal GPU clear-only, Stage259 private actor and Stage262 UV NRO
targets remain unchanged and still have **no new depth behavior**.
Depth buffers are released on all GPU cleanup paths, after GPU idle.

## Two adversarial generated-only actors, four actual guest captures

The Python generator reuses our own FOJRM001 / FOJMAT01 format and
64×64 classic RGBA8 **invented** solid-color DDS textures. It makes
two partially overlapping triangles, drawn in fixed material order:

- Batch 0 / warm first, batch 1 / cool second
- Triangle coordinates overlap around `(640,400)` on a 1280×720 frame
- Scenario A: warm first is **near**, cool second is **far**
- Scenario B: warm first is **far**, cool second is **near**

Since both materials are opaque and the same geometry order is used in
both runs, **simple overpainting without a functioning GPU depth buffer
must fail scenario A**. A correct real GPU depth test shows warm at the
overlap in scenario A and cool there in B.

The independent checker also requires the exposed warm wing around
`(520,380)` and the cool wing around `(760,400)` in **both** runs,
to reject all-red, all-cyan, missing material or blank screen. It
tests 121 interior samples at each of three predetermined probe
positions and requires at least 85 correct pixels with no more than
five opposite-color pixels. It takes two nonduplicate, alternating
background snapshots per scenario — **four actual guest PNGs**, not
fabricated reference images.

The native workflow also runs generated-only host negative tests.
Those test images simulate depth/no-depth raster cases solely to
validate the classifier; they never count as emulator proof.

## Evidence constraints

No original PS3 meshes, textures, packages, binaries or user SD files
are accepted by public GitHub Actions. Build and test artifacts contain
only generated data and independently captured NeXium images.

A successful Stage263 proves **only** generated static two-triangle
depth occlusion under NeXium. It does **not** verify original FoJ
character animation or bone poses, real game depth convention,
transparent geometry ordering, alpha cutout, physical Switch GPU
behavior, battle logic, or a playable game. Testing those requires
a separate user-local/private workflow, never original assets in a
public repository.

This research stage must not be merged until both real NeXium
scenario A and B captures verify depth visibility, and the existing
Stage262 GPU UV and research regressions remain green.
