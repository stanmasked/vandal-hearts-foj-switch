# Eighth Switch NRO: original rigged character + matching BANIM

**Date: 2026-10-16.** This is the first NRO in this repository capable
of loading user-supplied *original FoJ character geometry, bone weights,
bone hierarchy and animation keys together*.

It does **not** contain any commercial game data, decrypted executables
or publisher asset files. It is a wireframe experiment, not a port of
the original PS3 rendering, animation blending or gameplay engine.

## Build and input contract

GitHub Actions builds **`foj-rigged-actor-research.nro`** as the eighth
standalone native libnx application, in the
`foj-switch-research-nros` artifact. The code is
[rigged_actor_main.c](../switch/source/rigged_actor_main.c).

The NRO expects two files **privately provided by the user** on the Switch SD:

```text
/switch/foj/rig/preview.fojrm
/switch/foj/anims/preview.banim
```

If either input is missing, malformed, too large or has incompatible bone
parents, a text diagnostic is displayed instead of presenting invented
data as the original actor. No automatic game download or decryption
occurs on Switch.

### Generate inputs from your own original PS3 package

With the user's `NPEB00148` two-part ZIP stored privately:

```sh
mkdir -p local-data/rig local-data/anims

python3 -m tools.export_local_rigmesh \
  "/path/to/NPEB00148.pkg.zip.001" \
  "/path/to/NPEB00148.pkg.zip.002" \
  --asset "data/actors/npc/avatar_body.bmodel" \
  --output "local-data/rig/preview.fojrm"

python3 -m tools.export_local_banim \
  "/path/to/NPEB00148.pkg.zip.001" \
  "/path/to/NPEB00148.pkg.zip.002" \
  --asset "data/actors/anims/avatar_idle.banim" \
  --output "local-data/anims/preview.banim"

python3 -m tools.check_local_rig_pair \
  local-data/rig/preview.fojrm \
  local-data/anims/preview.banim
```

These tools refuse overwriting already existing files. The private
`local-data/` directory is excluded from Git; never add the resulting
`.fojrm`, `.banim`, PKG, textures or proprietary bytes to GitHub.

Copy the two generated files to the corresponding paths on your own SD
card. A prearranged private user-data ZIP with this exact folder structure
can also be copied to the SD card; the ZIP itself belongs only in your
local storage, not the source repository.

## Experimental viewer controls

| Control | Function |
| --- | --- |
| A | Play or pause |
| B | Reset to zero seconds and pause |
| D-pad left/right | Rotate camera |
| D-pad up/down | Camera elevation |
| ZR / ZL | Zoom |
| Plus | Exit |

The amber indicator signals that **real user-provided data is loaded but
the skinning and pose interpretation is experimental**.

The application uses the portable source C modules:

- [rigmesh_io.c](../core/rigmesh_io.c) — validates local FOJRM001 format,
  bone bounds, section order, float values and weight normalization.
- [banim_core.c](../core/banim_core.c) — original BANIM keyframe parsing
  and local quaternion/translation interpolation.
- [skeletal_skin.c](../core/skeletal_skin.c) — experimental hierarchical
  world transforms, inverse bind palette and weighted CPU vertex positions.
- [obj_wireframe.c](../core/obj_wireframe.c) — CPU wireframe rendering
  without original DDS materials, lighting or depth buffer.

## FOJRM001 portable rig mesh layout

All multi-byte integers and floats are **little-endian**.

| Layout | Size | Content |
| --- | ---: | --- |
| Header | 28 B | `FOJRM001` magic, version=1, bone count, vertex count, section count, flags=0 |
| Bone record | 32 B each | signed parent (-1 = root), quaternion XYZW, translation XYZ |
| Section record | 8 B each | first vertex index, count, both uint32 |
| Vertex record | 76 B each | XYZ, UV, normal (8 float32 values); uint32 influence count; five fixed (uint32 bone, float32 weight) pairs |

The loader limits count to 256 bones, 20,000 vertices and 64 sections,
maximum file size 2 MB. Vertices are triangle soup (each section count
divisible by 3); all shape sections must be contiguous.

This is a **private conversion format**. The native program does not
directly parse PS3 BMODEL or mount PKG/PSARC archives on Switch.

## First genuine model + clip private validation

Read directly from the user's original PS3 archive and checked against
this format:

| Sample | Verified |
| --- | ---: |
| `avatar_body.bmodel` | 5 shapes; 4,722 vertices; 1,574 triangles |
| Bind rig | 28 bones |
| Weighted geometry | All 4,722 vertices, 14,166 bone influences |
| `avatar_idle.banim` | 28 tracks; 5,600 keyframes |
| Clip duration | ~6.6333 seconds |
| Bone parent arrays | **28/28 exact match** |
| Private exported FOJRM001 | **359,836 bytes** |
| Private original BANIM | **184,952 bytes** |

An **independent desktop diagnostic** sampled the same model and original
clip at times **0.0, 3.317 and 6.603 seconds**, and drew three wireframe
poses. All 4,722 positions remained finite and moved in a connected
skeletal geometry structure. However, the mean displacement from the
source mesh was approximately **6.78, 6.96 and 6.74 source units**
respectively — substantial enough that the original PS3 matrix
convention/pose offsets must be checked visually before declaring the
render faithful.

Neither the existence of sampled motion nor matching bone parent arrays
proves correct original engine behavior. The visual result should be
compared to actual PS3 captures at identical timestamps, after
establishing the correct bind frame and coordinate transforms.

## Verification levels and outstanding work

- **Confirmed:** file converter and C parser pass synthetic tests and
  bounds/sanitizer regression; original sample's parent and weight
  invariants have been independently checked locally.
- **Confirmed:** the eighth ARM64 NRO is compiled by devkitA64 and passes
  executable container structure validation.
- **Not confirmed:** physical Switch launch/frame rate or visual equivalence
  to the PS3 animation and materials.
- **Not implemented:** accurate original FoJ lighting/shaders,
  full per-pixel DDS UV interpolation, rendering depth buffer, map and NPC
  placement, event scripts, original tactical gameplay, AI and campaign.

The next priority is determining original bind-pose conventions and
adding GPU/CPU textured triangle rendering, while retaining user-local
game data separation.
