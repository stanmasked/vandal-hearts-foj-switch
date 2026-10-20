# Stage257 — private FOJRM001 + FOJMAT01 to GPU stream

## New portable bridge

`gpu/private_actor_bridge.{h,c}` connects the **existing validated**
user-local interchange parsers `core/rigmesh_io.c` (FOJRM001)
and `core/material_table.c` (FOJMAT01) to the established
`foj_gpu_prepare_stream` and Stage256 `foj_gpu_actor_upload_plan`.

The call accepts **private byte buffers supplied by the caller**,
not built-in PS3 assets. It parses them into temporary owned allocations,
requires exact geometry-section to material-section correspondence,
validates all material slots and ordered triangle ranges, projects static
mesh XYZ/UV to `FojGpuVertex`, then returns contiguous `FojGpuBatch`
records and an aligned GPU vertex allocation plan.

On rejection, vertex outputs, batch outputs and plan are unchanged.
Parsed arrays and temporary projection vertices are freed on every path.
Maximum private FOJRM input is 2,000,000 bytes; material table is limited
to 64 sections/8 texture slots. GPU stream is at most 20,000 vertices.
Do not call this on unbounded raw PS3 containers: FOJRM001/FOJMAT01
are **private research interchange formats**, not original formats.

**Current limitation:** only original bind/static XYZ and UV fields
are prepared; this does not apply sampled BANIM animation, do texture
decoding, bind DDS material descriptors, submit deko3d commands, or render
an original FoJ actor. No user-owned original data is bundled or uploaded.
Current optional GPU research NRO still draws *generated-only quads*.
Actual GPU-side original-asset loading is a distinct future gate.

## Tests and approval rules

Generated `tests/test_gpu_private_actor_bridge.c` covers a two-section
FOJRM001 + two-texture FOJMAT01 binary pair and checks:
- Correct GPU vertex, UV, ordered section index and reservation/mask
- Broken magic, missing bytes, bad section order and NaN UV rejection
- Invalid material indices, mismatched section count, bad camera
- Too-small output capacity, alignment mismatch and oversize input
- Output bytes remain completely unchanged after every rejected input

Dedicated `stage257-private-actor-gpu.yml` runs GCC/Clang strict C11,
`-DNDEBUG`, ASan and UBSan on invented test data and compiles the new
bridge/parser sources with real devkitA64 to check portability.

The bridge is not yet integrated into the optional NRO's live rendering
path. First verify host tests and the ARM64 compile before considering
an opt-in private SD loader or DDS atlas bindings. A native compilation
is not evidence of a physical Switch GPU frame, original camera/pose
accuracy or playable FoJ gameplay.
