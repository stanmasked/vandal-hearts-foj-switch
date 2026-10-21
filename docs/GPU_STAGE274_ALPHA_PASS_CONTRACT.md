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

## Exact six-module native C11 preflight integration

`tests/emulator/test_stage274_actual_native_chain.py` now compiles
**the actual production C files together** (not a Python reimplementation)
under both GCC and Clang:

1. `core/gpu_vertex_stream.c` projects the exact generated FOJRM
   vertex positions and UVs using the same camera as the NRO.
2. `core/gpu_draw_plan.c` validates material sections and draw ranges.
3. `gpu/transparency_sort.c` computes the ordered triangle indices.
4. `gpu/alpha_pass_contract.c` verifies matching texture/depth/blend
   descriptors and independently formats the exact native receipt.
5. `gpu/atlas_dds.c` decodes the generated opaque rear DDS image.
6. `gpu/alpha_material_contract.c` checks every decoded alpha byte.

This one host test checks the original and depth-swapped safe scenes,
plus a Stage271 reversed fixed-order case (which **is safely sortable**
dynamically), and requires crossing/coplanar negative cases to be
rejected without mutating the order output. It then changes one valid
rear DDS alpha byte to either 254 or zero and requires the native
opaque-material guard to refuse both.

This is a native code integration preflight, **not** a Nintendo Switch
NRO build, emulator frame, or physical-console result.

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

`tools/foj_stage274_nexium_pass_drive.sh` requires both the acceptance marker **and the rear-alpha refusal marker** to be
absent before launch, runs the actual Stage273 NeXium framebuffer
driver, and checks and preserves both the native sort receipt and the
new exact native material/depth receipt. The same driver also requires the rear-alpha rejection witness to remain
**absent after a successful positive guest**. A test that emits both a
valid GPU pass-state receipt and a translucent rear-material rejection
is contradictory and must fail, even if four rendered RGB frames look
correct.

The final independent
`tools/foj_stage274_pass_contract_check.py` first validates all four
actual GPU screenshots via the Stage273 RGB oracle, then requires
both Stage274 native receipts. Host-synthesized image/marker unit
fixtures **are not evidence of real NeXium execution**.

## Verify the actual guest input before and after execution

The negative guest driver now executes
`tools/foj_stage274_rear_dds_witness.py` **twice**: before launching
NeXium and after observing the NRO-authored pre-GPU rejection. Both
measure the actual local `material2.dds` file byte for byte against a
freshly rebuilt generated-only reference and save an exclusive,
phase-tagged `rear-dds-before.json` / `rear-dds-after.json` in the
archived CI artifact. An altered input file aborts the driver.

The final independent verifier checks the exact contents of both
observations, their phase labels, 16,512-byte size, SHA-256 digests,
and the single alpha mutation at offset 131. It rejects absent or
tampered receipts. Three more synthetic-only classifier regressions
cover missing post-guest evidence, a fabricated post-guest digest,
and swapped phase labels.

These observations verify the test input's identity at two points,
**not** GPU behavior or continuous immutability during execution.
The separate native NRO rejection marker and real NeXium CI job
remain mandatory.

## Cryptographic identity of the negative synthetic DDS

The third NeXium guest now records **both** the pristine and modified
generated rear-DDS SHA-256 digests in its synthetic manifest. Before
opening NeXium, its shell driver independently rebuilds the public
64×64 RGBA8 DDS, flips **only** alpha byte at offset 131 (255→254),
and refuses any actual DDS payload that differs from this exact
expected file. Both manifest hashes must match that reconstruction.

The final Stage274 evidence auditor independently recomputes the
original/modified SHA-256 values from the public generator and checks
the preserved manifest. Two additional synthetic-only classifier
regressions reject missing or fabricated hashes. This establishes
which generated DDS bytes are prescribed to the real guest without
publishing any PS3 resources. The **real guest execution and refusal**
still require the third NeXium CI job; a hash or mock fixture alone
does not establish that result.

## Third NeXium guest: single rear DDS alpha-byte refusal

The Stage274-only research NRO now exclusively writes
`foj-native-rear-alpha-reject.txt` with the exact line
`FOJ_NATIVE_REAR_ALPHA_REJECT_V1 pre_gpu=1` if decoded material 2
contains *any* nonopaque texel. It returns before GPU initialization,
and neither the ordinary native sort marker nor the Stage274 pass
marker is written.

`tools/foj_stage274_negative_rear_alpha_sd.py` creates a **fresh**
generated-only SD root with exactly one byte changed from 255 to 254
in the 64×64 rear DDS texture. The other actor, materials and shader
assets remain unchanged. It never loads private resources.

A **third independent real NeXium guest** now runs this invalid case.
The dedicated shell driver requires all native markers to be absent
before launch, observes the exact guest-created refusal marker,
requires both positive-render markers and the GPU boot journal to
remain absent, and saves a log and refusal receipt. The final
independent evidence checker validates the negative generator receipt,
exact refusal bytes and guest log in addition to all four RGB frames
from the two valid guest scenes.

Mock evidence tests only check the classifier and rejection of missing,
tampered and forged refusal markers. They do not establish that the
actual NRO was executed in NeXium.

## Independent evidence contradiction audit

In addition to the NeXium guest launch scripts, the final
`foj_stage274_pass_contract_check.py` **independently rejects**
contradictory artifact contents. Each positive scene must contain its
real framebuffer RGB frames and expected native alpha-pass receipt,
but **must not** contain a native rear-alpha rejection receipt. The
single-byte rear-alpha negative scene must contain its exclusive
pre-GPU rejection receipt, but **must not** carry a native successful
sort receipt, successful GPU pass-state receipt, screenshots or a
`foj-boot-*.txt` journal. File and symlink cases both fail closed.

Four synthetic-only classifier regressions verify the independent
rejection rules for contradictory positive refusal, unexpected native
negative sort success, unexpected negative screenshot and unexpected
negative boot journal. Those host tests demonstrate fail-closed audit
logic only; they never claim that NeXium executed the synthesized data.

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
