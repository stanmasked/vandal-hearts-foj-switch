# Stage256 — ordered GPU actor vertex-upload budget (generated-only)

## Purpose

Prepare one GPU vertex reservation for **up to 64 contiguous triangle batches**
and up to **8 material indices**, using existing `FojGpuBatch` metadata.
This is a deliberately small bridge towards a multi-material character
renderer. It **does not** load an original PS3 BMODEL, FOJRM001, FOJMAT01
or a copyrighted DDS atlas, and does not claim game compatibility.

## Validation contract

`foj_gpu_actor_upload_plan` first calls the existing transactional
`foj_gpu_build_draw_plan` validator on scratch output. The input must:

- Use 1..64 nonempty, contiguous, ordered batches covering exactly all
  vertices; every batch contains complete triangles
- Fit within 20,000 vertices and 8 material slots, with valid texture indices
- Request a power-of-two GPU allocation alignment from 16 B to 1 MiB

It computes payload as `vertex_count * sizeof(FojGpuVertex)` (24 bytes)
and rounds the reservation upward to the requested alignment, without
overflow or partial output writes. The material mask records only referenced
texture slots; it does **not** imply the textures were loaded or bound.

On invalid section order, overlapping/gapped ranges, unsupported counts or
alignment, and any null required input, the output structure is preserved.

## Generated test sizes

| Generated case | Triangles | Batches | Materials | Payload | GPU reservation at 4096 alignment |
|---|---:|---:|---:|---:|---:|
| Separate two-quad demo | 4 | 2 | 2 | 288 B | 4,096 B |
| Invented six-section actor scale | 3,022 | 6 | 2 | 217,584 B | 221,184 B |
| Maximum three-vertex-aligned stream | 6,666 | 1 | 8 declared | 479,952 B | 483,328 B |
| 64 tiny sections | 64 | 64 | 8 | 4,608 B | 8,192 B |

The six-section example uses only fabricated batch lengths and an index
pattern. It contains **no original Daldren geometry, original material names
or copyrighted assets**.

## Integration and proof

Only the **optional** `gpu/triangle.mk` NRO now calls this validator
before allocating its generated two-quad vertex buffer. This changes neither
the default nine CPU NROs nor the independent clear-only GPU NRO.

Host coverage includes GCC, Clang, `-DNDEBUG`, UBSan and ASan, with tests
in `tests/test_gpu_actor_upload_plan.c`, as well as the existing
`gpu/clear.mk` host-check suites. The dedicated
`.github/workflows/stage256-gpu-actor-upload.yml` also builds the
experimental NRO using devkitA64 and validates its NRO header.

**A successful host test or devkitA64 link alone does not prove real Switch
GPU presentation.** Nor does this stage validate the original PS3 scene,
bone animations, UV conventions, multi-atlas sampling, or battle gameplay.
A physical console or independently observed framebuffer will still be
needed; private original assets must remain outside public GitHub.
