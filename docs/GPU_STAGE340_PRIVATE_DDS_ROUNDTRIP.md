# Stage340 — bounded native DDS GPU upload/readback

## Scope

Stage338 established that a Stage336-uploaded **generated** RGBA texture can
be sampled by the fragment shader in real NeXium framebuffer captures.
Stage339 added a strict, synthetic-tested DDS decoder-to-GPU-plan bridge.
Neither was evidence that an original PS3 texture was transferred to the GPU.

Stage340 introduces a standalone NRO that reads one DDS from
`sdmc:/switch/foj/gpu/source.dds`. It accepts only the selected bounded
256×256 classic BGRA8 base-level contract, runs Stage332 inspection and
Stage339 preparation using the actual `dkImageLayoutGetSize/Alignment`,
uploads RGBA8 via Stage336, submits a native deko3d queue, then copies the
GPU image back to CPU memory. A fixed success receipt is created exclusively
after queue synchronization, GPU cache visibility and byte-exact comparison
of every decoded RGBA channel.

The NRO embeds no game assets. The public workflow supplies only an invented
256×256 BGRA8 DDS generated from constants. Public CI checks the source
fixture is unchanged before/after execution and publishes only an allowlisted
aggregate JSON and the NeXium runtime archive checksum.

## Exact evidence boundaries

A successful public run proves the Stage340 implementation can transfer a
generated DDS through native Stage336 upload and GPU image readback in
NeXium. It does **not** prove that an original PS3 DDS was read or rendered,
does not test shader sampling of the original texture, and does not establish
physical Nintendo Switch behavior. Original-texture sampling is a separate
owner-local gate. The existing Stage334 owner-only report covers exact
Stage332 C vs Pillow base-mip CPU pixel parity for 1,479/1,479 original DDS
images; it is not itself GPU evidence.

## Owner-local source run

Use the same NRO and a fresh SD root, but copy one owner-held selected DDS to
`sdmc/switch/foj/gpu/source.dds` **outside any Git checkout**. Keep the
original PKG and extracted DDS in the owner's private Drive. Run the
owner-local runner only against the exact file and NRO; it writes a private
aggregate report with source identity and the native guest receipt. Do not
upload source DDS bytes, decoded images, raw readback buffers, guest logs or
private source hashes to public GitHub/Actions. The owner-local report belongs
in private Drive's `03_Aggregate_Reports`; the unchanged extracted DDS, if
archived as a separate file, belongs in `01_Private_Originals`.

If the guest fails, a bounded numeric stage may be used to localize the stop.
A progress marker alone is never considered GPU success; only the exact
NRO-written receipt following the full channel-by-channel comparison counts.

## Current limits

- One bounded 256×256 BGRA8 texture, base mip only.
- DDS-to-RGBA CPU decoding is checked by Stage332; upload sizing by Stage339
  and Stage336 using actual SDK image layout values.
- Stage340 is a transfer/readback gate, not a framebuffer or material-binding
  gate. Stage341 should sample the exact original texture through a shader and
  compare selected rendered pixels to a private CPU reference.
- Original package authenticity against an independent publisher hash remains
  unverified; source bytes remain owner-only and unchanged.
