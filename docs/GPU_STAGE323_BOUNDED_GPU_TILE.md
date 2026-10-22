# Stage323 — genuine NeXium GPU draw of a Stage322 16×16 four-page BC1 tile

## Grounded baseline

Stage322 verified CPU generation of exact 1024-byte, 16×16 RGBA8 tiles
from four separately decoded BC1 atlas pages across all nine internal
junctions (Draft PR #207, dedicated CI 4/4). That was **not GPU rendering**.
Stage316 independently proved real NeXium GPU filtering on a distinct,
much larger 256×256 synthetic four-color quadrant texture.

## This actual GPU experiment

The optional Switch NRO is built from
`gpu/stage323_bounded_gpu_tile.mk`, preserving the working 18-vertex,
three-material deko3d scene, linear sampler and depth configuration
from the Stage316 generated-only research path.

Inside `foj_stage309_prepare_gutter_scene`, with explicit Stage323 and
Stage316 compile-time flags:

1. Create only one invented 1024×1024 BC1 DDS with color-coded pages.
2. Decode four independent 256×256 RGBA8 page buffers at (1,1),
   (2,1), (1,2) and (2,2).
3. Route a UV triangle to Stage320, Stage321, requiring `PATCH_REQUIRED`
   for all four sources; Stage322 builds one **16×16×4=1024-byte** RGBA
   replacement from true boundary pixels.
4. Use the replacement as GPU material 0, retaining two 256×256
   reference color pages in materials 1 and 2. The GPU upload receives
   real 16×16 atlas dimensions for material 0.
5. Change foreground quad UVs from Stage316's 127.5/256..128.5/256 to
   **7.5/16..8.5/16**, which covers exactly the four texel centers
   around the patch junction.
6. Create a distinct native **Stage323** marker with tile dimensions
   and byte count. Stage316 markers and evidence cannot stand in.

The native C test verifies actual material 0 size, 16×16 pixels and
UV range, 18-vertex topology and fail-closed fixture validation. The
dedicated devkitA64 job compiles the new NRO. The dependent NeXium
job must capture two *real* GPU frames and pass independent color,
two-axis gradient, four-corner endpoint and phase-change tests.
The checker will publish only the strict generated-only evidence list.

## Important distinctions

An exact Stage322 1-KiB CPU tile **does not automatically become a
drawable original FoJ mesh**. This experiment uses just one generated
centered quad and already-established GPU shader/material upload code.
It does not verify imported original PS3 mesh UVs, automatic filtering
across four independently bound GPU textures, geometry splitting,
arbitrary alpha-draw order, or physical Nintendo Switch hardware.

Only successful specialized Stage323 NeXium CI, not a host-generated
mock screenshot or a successful NRO build, proves that the new exact
1-KiB material was genuinely rendered. Keep this PR Draft and never
publish NPEB00148 contents, private capture logs or commercial assets.
