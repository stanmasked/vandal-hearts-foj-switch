# Full FoJ BMODEL mesh sections, skin weights and material links

**Research date:** 2026-10-16. Investigated directly from the user's original
PS3 `NPEB00148` split archive → `cdata.psarc`. The GitHub repository
contains only our parser, synthetic test fixtures and aggregate observations.
The commercial data and exported models remain outside GitHub.

This substantially extends the
[first-shape report](REAL_BMODEL_FIRST_SHAPE.md).

## Results across the complete original game archive

| Measurement | Confirmed observation |
| --- | ---: |
| .bmodel resources inspected | **583 / 583** |
| Geometric sections decoded structurally | **1,380** |
| Total triangles across **all** shapes | **583,431** |
| Models with bone-influence records | **87** |
| Shapes with bone-influence records | **275** |
| Model files with one shape | 336 |
| Models with multiple shapes | 247 |
| Material/texture link records | **895** |
| Unique texture basenames referenced | **370** |
| Texture link references found in PSARC | **895 / 895** |
| Header/array structural parsing errors | **0** |

Shape count varies from 1 up to 50 sections per model. Each observed mesh
section repeats the same big-endian XYZ/UV/normal/face-normal/index record
sequence; individual section boundaries are separated by marker `0x07`.
After each section, an `0x14` material name and `0x21`-prefixed six-float
bounds record are present. All 1,380 sections were traced through these
structures by a local independent validation probe.

### Skinning / vertex bone weight records

An optional `0x0F` record follows the triangle indices before the material
and bounds block.

| Field | Observed representation |
| --- | --- |
| Marker | `0F` |
| Next two bytes | uint16 BE: **total influence records** |
| Next two bytes | uint16 BE: **influences per vertex** |
| Each influence record | uint16 BE **bone index**, float32 BE **weight** |
| Invariant | total influences = number of vertices × influences/vertex |
| Per-vertex invariant | sum of weights ≈ 1.0 |

All 275 affected shape records pass the count check and all their vertex
weight sums are within 0.001 of one. Per-vertex influences range from
**1 to 5**. Counts of affected sections by influence count:

- 1 influence: 27 sections.
- 2 influences: 38 sections.
- 3 influences: 67 sections.
- 4 influences: 142 sections.
- 5 influences: 1 section.

This is **weight data**, not a complete skeleton. The corresponding bone
transforms, hierarchy, pose matrices and animation interpolation have not
yet been decoded.

### Material and texture table

After the final mesh section, `0x07` introduces a list of material entries.
Each `0x06` entry contains a length-prefixed material name and one or more
length-prefixed texture names. The observed materials refer to `.tga`
**filenames**, whose bytes can actually be legacy DDS images.

Across all 583 models, 895 individual texture-name links were found.
370 different texture basenames occur in these links.

Using *only* the bare filename, **752** links have one matching PSARC path,
and **143** have multiple matching PSARC paths (often an NPC and a prop
texture with the same name).

For **all 143 ambiguous links**, exactly one matching texture is located
in the **same PSARC directory as its .bmodel**. Choosing that match resolves
all 895 references without arbitrary filename guesses.

This is a validated **resource path resolution rule**, not proof that the
original renderer lacks additional per-material configuration.

### Undecoded trailing records

After the material bundle, 494 models continue with marker `0x0C` and
89 with `0x0A`. The semantics of those trailing records remain unknown.
**No animation skeleton, hierarchy or transforms should be inferred**
from their mere presence.

## Reproducible tools

- [Complete model parser](../tools/inspect_complete_bmodel.py):
  parses **all** mesh sections, validates skinning weights, records material
  references and resolves matching texture paths.
- [Aggregate BMODEL audit](../tools/audit_all_bmodels.py):
  validates multiple models and reports only counts and format checks.
- Generated-data regression suites:
  [test_inspect_complete_bmodel.py](../tests/test_inspect_complete_bmodel.py)
  and [test_audit_all_bmodels.py](../tests/test_audit_all_bmodels.py).

To reproduce aggregate findings on your own local split PKG ZIP:

```sh
python3 -m tools.audit_all_bmodels \
  "/path/to/NPEB00148.pkg.zip.001" \
  "/path/to/NPEB00148.pkg.zip.002" > local-bmodel-audit.json
```

To inspect one original model, without extracting any bytes:

```sh
python3 -m tools.inspect_complete_bmodel \
  "/path/to/NPEB00148.pkg.zip.001" \
  "/path/to/NPEB00148.pkg.zip.002" \
  --asset "data/actors/npc/avatar_body.bmodel" --json
```

To opt in to **local-only multi-shape OBJ export**:

```sh
mkdir -p local-data/models
python3 -m tools.inspect_complete_bmodel \
  "/path/to/NPEB00148.pkg.zip.001" \
  "/path/to/NPEB00148.pkg.zip.002" \
  --asset "data/actors/npc/avatar_body.bmodel" \
  --reverse-winding --flip-v --output "local-data/models/preview.obj"
```

The new OBJ includes all shape groups, XYZ, UVs, normals and original
**material labels**, but does not bundle textures or skeletons. It refuses
overwriting a previous local file. The native
[Switch OBJ wireframe viewer](OBJ_SWITCH_VIEWER.md) can load this multi-shape
OBJ after the user places it on their own SD card.

## First complete model tested visually

`data/actors/npc/avatar_body.bmodel`:

- **5** geometric sections; **4,722** vertices and **1,574** triangles.
- **14,166** individual skin-influence records.
- All sections refer to material `avatar_mat`, linked to
  `avatar_texture.tga`.
- The original atlas and all five mesh sections were loaded locally and a
  two-view diagnostic render was created.
- A private Blender-compatible OBJ/MTL/PNG bundle was built from the user's
  provided PS3 data, **never committed to GitHub**.

The visual reference is **not** a faithful game shader or rigged animation.
It uses a simple UV sample for each triangle rather than full per-pixel
filtering. Real shaders, skeleton and poses must be implemented separately.

## Remaining milestones

1. Understand `0x0A` / `0x0C` trailing blocks, original bone hierarchies
   and skin transforms.
2. Parse original `.banim` pose/keyframe streams and interpolate them.
3. Build a true textured triangle rasterizer (UV interpolation + depth
   buffer), then bring the original textured mesh to Switch using only
   user-provided local resource files.
4. Incorporate original map placements, cameras and authentic tactical
   engine callbacks.
5. Validate runtime/performance on actual Nintendo Switch hardware.

**This milestone decodes the static original mesh structure, not the
playable original PS3 game.**
