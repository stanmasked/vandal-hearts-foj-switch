# Stage273 — real GPU dynamic alpha order on generated three-layer actor

Stage270 confirmed the fixed three-layer positive path on a real
devkitA64 NRO and six NeXium framebuffer captures.
Stage271 is the separate unsafe-scene rejection test, while Stage272
introduces a portable CPU topo-sort for 1..64 translucent triangles.

**Stage273 is a new, separate opt-in NRO**, not an edit to Stage267 or
Stage270's already verified NRO binaries.

## Build

```bash
make -f gpu/dynamic_alpha_sort.mk verify
# build/foj-deko3d-dynamic-alpha-sort-proof.nro
```

Only this makefile defines `FOJ_GPU_DYNAMIC_ALPHA_SORT`. The new
C11 source `gpu/transparency_sort.c` is linked into that NRO.
`FOJ_GPU_NATIVE_ALPHA_ORDER_GUARD` is intentionally **absent** from
this target: Stage270's fixed-order guard would reject the second
valid scene even though the Stage272 planner can safely reorder it.

After the existing validated private FOJRM/FOJMAT/3 DDS intake and
orthographic projection — but **before** creating a GPU device — the
NRO calls `foj_alpha_sort_back_to_front` on the same actor GPU
vertex positions later uploaded to deko3d.

The initial integration is narrow: exactly three 3-vertex draw ranges
with canonical materials `violet(0)`, `warm(1)`, `cool(2)`.
Any malformed shape, numerical ambiguity, crossing or cycle fails
closed with code 8. The calculated first draw **must** be material
`cool(2)`, the only opaque rear. Before any GPU initialization,
`foj_gpu_opaque_rear_atlas` also checks **every decoded RGBA8 alpha
byte in material 2 is 255**, with strict texture dimension and length
bounds. Any single translucent rear texel is rejected with exit 8:
the sorter must never write an assumed-opaque depth buffer for
transparent source pixels. This preserves depth-write and
straight-alpha state transitions. The two translucent materials may
be reordered safely as `violet, warm` or `warm, violet`.

The GPU command buffer uses the actual dynamic pass indices — unlike
Stage272's CPU-only planner — to select the material, vertex range,
blend enable and depth-write behavior.

## Two synthetic real-GPU scenarios

Both share exactly the same XY triangles and RGBA8 DDS color/alpha
texture bytes. The difference is **only six Z float values** in
`actor.fojrm`:

| Case | GPU material order (back to front) | Expected overlap RGB |
|---|---|---|
| `original` | cool → warm → violet | (111,100,162) |
| `reversed` | cool → violet → warm | (146,96,119) |

The expected pixels are computed independently from Stage266's
straight-alpha RGB reference model, not from a claimed GPU snapshot.

CI compiles the C11 topo-sort and **strict opaque-atlas guard** under
GCC/Clang (with and without NDEBUG), checks randomized C/Python reference
parity, builds the actual NRO with devkitA64/UAM, and starts
**two independent real NeXium guests**, each with its own new
synthetic SD root. For each guest it requires two distinct framebuffer
captures with independently changed clear colors. The checker verifies
the predicted overlap RGB within 8 levels over 116/121 pixels in
each probe and checks the rear-only material footprint. Four real
frames are required, with different blended overlap signatures.

## Safety and non-goals

- No original FoJ PS3 models, packages, textures, sound, private files,
  personally identifiable inputs or proprietary game content in CI.
- No output is considered verified merely because a host Python test
  constructs a matching image. Real NeXium guest checks must succeed.
- **Not** general order-independent transparency (OIT), geometry
  splitting, animated actor meshes or perspective-correct Z.
- 64-triangle CPU sorting does not mean this NRO renders 64 separate
  translucent draw ranges. The GPU integration deliberately remains
  exactly three materials / three triangles until proven otherwise.
- A successful guest test validates only these two synthetic
  orthographic scenes, not real gameplay or physical Switch hardware.

Keep the stacked PR Draft until its own exact-head devkitA64 and
NeXium evidence is complete.
