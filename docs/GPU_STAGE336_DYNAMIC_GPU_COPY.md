# FoJ Stage336 — bounded native deko3d copy recording (generated data only)

Stage336 is a **narrow opt-in native transfer component**, not an executed GPU
frame or an original-game upload. This remains a Draft child of Stage335.

- `gpu/stage336_gpu_copy_plan.[ch]` independently checks Stage335 RGBA row
  metadata, 32–4096-byte row alignment, 4KiB CPU-visible GPU staging buffers,
  64MiB maximum device image allocation and 1MiB maximum device alignment.
  The values for the latter two limits are sanity bounds rather than proofs of
  available hardware memory. All invalid requests leave output unchanged.
- `gpu/stage336_native_upload.[ch]` uses **actual** SDK types and commands:
  `DkImageLayoutMaker`, `dkImageLayoutGetSize/Alignment`,
  `DkMemBlockMaker`, `dkImageInitialize`, `DkCopyBuf`, `DkImageRect`, and
  `dkCmdBufCopyBufferToImage`. Its source address points to a separately
  allocated, zero-padded, GPU-visible staging block. Copy `rowLength` is the *byte stride*, never the pixel count
  (as implemented in upstream deko3d `source/dk_image.cpp`).
  `imageHeight` is a byte layer stride and can be zero for one layer.
  Both upload and reverse readback must pass `row_pitch_bytes`. The dynamic device image is `RGBA8_Unorm`, with one
  mip level; source mip >0 upload is explicitly out of scope.
- The function records exactly one deko3d copy only **after** validating and
  allocating GPU buffers. The caller must keep both allocations alive until
  the submitted queue completes and release them after synchronization. It
  does **not** submit a queue, capture a framebuffer, or certify GPU success.
- Generated fixtures test 74x81 uneven width, 2048x2048 maximum input,
  overflow, invalid alignments, forged metadata, short capacity, and no
  mutation on rejection, with GCC/Clang and Clang ASan/UBSan.
- Native devkitA64 CI compiles the deko3d adapter against real SDK headers.
  Neither the `DkCopyBuf` alignment contract on target hardware nor the
  per-frame memory budget is considered validated until a real NeXium GPU
  transfer and framebuffer comparison is executed in a later stage.

Private source archive: original NPEB00148 PS3 PKG and 1,479 source DDS assets
stay in owner-only Google Drive. No source bytes, paths or raw GPU screenshots
are committed to GitHub. Independent base-level CPU DDS pixel comparison was
completed for the full 1,479-texture catalog. This Stage336 code works solely
on caller-supplied RGBA8 buffers and generated CI inputs.
