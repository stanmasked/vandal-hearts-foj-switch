# Stage 179 — generated DDS pixel contract between Python and native C

This stage checks an actual **cross-language RGBA8 pixel buffer**,
not just whether an NRO/DKSH build completed successfully.

The stage-162 Python generator writes two fixed **8×8 RGBA8**
checkerboards. The native C `gpu/atlas_dds.c` parser is used by the
GPU research path to decode the user-selected DDS. To guard against
channel-order mistakes before any on-device visual check, stage 179
compiles `tests/foj_stage179_native_dds_pixels.c` against the exact
native parser and invokes it from Python.

The native helper accepts **exactly 384 DDS bytes on standard input**
and emits exactly **256 decoded RGBA8 bytes on standard output**.
It has no file path argument, contains no original FoJ artwork and
does not write a file. If validation fails, it returns nonzero and
emits no pixel bytes.

Tests compare native output byte-for-byte against the independently
generated Python payload, for **both distinct material slots**.
They also transform each texture into a valid BGRA8-ordered DDS and
verify the C decoder restores precisely the same canonical RGBA8
output. Invalid magic, short/trailing payload, invalid channel
masks, extended DX10 FourCC and invalid dimensions must be rejected
without leaking partial output.

Run on a host with a C11 compiler:

    python3 -m unittest discover -s tests \
      -p 'test_foj_stage179_native_dds_color_contract.py' -v

The normal Research tests matrix runs these five tests on Python 3.11
and 3.13. The native research build workflow explicitly repeats the
same test after SDK NRO/DKSH compilation.

Expected first RGBA8 texel values (red, green, blue, alpha):

| Synthetic DDS | Top-left pixel | Second 2×2 checkerboard |
| --- | --- | --- |
| `material0.dds` | (255, 215, 70, 255) | (240, 45, 30, 255) |
| `material1.dds` | (70, 235, 220, 255) | (35, 95, 235, 255) |

**Evidence boundary:** This checks native **CPU DDS decoding and
pixel channel order**, not deko3d texture upload, sampler state,
shader execution, framebuffer presentation, correct screen colors
or real Nintendo Switch hardware. All images are invented,
generated-only research patterns; no PS3 game data are published.
