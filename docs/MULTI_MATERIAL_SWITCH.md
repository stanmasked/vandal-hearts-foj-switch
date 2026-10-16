# Native multi-material DDS atlas rendering for FoJ models

**Verified on 2026-10-16** by rereading all **583** original BMODEL
resources in the user's NPEB00148 package → cdata.psarc. Neither original
DDS pixels nor model geometry is committed to GitHub.

## Evidence from the real archive

| Property | Original models |
| --- | ---: |
| Total examined | 583 |
| 1 material | 394 |
| 2 materials | 118 |
| 3 materials | 53 |
| 4 or more materials | 18 |
| 1 *distinct texture atlas* | **463** |
| 2 distinct atlases | **67** |
| 3 distinct atlases | **42** |
| 4 distinct atlases | 7 |
| 5 distinct atlases | 1 |
| 6 distinct atlases | 2 |
| 8 distinct atlases | 1 |

**189 models have multiple material records, but only 120 actually
reference multiple *different texture files*.** The other 69 models
reuse the same texture under different material names, commonly for
two-sided geometry, capes, or other distinct shader parameters.

Among 89 models with an embedded BMODEL skeleton, 6 refer to multiple
unique DDS atlases. These are the immediate candidates for verifying
the **skinned + multi-texture** path in the ninth NRO.

All 583 original models have at most eight distinct texture basenames;
therefore, the new research atlas-slot format covers this observed
dimension of the original asset catalog. This does **not** imply the
whole game renders, that all models fit in 20,000 vertices, or that
material/shader fidelity is achieved.

One verified grounded example:
`data/actors/npc/cape_daldren_stone.bmodel` has **6 original sections**
and 3 material entries, but only **2 actual DDS atlases**:
`daldren_texture.tga` and `stone_of_judgment.tga`.
Different material names for the cape/body share the first DDS.

## End-to-end verification with original Daldren character

The first **real two-atlas model** was also decoded and rendered locally
with the user's original protected PS3 resources:

- Original BMODEL: `data/actors/npc/cape_daldren_stone.bmodel`.
- **6 shapes, 9,066 vertices, 3,022 triangles**.
- Material assignments: `daldren_mat`, `daldren_twosided`,
  `stone_mat`. The first two share the same DDS.
- Two actual 256×256 DDS files:
  `data/actors/npc/daldren_texture.tga` and
  `data/actors/npc/stone_of_judgment.tga`.
- Original embedded skeleton: **50 bones**.
- `data/actors/anims/cape_daldren_judgement.banim` has **50 tracks
  matching the complete model parent array**. This is a structural
  compatibility result, not confirmation of scene association or a
  PS3-accurate movement.
- A user-private `FOJRM001` original-model conversion and
  `FOJMAT01` two-texture mapping have been generated and checked.
- Three computer-rendered static camera angles visibly show gold armor,
  red cape and the separate stone using the correct respective atlas.
  The desktop probe **composes per-section depth results**, consistent
  with the new native shared-depth implementation; it is not evidence
  of Switch hardware rendering.

No asset pixels, rigged original mesh bytes, BANIM clip or rendered
commercial image has been committed to GitHub. The original static model
preview and private SD bundle are available **only in the user's
conversation artifacts**.

## Portable research implementation

- [core/material_table.c](../core/material_table.c): bounded, strict
  binary table parser.
- [core/textured_triangles.c](../core/textured_triangles.c): multi-section
  triangle rendering with a **single shared depth buffer** and individual
  texture slots.
- [tools/export_local_material_pack.py](../tools/export_local_material_pack.py):
  user-initiated PS3 original material/texture path resolution and private
  export of each required DDS atlas.
- [switch/source/textured_actor_main.c](../switch/source/textured_actor_main.c):
  the **existing ninth NRO** now accepts optional multi-material input.
- [tests/test_material_table.c](../tests/test_material_table.c),
  [tests/test_export_local_material_pack.py](../tests/test_export_local_material_pack.py)
  and [tests/test_textured_triangles.c](../tests/test_textured_triangles.c)
  validate format safety, path resolution, depth across material switches,
  no-overwrite behavior and malformed inputs.

### FOJMAT01 format

This is **our own local research format**, not an original PS3 format.
The complete file is:

```text
8 bytes        ASCII "FOJMAT01"
4 bytes LE     original mesh section count (1..64)
4 bytes LE     unique DDS texture count (1..8)
4 bytes LE × N texture slot index (0..texture_count-1) for each section
```

Every texture slot must be referenced; the sections refer to the ordered
sections in the user's private `FOJRM001` mesh. The native program
validates exact section-count equality, then loads local
`texture_00.tga`, `texture_01.tga` ... in that order.

## Prepare a private material bundle

For a user-owned PS3 archive:

```sh
mkdir -p local-data/textures
python3 -m tools.export_local_material_pack \
  "/path/to/NPEB00148.pkg.zip.001" \
  "/path/to/NPEB00148.pkg.zip.002" \
  --asset "data/actors/npc/cape_daldren_stone.bmodel" \
  --output-dir local-data/textures
```

This produces (depending on the model) `preview.fojmat` and up to eight
`texture_XX.tga` files. The original DDS bytes are validated and
exported **only locally**, and existing output files are not overwritten.

For Switch, copy the local results into:

```text
/switch/foj/textures/preview.fojmat
/switch/foj/textures/texture_00.tga
/switch/foj/textures/texture_01.tga
...
```

The ninth NRO also requires `/switch/foj/rig/preview.fojrm` and a
compatible `/switch/foj/anims/preview.banim`. Both must correspond to
the intended actor; an equal bone hierarchy is a necessary but
insufficient condition to guarantee the original animation association.
See [the original actor setup guide](TEXTURED_ACTOR_SWITCH.md).

If **no** `preview.fojmat` is present, the ninth NRO falls back to the
existing single-atlas `preview.tga` for all shape sections. If a
`preview.fojmat` **is present but invalid/incompatible**, it rejects the
input rather than silently rendering all sections with a wrong texture.

## Limitations

The renderer is still **orthographic CPU research** with nearest-neighbor
UV sampling and binary alpha cutout, not the Nintendo Switch GPU graphics
pipeline. It does not yet reproduce original material parameters:
two-sided rendering, blending, opacity, emissive/lightmap flags, lighting,
normal maps, filtering or PS3 gamma/shading. It has no physical-console
frame-time measurements yet.

**Priority next:** test a two-atlas animated actor in the ninth NRO on
Switch, measure frame time, then migrate the verified material/triangle
feed to GPU rendering. This is not an original PS3 engine or playable game.
