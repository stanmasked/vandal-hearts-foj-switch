# Stage335 — bounded row-padded source DDS staging (synthetic only)

## Engineering problem

The current research renderer in `gpu/deko3d_clear_main.c` reserves a
`PIXEL_STAGING_STRIDE` of `0x40000` (256 KiB) per RGBA8 material, enough for
256×256 textures. Stage332 accepts original DDS image dimensions as large as
2048×2048, requiring 16 MiB of decoded RGBA8 data. Directly copying such a
source into the old fixed buffer would overflow; odd widths also require an
explicit row-pitch policy.

## Safe CPU staging contract

`gpu/stage335_source_staging.[ch]` introduces a separate opt-in, platform-neutral
staging planner for a **single** already-decoded Stage332 RGBA8 base level.
It enforces:

- Stage332 format, width, height, mip-count and RGBA byte-count bounds
- exact caller-provided source byte count, output capacity, and power-of-two
  alignment (4..4096 bytes)
- at most 2048×2048 pixels and at most 16 MiB staged bytes
- checked row pitch and row-length-in-pixels for future image copy setup
- generated deterministic zero padding after each actual RGBA row
- rejection of forged plan metadata and overlapping source/output memory
- failure without changing destination or output plan

Host-only generated fixtures validate a 74×81 BGR-derived RGBA texture at
64-byte alignment, full 2048×2048 RGBA at 4096-byte alignment, and negative
bounds, unsafe aliasing, invalid format/alignment, forged plan, and capacity
cases. No original pixel data or source file paths are compiled into tests.

## Explicit limits / gating

This is **NOT** a native deko3d image upload or proof of DMA synchronization.
This module doesn't allocate a `DkMemBlock`, set a `DkCopyBuf`, bind an image,
record a command list, or submit GPU work. The legal deko3d row-length and
alignment requirements must be independently checked against the installed
SDK, then confirmed with generated-only NeXium framebuffer sampling before
the owner opts into source-texture execution. Never replace the existing
fixed-size atlas path with this plan without updating the native allocation
and image-copy code and writing failure-path tests.

The Stage334 private all-source CPU parity is independent: 1479/1479 original
DDS base images (221,530,568 RGBA pixels) matched the independent Pillow
reference exactly. Original PS3 bytes and the full private report stay in
owner-only Google Drive, not public GitHub CI.
