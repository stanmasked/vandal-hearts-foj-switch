# Original FoJ multi-shape wireframe viewer for Nintendo Switch

A fifth native `devkitA64/libnx` research NRO has been added:

**`foj-obj-wireframe-research.nro`**

It accepts the user's **locally exported multi-shape OBJ** generated from
their own PS3 `NPEB00148` package with
[inspect_complete_bmodel.py](../tools/inspect_complete_bmodel.py).
The original first-shape-only converter is also still supported. It is
a simple 3D wireframe renderer: no original game shaders, textures, PS3
executable, battle UI, animation or gameplay.

## Prepare and inspect the actual local geometry

First export the 3D mesh to a local gitignored folder, using your legally
held original two ZIP parts:

```sh
mkdir -p local-data/models

python3 -m tools.inspect_complete_bmodel \
  "/path/to/NPEB00148.pkg.zip.001" \
  "/path/to/NPEB00148.pkg.zip.002" \
  --asset "data/actors/npc/avatar_body.bmodel" \
  --reverse-winding --flip-v \
  --output "local-data/models/preview.obj"
```

This writes **all geometric sections** as one OBJ using big-endian
PS3-derived XYZ, UV and normal data. The OBJ includes original material
labels, but no texture pixels or bone pose data. The output will never be created unless
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
triangular edges with simple orthographic projection. `usemtl` and
`mtllib` directives are ignored safely by the wireframe-only loader. It has no z-buffer,
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

Full skeleton/rig transforms and `0x0A`/`0x0C` footer records,
original shader passes, vertex morphs,
`.banim` pose tracks, model placement in actual FoJ map scenes, and gameplay.
