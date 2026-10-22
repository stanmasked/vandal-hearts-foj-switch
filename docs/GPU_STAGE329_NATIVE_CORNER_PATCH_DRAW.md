# Stage329 — native deko3d draw of a Stage328 corner patch

## What the target does

The separate target in gpu/stage329_corner_patch_draw.mk is a generated-only
Switch NRO. It does not enable private actor intake, depth proof, alpha blend,
or the three-layer demo. It creates four solid 256x256 RGBA8 page fixtures
(NW red, NE green, SW blue, SE white), plans one UV triangle at the internal
(2,2) atlas junction through Stage320, and invokes Stage328 to produce both
the 16x16 corner tile and its matching tile-local geometry stream.

The test triangle spans nearly the full 16x16 tile while remaining
strictly inside its atlas bounds, so the draw stream has three vertices and
one material section that selects texture slot 1. Stage324 already remaps the
tile fragment to tile-local UVs; Stage327 retains original-atlas UVs only for
source remainders. This Stage329 fixture has no remainder, so it validates the
local UV range and passes it to the GPU unchanged. Slot 0 contains a separate
generated fallback and is not used by the triangle.
The projected vertices use V flipping to match the native texture row
orientation, and the sampler is explicitly linear. The resulting midpoint
should sample the average RGBA value (128,128,128,255), while the four
surrounding samples should retain their respective red, green, blue and white
quadrant colors.

## Native evidence boundary

The NRO writes
foj-native-stage329-corner-patch-upload.txt only after the tile upload command
has been submitted and dkQueueWaitIdle has returned. That file proves the
expected CPU receipt and upload path, not that a visible triangle was drawn.

The dedicated NeXium workflow separately captures two real GUI frames and
requires the central gray midpoint, horizontal green interpolation, vertical
blue interpolation, red/green/blue/white quadrant contributions, a triangle
footprint distinct from the animated background, and a change between frames.
Host-painted gradient fixtures exist only for testing the screenshot auditor;
they are never exported as runtime evidence.

The public evidence export is restricted to the generated-input descriptor,
fixed upload receipt, two audited screenshots, compact audit receipt and the
NeXium archive checksum. Raw guest logs are excluded.

## Limits

This stage demonstrates that Stage328's generated tile can be uploaded as a
second deko3d texture and sampled by a real GPU draw in NeXium. It does not
show the original FoJ actor, the original full atlas, PS3 material/shader
semantics, multi-junction clipping, alpha ordering across an original mesh,
or physical Switch hardware. The target remains isolated from main and should
stay Draft until host, native devkitA64 and real NeXium checks all pass.
