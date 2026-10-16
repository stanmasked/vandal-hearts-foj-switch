# Nintendo Switch homebrew bring-up

This phase verifies **compiler/toolchain integration, synthetic tactical
logic and user-provided original-data research input**. No commercial game
assets are bundled. None of these NROs is the playable original PS3 game.

## Build

Requires a recent devkitPro devkitA64 / libnx toolchain and the usual Switch
Homebrew SDK support.

From the repository root:

```sh
make -f switch/Makefile verify
```


Produces nine independently built research executables, without bundled
commercial game assets, and validates NRO0 magic, file size and segments:

- `build/foj-switch-research.nro` — text-console map, controls, and logic.
- `build/foj-isometric-research.nro` — 1280×720 CPU-rendered isometric tiles
  displayed through libnx's linear framebuffer.

GitHub Actions uses `devkitpro/devkita64:latest` to compile the
research NROs and uploads them in artifact `foj-switch-research-nros`.
See [Switch NRO workflow](../.github/workflows/switch-nro.yml).

## Shared controls

- D-pad: move a cursor across the invented 8×6 battlefield.
- A: select the hero at H, or attempt a reachable move.
- B: cancel a selection.
- Plus: exits to the homebrew loader.

The invented elevation- and obstacle-aware movement uses `core/tactical_demo.c`.
A breadth-first search computes reachable tiles with a four-step budget and
maximum one-level climb per step. This is **not** the original game's battle
rules, meshes, renderer, menus, save system, PS3 executable or data.

## Portable movement core

Host-side tests in `tests/test_tactical_demo.c` validate reachability, slope
limits, blocking, selection, rejection, cancellation and cursor clamping.
They are executed through `.github/workflows/ci.yml` with the system C compiler.
The same core source is linked into both Switch `NRO` binaries.

The isometric NRO additionally uses `core/isometric_demo.c` to draw
**synthetic tile diamonds, height extrusions and unit markers** with a portable
CPU rasterizer. Host tests cover projection and pixel-buffer bounds. This is
not FoJ's original 3D rendering engine, does not load real game geometry or
textures, and has not yet been visually validated on real Switch hardware.

## Evidence ladder

1. Successful host-side unit tests — parser and validation only.
2. Successful NRO compiler/linker run — shell builds for ARM64.
3. NRO0 header/segment validation — structural plausibility only.
4. Emulator launch and input smoke test — runtime evidence on emulator.
5. Physical Switch run — hardware compatibility evidence.
6. Original FoJ game asset/render/gameplay tests — true porting progress.

Only claim levels that were specifically measured. Neither the build nor
the NRO metadata validator proves proper runtime behavior.

## Security and distribution

No downloaded game, game patches, PSN entitlements, cryptographic material or
copyrighted commercial assets are ever included in this CI workflow. Keep
original game files local.

## Synthetic host reference image

`tools/render_isometric_preview.c` produces an RGB PPM from the **same**
portable rasterizer as the Switch NRO; `tools/ppm_to_png.py` packages that image
as PNG without third-party Python packages. GitHub Actions workflow
[`isometric-preview.yml`](../.github/workflows/isometric-preview.yml)
uploads artifact `foj-isometric-synthetic-preview`.

The PNG shows invented geometry and units, **not actual FoJ graphics**.
Compare this reference to a later real Switch capture to detect rendering
issues; passing its host pipeline is not proof the NRO was run on hardware.


## Real-format COLL diagnostic viewer

A **third** NRO is now included in the devkitA64 build:
`build/foj-coll-map-research.nro`. It parses a user-provided local
`map1-1.coll` at `sdmc:/switch/foj/maps/map1-1.coll` and visualizes its
four numeric and two boolean fields as a top-down diagnostic heatmap.
If no valid file is present, it uses a generated 50×50 synthetic grid;
the status marker at the top-right is green for loaded files and red for
the synthetic fallback. These are *not* original collision gameplay rules.

For extraction to a local (gitignored) directory and Switch SD card
placement, see [COLL_SWITCH_VIEWER.md](COLL_SWITCH_VIEWER.md).

## Fourth independent build: DDS texture inspector

`build/foj-dds-texture-research.nro` decodes a user-supplied DDS-in-TGA
image in the local SD folder and displays it against a checkerboard; with no
valid file it loads a synthetic gradient. See
[DDS_SWITCH_VIEWER.md](DDS_SWITCH_VIEWER.md) for exact controls and local
export steps. This proves ARM64 compilation and asset-loader preparation,
not operation of the original game's 3D renderer or a hardware test.

## Fifth build: original first-mesh wireframe viewer

`build/foj-obj-wireframe-research.nro` is compiled from
`core/obj_wireframe.c` and `switch/source/obj_main.c`. It reads the
user's own locally exported `preview.obj` from SD, otherwise displaying
an original **synthetic cube**. The app rotates and zooms a CPU wireframe;
it does not simulate the original FoJ 3D engine. For controls, file paths
and legal data separation see [OBJ_SWITCH_VIEWER.md](OBJ_SWITCH_VIEWER.md).

## Sixth build: local original BANIM clip reader

`build/foj-banim-research.nro` links `core/banim_core.c` and displays
sampled bone-track quaternion/translation values from a user-supplied local
`sdmc:/switch/foj/anims/preview.banim`. Without it, the NRO displays
synthetic one-key animation data. See
[BANIM_SWITCH_VIEWER.md](BANIM_SWITCH_VIEWER.md). It does not yet deform
original meshes or reproduce PS3 animation blending; hardware launch
is still unverified.

## Seventh build: skeletal deformation mechanics (synthetic)

`build/foj-skinning-research.nro` links the portable native
`core/skeletal_skin.c` and the existing wireframe renderer. It demonstrates
joint-driven **moving vertices** on an invented two-bone test strip.
Original FoJ model geometry/animation is not included or claimed to render
correctly. The red marker denotes synthetic input. Controls and caveats:
[SKINNING_SWITCH_VIEWER.md](SKINNING_SWITCH_VIEWER.md).

## Eighth build: original local mesh + BANIM animation

`build/foj-rigged-actor-research.nro` accepts a user-owned original
`FOJRM001` rigged model at `sdmc:/switch/foj/rig/preview.fojrm` and its
parent-compatible `BANIM` clip at
`sdmc:/switch/foj/anims/preview.banim`. It then runs experimental
bone-world/inverse-bind/weight deformation and displays a wireframe, not
the original PS3 shader/material scene.

On absent, corrupt or incompatible user files, the app displays an
explanatory diagnostic instead of claiming original graphics are present.
The exact procedure for local original asset preparation and the limitations
of experimental skinning are in
[ORIGINAL_RIGGED_ACTOR_SWITCH.md](ORIGINAL_RIGGED_ACTOR_SWITCH.md).
Physical Switch execution and matching the PS3 engine are still unverified.

## Ninth build: original user-controlled DDS textured animated mesh

`build/foj-textured-actor-research.nro` combines local original rigged
geometry, matching `BANIM` animation, and original DDS-in-TGA atlas from
SD. Its CPU triangle rasterizer interpolates UV coordinates, performs
alpha cutout and depth testing, and renders an experimental animated mesh.
No copyrighted asset is bundled in GitHub or NRO. The original engine's
materials, skinning transform order, visual style and console performance
are not yet validated. See
[TEXTURED_ACTOR_SWITCH.md](TEXTURED_ACTOR_SWITCH.md).
