# FoJ Stage338 — generated GPU framebuffer samples Stage336-uploaded image

## Scope and evidence gate

This optional, **generated-only** Nintendo Switch research NRO is a child of
the Stage337.8 verified GPU buffer/image roundtrip. It does **not** load,
decode, redistribute or render any original game DDS, PS3 package or capture.

The Stage330 synthetic corner-patch renderer previously sampled a generated
256×256 atlas and a 16×16 four-corner tile from a fixed CPU staging pool.
Stage338 reuses its independent screenshot oracle and shader draw path, but
**replaces source texture slot 0 with a real Stage336 dynamically staged,
GPU-uploaded RGBA8 image**:

1. Generate the exact 256×256 quadrant atlas in the guest NRO.
2. Pass these RGBA bytes to `foj_stage336_native_record_rgba_upload` at
   256-byte row alignment; it allocates bounded staging and GPU image storage.
3. Use the resulting `FojStage336NativeTexture.image_view` as the actual
   descriptor for fragment-texture slot 0. The image remains allocated until
   queue completion.
4. Keep the 16×16 corner tile as the second shader sample; correct its
   `DkCopyBuf.rowLength` from 16 **pixels** to 64 **bytes**. A one-layer copy
   sets `imageHeight=0` per upstream deko3d source's byte-stride semantics.
5. Use the existing generated DKSH shaders to sample both textures on a
   geometry split between source remainder and an ordered corner patch.
6. Capture **two independently acquired NeXium framebuffer PNGs**, reject
   duplicates, wrong 1280×720 size, missing four-quadrant contributions,
   incorrect central blended midpoint, wrong linear filtering, incorrect
   source remainder colors or displacement of the patch center.

A guest upload marker **alone cannot pass**. An all-green general CI or
successful Stage337 roundtrip is also **not** proof of this framebuffer scene.
The existing Stage330 auditor independently opens both actual framebuffer
captures and checks spatial/color features under bounded tolerance (not exact
full-frame pixel equality).

## Build and verification

- `gpu/stage338_native_frame.mk`: isolated NRO `build/foj-deko3d-stage338-native-frame.nro`
  with opt-in flag `FOJ_GPU_STAGE338_NATIVE_TEXTURE_DRAW=1`.
- `gpu/deko3d_clear_main.c`: protected opt-in native upload, descriptor
  association, 16×16 byte-stride correction and resource ownership; previous
  generated-only configurations remain on their existing branches.
- `tools/foj_stage338_frame_gate.py`: rereads both screenshots using the
  independently tested Stage330 pixel oracle, confirms receipt and shader
  provenance, then exports *only* one safe aggregate JSON plus downloaded
  public NeXium binary archive SHA256.
- `tests/emulator/test_stage338_frame_gate.py`: generated-only negative
  fixtures for forged receipts, duplicate frames, extra input files, existing
  output and native GPU shader/texture wiring.
- `.github/workflows/stage338-native-frame.yml`: host and devkitA64 tests,
  then a real NeXium guest GPU draw and screenshot verification.

The raw guest log and both PNG framebuffer captures **remain on the ephemeral
CI runner only**. They are **not** in any public GitHub artifact; no source game
bytes, private material references or raw experiment recordings are uploaded.
For persistent evidence, the aggregate JSON and build NRO should be copied
to the owner-only Google Drive evidence archive, with exact SHA256 and owner
permissions verified.

## Strict limits

This stage proves *only* if its exact-head native guest GPU framebuffer
screenshot job is SUCCESS. It is intended to validate the **synthetic**
Stage336-uploaded RGBA image is sampled by a live deko3d shader and displayed
at the expected location/colors. It does not establish original game rendering
or physical Switch behavior. Keep Draft pending independent CI and evidence
archiving. Parent PR216/218/219/220 remain unmodified and unmerged.

Upstream byte-stride reference:
https://github.com/devkitPro/deko3d/blob/master/source/dk_image.cpp
