# Stage262 — generated DDS quadrant, UV orientation and material proof

Stage261 demonstrated actual deko3d geometry and two *uniform-color*
research DDS atlases in NeXium. Stage262 deliberately makes each atlas
nonuniform, revealing errors which uniform-color textures cannot detect:
horizontal U mirroring, vertical V mirroring, constant UVs, swapped
material indices, absent DDS areas, or wrong UV interpolation.

## Strict invented-only input

The new generator `tools/foj_stage262_generated_uv_sd.py` reuses the
**same 6-vertex, two-section FOJRM001/FOJMAT01 model** and real generated
UAM shaders from Stage260. It replaces just the 64×64 classic RGBA8
DDS base pixels with eight fixed opaque colors:

| DDS | Top-left | Top-right | Bottom-left | Bottom-right |
|---|---|---|---|---|
| warm/slot 0 | (234,45,35) | (250,130,22) | (180,20,42) | (225,90,90) |
| cool/slot 1 | (15,165,237) | (85,220,211) | (26,190,165) | (75,175,247) |

Top-left refers to a decoded DDS pixel at x=0..31, y=0..31, with
`v=0` expected at the **top** of each image. This tests an explicit
orientation convention; the verifier must NOT discover or silently
compensate for a reversed V mapping.

For each material triangle, four UV sites are intentionally separated
from the DDS color seams:
`(.40,.40)`, `(.60,.40)`, `(.25,.75)`, `(.75,.75)`.
The independent verifier inverts the specified UV triangle
`(0,1), (1,1), (.5,0)`, projects its coordinates via the documented
camera, samples a small neighborhood at each *predicted* screen pixel,
and demands the corresponding quadrant color at >=32 samples.
It also demands >=220 image samples of each quadrant across the
material's region in each of two fresh real guest frames, without
admitting colors from the other atlas.

The test preserves Stage260 color presence and Stage261 silhouette
IoU/precision/recall gates and explicitly rejects duplicate screenshots
and unchanged GPU background.

## Actual GPU verification

Dedicated `.github/workflows/stage262-gpu-uv-quadrants.yml`:
1. Builds the same real opt-in deko3d NRO plus UAM DKSH using devkitA64.
2. Generates **only** new test DDS files into an empty isolated NeXium SD.
3. Launches the NRO in NeXium with Vulkan/Xvfb.
4. Requires independent Stage260 and Stage261 geometry validation.
5. Requires the Stage262 eight-quadrant UV/color verifier on real
   captured 1280×720 PNG frames.
6. Uploads guest captures, logs, source receipt and UV report.

Unit tests generate mock Pillow raster images solely to test the
detector, and intentionally try absent, uniform, horizontally
mirrored, vertically mirrored, and swapped materials. Such mock
images can never satisfy or substitute for actual emulator evidence.

No original PS3 game binaries, DDS data or screenshot content is
stored, committed or fed to a public CI runner.

## Limitations

Even a success proves only **the synthetic two-material, static
projected model's UV orientation and basic texture sampling in
NeXium**. It does NOT establish real PS3 model UV conventions,
multi-material shaders, bone animation, PS3 camera, depth/culling,
physical Switch behavior, frame rate or playable game. If the
orientation is wrong, hold PR as Draft and diagnose the conversion;
do not change the oracle to mask the bug.
