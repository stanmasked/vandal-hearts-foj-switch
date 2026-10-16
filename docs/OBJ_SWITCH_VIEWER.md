# Original FoJ first-shape wireframe viewer for Nintendo Switch

A fifth native `devkitA64/libnx` research NRO has been added:

**`foj-obj-wireframe-research.nro`**

It accepts the user's **locally exported first-shape OBJ** generated from
their own PS3 `NPEB00148` package with
[decode_bmodel_geometry.py](../tools/decode_bmodel_geometry.py). It is
a simple 3D wireframe renderer: no original game shaders, textures, PS3
executable, battle UI, animation or gameplay.

## Prepare and inspect the actual local geometry

First export the 3D mesh to a local gitignored folder, using your legally
held original two ZIP parts:

```sh
mkdir -p local-data/models

python3 -m tools.decode_bmodel_geometry \
  "/path/to/NPEB00148.pkg.zip.001" \
  "/path/to/NPEB00148.pkg.zip.002" \
  --asset "data/actors/npc/archery_target_character.bmodel" \
  --reverse-winding \
  --output "local-data/models/preview.obj"
```

This writes **only the first geometric section** as an OBJ using big-endian
PS3-derived XYZ, UV and normal data. The output will never be created unless
the user supplies `--output`, and existing files are not overwritten.

Copy `preview.obj` into this directory on your own Switch SD card:

`/switch/foj/models/preview.obj`

Then launch `foj-obj-wireframe-research.nro` from Homebrew Menu. The viewer
opens the file at `sdmc:/switch/foj/models/preview.obj`.

**Status indicator:** green means a syntactically acceptable local OBJ was
loaded; red means the synthetic fallback cube is displayed. Neither color
establishes authenticity or compatibility with the original game.

**Controls:** D-pad left/right rotates around the vertical axis; up/down
adjusts elevation. ZR/ZL zoom in/out; Plus exits the viewer.

The visualizer ignores OBJ `vt` and `vn` records for now, drawing only
triangular edges with simple orthographic projection. It has no z-buffer,
occlusion, texture mapping, mesh transforms or skeletal deformation. Users
may rotate a correct mesh and verify the object is recognizable, but this is
not equivalent to restoring an original PS3 scene.

## Engineering evidence

- `core/obj_wireframe.c` implements portable, bounded XYZ/F triangle input
  and a CPU wireframe view usable on host and ARM64 Switch.
- `tests/test_obj_wireframe.c` uses generated OBJ fixtures to check
  triangle import, invalid inputs, framebuffer bounds and synthetic fallback.
- `switch/source/obj_main.c` provides a native libnx framebuffer/controller
  shell with no proprietary content.
- The compiled NRO is uploaded to the shared `foj-switch-research-nros`
  GitHub Actions artifact after NRO0 validation.
- Actual Switch hardware execution and original mesh display still await
  runtime testing.

## Legal/data separation

The repo contains only original clean-room code and synthetic test meshes.
Never commit `preview.obj`, the real `.bmodel`, DDS atlases or the user's
PKG to the repository, even if it is private. Keep them on local storage and
the user-controlled Switch SD card.

## What still must be reverse-engineered

All model sections beyond the first, the `0x0F` record family, bone
weights, material assignments, original shader passes, vertex morphs,
`.banim` pose tracks, model placement in actual FoJ map scenes, and gameplay.
