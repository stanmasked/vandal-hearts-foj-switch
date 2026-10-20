# Stage274 — bind dynamic sorting to actual texture/blend/depth GPU states

Stacked on Stage273, whose own exact-head native NRO + NeXium workflow
must pass independently. Stage272's CPU planner has 5/5 CI successful
and Stage271's unsafe guest cases are independently successful.

## Scope

The separate experimental opt-in
`gpu/alpha_pass_contract.mk` builds
`foj-deko3d-alpha-pass-contract-proof.nro`. It preserves the existing
Stage270 and Stage273 build entrypoints unchanged.

Stage273 already computes a safe dynamic triangle sequence on the real
projected actor vertices, requires canonical three draw sections and
opaque rear material 2, and rejects ambiguous geometry.

Stage274 adds `gpu/alpha_pass_contract.c`, an independent portable
C11 **material/depth pass contract**. Before recording any draw
commands, it checks that exactly three contiguous three-vertex
sections map one-to-one to texture IDs 0, 1, and 2. The computed index
order must be a complete permutation of 0,1,2 with **opaque material 2
first**.

The contract emits exactly three ordered, immutable pass descriptors:
`first_vertex`, `vertex_count`, `material_index`,
`blend_enabled`, `depth_test_enabled`, `depth_write_enabled`.

For the rear pass only: `blend_enabled=0`,
`depth_test_enabled=1`, `depth_write_enabled=1`.
For both subsequent translucent passes: `blend_enabled=1`,
`depth_test_enabled=1`, `depth_write_enabled=0`.

All failures leave the caller's output buffer unchanged. It refuses
invalid/deduplicated orders, wrong material mappings, mismatched vertex
ranges, and an opaque rear scheduled after a translucent pass. The
Stage273 decoded-DDS all-alpha-255 rear check remains required.

## Native GPU integration

With `FOJ_GPU_DYNAMIC_PASS_CONTRACT=1` *only* in Stage274's isolated
NRO target, the deko3d path consumes the checked descriptors when
binding textures, setting blend state, configuring depth-test/write,
and issuing actual GPU draw calls. Before consuming a descriptor, the
corresponding validated research draw range must still match its
texture index and vertex range.

The prior constant-order Stage270 NRO and dynamic Stage273 NRO are
**not** recompiled or behaviorally altered by these opt-in changes.

## Guest-native binding of GPU pass states to real framebuffer evidence

Stage273 independently records the **triangle ordering** it calculated
and confirms two separate NeXium scenes have the expected source-over
RGB. Stage274 now also records, after constructing the validated C11
pass plan, the exact **texture ID, blend enable, depth-test enable,
and depth-write enable** for all three passes:

```text
FOJ_NATIVE_ALPHA_PASS_V1 2:0:1:1 1:1:1:0 0:1:1:0
FOJ_NATIVE_ALPHA_PASS_V1 2:0:1:1 0:1:1:0 1:1:1:0
```

Exactly one of these lines, terminated by a newline, is written per
native guest to `sdmc:/switch/foj/gpu/foj-native-alpha-pass.txt`.
The file is created exclusively; an existing file/symlink or a failed
flush causes the opt-in NRO to abort rather than falsely attest pass
states. This recording happens **before GPU draw command lists are
recorded** and reveals no original game data.

`tools/foj_stage274_nexium_pass_drive.sh` requires the marker to be
absent before launch, runs the actual Stage273 NeXium framebuffer
driver, and checks and preserves both the native sort receipt and the
new exact native material/depth receipt. The final independent
`tools/foj_stage274_pass_contract_check.py` first validates all four
actual GPU screenshots via the Stage273 RGB oracle, then requires
both Stage274 native receipts. Host-synthesized image/marker unit
fixtures **are not evidence of real NeXium execution**.

## Test plan

- GCC and Clang, ordinary C11 and NDEBUG: host contract unit cases for
  valid `[2,1,0]` and `[2,0,1]`, precise texture IDs, both state
  transitions, and rejection of aliases, duplicates and malformed
  metadata without output mutation.
- Preserve Stage272 native DAG and Stage273 exact native projection,
  DDS and screenshot-classifier host tests.
- Real devkitA64/UAM NRO build and validation.
- Real NeXium runs in **two fresh separate generated-only SD roots**,
  with the same RGB predictions and exclusive native index-order
  markers as Stage273. The already independent screenshot checker
  requires four real frames, correct different source-over alpha
  pixels, correct rear-only material and changed clear-color phases.

This is three generated triangles and three materials **only**, not
64-material GPU rendering, arbitrary original PS3 actor content,
cyclic transparency OIT, physical Switch certification, or a playable
port. Stage274 is not confirmed until its *own* exact-head CI succeeds.
