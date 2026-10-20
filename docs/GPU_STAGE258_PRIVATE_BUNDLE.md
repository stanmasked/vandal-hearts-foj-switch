# Stage258 — private actor + two DDS file intake

## Result and scope

A **separate opt-in** deko3d NRO now performs a bounded preflight of
user-local research interchange files **before** starting its graphics
device. The normal GPU research NRO, GPU clear smoke, and normal Switch
CPU NROs keep their earlier generated-only behavior.

The new target is:

```sh
make -f gpu/private.mk verify
```

Outputs `build/foj-deko3d-private-bundle-preflight.nro`. The compiled
program contains **no commercial game assets**. To exercise private mode,
place the following **user-owned, locally converted** files on the
device/emulator SD card (do not upload them to a public repository):

```text
sdmc:/switch/foj/gpu/actor.fojrm
sdmc:/switch/foj/gpu/actor.fojmat
sdmc:/switch/foj/gpu/material0.dds
sdmc:/switch/foj/gpu/material1.dds
```

The FOJRM001 / FOJMAT01 formats are **our own bounded local interchange
formats**, not native PS3 resource formats. Only *classic DDS* RGBA8,
BGRA8, DXT1/BC1 and DXT5/BC3 (with fully validated mip chains) are
supported. DDS base levels must fit 256×256 RGBA8 and the model must
have exactly two used material slots, because this research renderer
currently supports only two textures. No proprietary PS3 swizzling,
cubemap/array, DX10 or arbitrary multi-atlas count is accepted.

## Safety and transaction contract

The `foj_gpu_private_bundle_preflight` API:

- Checks regular-file size bounds and rejects symlink/directory/FIFO
  entries for both model and material sources; verifies one opened file
  descriptor, two bytewise reads and entry metadata after reading
- Caps private FOJRM001 source to 2,000,000 bytes and FOJMAT01 to at
  most 272 bytes, with the established maximum 20,000 vertices and
  64 sections
- Calls the **real** Stage257 FOJRM/FOJMAT geometry bridge and Stage256
  ordered GPU memory planning; refuses mismatched sections or materials
- Requires **both** validated local DDS files using the existing
  fail-closed DDS reader; a missing texture never causes a synthetic
  fallback in private preflight mode
- Only commits a path-free, metadata-only numeric output report when
  *all four* input files pass; frees all temporary source, vertex,
  batch and decoded pixel buffers even on an error
- Reports generic statuses without printing user paths, file hashes,
  original vertex coordinates or image contents

**Limitations:** parent directory components are assumed to be trusted
local mounts; the final path component gets no-follow protection. The
reader cannot guarantee atomic consistency of all four independently
read files against deliberate concurrent mutation/ABA. The generated
CI suite provides source-level security and correctness tests, not a
physical Switch hardware proof.

## Deliberate rendering limitation

**Even after private preflight succeeds, the Stage258 NRO continues to
draw ONLY the previously generated two-quads demonstration.** The
original FoJ actor vertices and DDS pixels are validated in temporary
memory and then discarded, not copied to deko3d vertex/image memory.

This stage is therefore the **file-to-validated-manifest gate**, not
real original-game rendering. The next step is an explicit private
actor GPU upload/draw branch with separate NeXium/hardware pixel proof,
material sampler tests, and a distinction between static bind geometry
and BANIM-animated/PS3-accurate scene output.

Synthetic-only checks live in `tests/test_gpu_private_bundle_intake.c`
and are executed under GCC, Clang, NDEBUG and ASan/UBSan.
`.github/workflows/stage258-private-bundle.yml` builds both the
host fixture and the real separate devkitA64 NRO; no user files are used.
