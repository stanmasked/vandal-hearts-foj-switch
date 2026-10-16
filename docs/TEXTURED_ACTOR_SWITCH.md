# Ninth Nintendo Switch NRO — original textured animated FoJ actor

**Status (2026-10-16): native ARM64 compilation and automated tests pass.
No physical Switch frame-rate or original PS3 visual-fidelity test yet.**

A new clean-room research program, `foj-textured-actor-research.nro`, links
the previously verified original-data readers to a **new CPU rasterizer**
that draws filled textured triangles instead of only wireframe edges.

It is not the original game's graphics engine, HD remake or playable port.
No copyrighted textures/models/animations are included in the GitHub NRO
or repository source.

## What now works

1. Load the user's locally supplied converted original BMODEL (all meshes,
   bind bones, indices and per-vertex weights), `FOJRM001`.
2. Load a matching original BANIM clip; reject incompatible parent
   hierarchies instead of choosing a random animation.
3. Recalculate interpolated local poses and deform original vertex positions
   using experimental CPU linear blend skinning.
4. Load either **one** or **up to eight** original DDS-in-TGA atlases (BGRA8
   or DXT1/BC1) from SD, selected per model section via FOJMAT01.
5. Render real mesh triangle fills with **interpolated UV coordinates**,
   nearest-neighbor texture sampling, an orthographic camera, alpha cutout
   and a per-pixel floating-point depth buffer.

The renderer now supports **multiple atlas files assigned per geometric
section**, with one depth buffer for all sections. A material table does
not yet encode the original FoJ shader flags, two-sided blending, or
lighting. See [MULTI_MATERIAL_SWITCH.md](MULTI_MATERIAL_SWITCH.md).

### Private files on Nintendo Switch SD card

```text
/switch/foj/rig/preview.fojrm
/switch/foj/anims/preview.banim
/switch/foj/textures/preview.tga       (single atlas)

# Or, when multiple atlas files are needed:
/switch/foj/textures/preview.fojmat
/switch/foj/textures/texture_00.tga
/switch/foj/textures/texture_01.tga
...
```

The file may be called `.tga` but must contain the actual **DDS**
container data, as observed in the original game.

**With missing or malformed data:** the app shows a diagnostic message,
not a fake original FoJ character. It never downloads assets.

### Create the three files locally from your own original game copy

From the repository root, with the user's provided package ZIP chunks:

```sh
mkdir -p local-data/rig local-data/anims local-data/textures

python3 -m tools.export_local_rigmesh \
  "/path/to/NPEB00148.pkg.zip.001" \
  "/path/to/NPEB00148.pkg.zip.002" \
  --asset data/actors/npc/avatar_body.bmodel \
  --output local-data/rig/preview.fojrm

python3 -m tools.export_local_banim \
  "/path/to/NPEB00148.pkg.zip.001" \
  "/path/to/NPEB00148.pkg.zip.002" \
  --asset data/actors/anims/avatar_idle.banim \
  --output local-data/anims/preview.banim

python3 -m tools.export_local_texture \
  "/path/to/NPEB00148.pkg.zip.001" \
  "/path/to/NPEB00148.pkg.zip.002" \
  --asset data/actors/npc/avatar_texture.tga \
  --output local-data/textures/preview.tga

python3 -m tools.check_local_rig_pair \
  local-data/rig/preview.fojrm \
  local-data/anims/preview.banim
```

These are user-initiated exports, and the tools refuse to overwrite files.
Copy the three previews to their matching SD paths. For a multi-atlas model,
run `python3 -m tools.export_local_material_pack` with the **same BMODEL**
and copy its `preview.fojmat` and `texture_XX.tga` files instead
(see [full instructions](MULTI_MATERIAL_SWITCH.md)). Never commit them to
GitHub, even when the repository is private.

### Controls

| Button | Function |
| --- | --- |
| A | Play / pause original BANIM clip |
| B | Reset timeline to zero and pause |
| D-pad left/right | Rotate around vertical axis |
| D-pad up/down | Adjust camera elevation |
| ZR/ZL | Zoom |
| X | Toggle flipped texture V for diagnostics |
| Plus | Exit |

A small amber indicator denotes **original user-controlled input with
UNVERIFIED engine transform/material interpretation**, not a fidelity pass.

## Grounded real-data desktop verification

An independent local test used the user's real archived files:

| Original sample | Result |
| --- | --- |
| `avatar_body.bmodel` | 5 shape sections, 4,722 vertices, 1,574 triangles |
| `avatar_idle.banim` | 28 matching bone tracks, 5,600 keys, ~6.6333 s |
| `data/actors/npc/avatar_texture.tga` | DDS DXT1, 1024 × 1024 |
| Original DDS data bytes | 524,416 |
| Original mesh + animation + texture loading | Passed format and bounds checks |
| CPU rasterizer with original static mesh | Nonempty real textured triangular output |
| Original-keyframe pose test | Nonempty output at 0, ~3.32 and ~6.60 s |

The desktop images compare raw UV-V orientation and flipped V.
Raw/source V produced visibly more plausible texture placement for this
avatar example. That is **evidence for the chosen orientation**, not a
final proof of PS3 shader sampler state.

The animated example changes hand and arm positions and produces finite
vertices. **Original PS3 inverse-bind and blending conventions are still
unknown**. The previous animation analysis measured approximately
6.8 source-unit mean displacement from the static mesh, even at t=0,
so do not claim animation fidelity yet.

## Engineering and testing

- Portable CPU triangle module:
  [core/textured_triangles.c](../core/textured_triangles.c)
- Synthetic tests:
  [tests/test_textured_triangles.c](../tests/test_textured_triangles.c)
- Native Switch integration:
  [switch/source/textured_actor_main.c](../switch/source/textured_actor_main.c)
- Full build:
  `make -f switch/Makefile verify`

The C11 tests check actual UV interpolation, texture choice, draw bounds,
overlapping faces, z ordering and rejection of fully transparent texels.
AddressSanitizer and UndefinedBehaviorSanitizer run in CI.
The ninth NRO passes compiled ARM64/NRO structural validation.

## Remaining essential milestones

- Compare pose and camera to an original PS3 capture; correct coordinate
  conventions and inverse bind offsets if different.
- Support multiple DDS atlases and original materials within a model.
- Replace nearest-neighbor filtering, hard alpha cutout, orthographic
  projection and CPU rasterization with appropriate resolution-scalable
  Switch GPU shaders/lighting and proper transparency.
- Reconstruct map scenes, effects, environment, event scripting, combat
  systems and all original gameplay.
- Physically launch the NRO on a Nintendo Switch; record frame rate,
  memory, visual output and errors. CI success alone does not do this.
