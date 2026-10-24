# Stage340 — private original DDS GPU sampling

Stage340 adds an opt-in native NRO that reads exactly one local
`sdmc:/switch/foj/gpu/material0.dds`, validates it with Stage332, decodes
level zero into RGBA8 through the Stage339 bridge, derives the Stage335 row
staging plan from the actual deko3d image layout, records the Stage336 native
upload, and samples that uploaded image on a full-screen quad. Missing,
malformed, unsupported or oversized source DDS files fail closed; slot 0 never
falls back to a generated texture.

The native NRO writes a fixed receipt only after a frame has been presented
and the queue has drained. The host then independently decodes the source DDS
and checks sampled framebuffer pixels in two real NeXium captures. The source
hash and raw frames are kept only in the private evidence directory.

## Privacy boundary

The GitHub Actions workflow deliberately creates a synthetic 64x64 BGRA32 DDS
inside the runner. It never downloads the original PS3 PKG, any extracted game
resource, a private texture, or a private capture. Only a strict aggregate
proof and the NeXium archive checksum are uploaded as an Actions artifact.
The aggregate explicitly states that original PS3 assets were not used and
that physical Switch output was not verified.

For an owner-local run, place one independently selected DDS at
`sdmc/switch/foj/gpu/material0.dds`, copy the two generated DKSH shader files
beside it, and run `tools/foj_stage340_nexium_drive.sh` with
`NEXIUM_BIN`, `FOJ_NRO`, `NEXIUM_DATA_ROOT`, and `FOJ_EVIDENCE_DIR`
pointing to the private workspace. Set `FOJ_ORIGINAL_PS3_ASSET=1` only when
the source file is confirmed to be an original resource from the owner-held
PS3 package. Point `FOJ_EVIDENCE_DIR` at the owner's private Google Drive
sync folder so the source SHA, two raw captures, native receipt and private
report persist beyond the temporary runtime. Do not upload this directory to
GitHub or run the public `publish` command on it.

## Evidence levels

A passing generated-only NeXium run proves that the integrated DDS decoder,
staging plan, native upload and shader sampling path work together for the
synthetic fixture. It does **not** prove that an original PS3 texture was
displayed. That claim requires the separate owner-private run above, where the
source DDS SHA is checked before and after execution and both captured frames
match an independent CPU decode. Physical Nintendo Switch verification remains
a separate gate.
