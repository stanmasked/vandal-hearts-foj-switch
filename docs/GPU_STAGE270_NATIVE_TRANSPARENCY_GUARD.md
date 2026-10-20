# Stage270 — Native GPU transparency fail-closed preflight

Stage270 is an **opt-in, separate research Nintendo Switch NRO** that
enforces the Stage268/269 safety condition on the *actual deko3d input
vertex stream*, not just the Python fixture source.

## Native integration

Build on devkitA64:

```sh
make -f gpu/native_alpha_guard.mk verify
# build/foj-deko3d-native-alpha-guard-proof.nro
```

`FOJ_GPU_NATIVE_ALPHA_ORDER_GUARD` is **defined only for this NRO**.
No existing Stage265/Stage267 NRO is overwritten or changes its binary.
Immediately after the fail-closed private FOJRM/FOJMAT/3×DDS loader
has validated and projected the actor (and **before creating a deko3d
device**, allocating GPU memory, or submitting any draw list), the
NRO calls `foj_three_layer_preflight` on the same
`private_payload.vertices` and `private_payload.batches` later
used for GPU upload.

If the geometry is invalid or transparent depth ordering is unsafe,
the NRO frees the private payload and returns **exit code 8**.
Only a validated scene continues to shader loading and GPU drawing.

## Guard contract

The initial limit is deliberately narrow, matching Stage267 exactly:

- Three contiguous draw ranges of **three vertices each**, material
  indices 0 / 1 / 2, and exactly nine vertices;
- Finite clip-space XYZ in XY [-1,1] and Z [0,1] with **W exactly 1**;
  no degenerate projected triangles;
- Near material 0, middle material 1, opaque rear material 2;
- True convex projected triangle overlap found by clipping. On all
  vertices of every positive-area overlap region, the nearer triangle
  must have strictly **greater Z**, with a conservative tolerance.
  Coplanar, crossing, or reversed relationships are rejected.
  Triangles that do not overlap in screen space need no constraint.

Because depth difference is affine under the current orthographic
projection with constant W, checking each vertex of the clipped
overlap polygon proves the fixed ordering for that overlap region.

The C11 safety guard is free of Nintendo SDK dependencies. CI compiles
it with GCC and Clang, both normal and NDEBUG, and checks positive,
crossing, reversed, coplanar, near-equal, malformed and winding cases.
An independent real devkitA64 build compiles the actual guarded NRO.
The companion NeXium job uses the Stage269 **guarded generated-scene
installer** and compares six real framebuffer captures with the
Stage267 source-over oracle.

## Known limits

This is **not** a general transparencies solution, perspective
triangulation, depth peeling or OIT. It does not guarantee equivalence
to original PlayStation 3 rendering, nor does it show real game assets.
For intersecting triangles a future compositor must actually split
geometry or use an appropriate per-pixel method. This stage correctly
**refuses** unsafe cases rather than presenting invalid blended output.

The existing Stage267 proof remains intact; new native guard success
requires its separate GitHub Actions workflow on this exact PR head.
