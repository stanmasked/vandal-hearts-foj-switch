# Ground-truth first 3D mesh layout: all 583 FoJ BMODEL files

**2026-10-16.** Verified directly from the user's original European
`NPEB00148` split PS3 ZIP → debug PKG → `cdata.psarc`. No actual
model vertices, textures, animation bytes or game executables are committed.

This is a substantial advance over [header reconnaissance](REAL_MODEL_ANIM_HEADERS.md):
**the first mesh section of every one of the 583 model resources can now be
parsed**, including actual float32 vertices, UV coordinates, normals, triangle
normals and indices. Later records within each multi-section model remain
undecoded.

## Structural validation across the full resource archive

| Check | Result |
| --- | --- |
| Original files processed | **583 / 583** |
| First-shape array structure matched | **583 / 583** |
| First-section triangle count in total | **320,810** |
| Largest first-section vertex count | **15,747** |
| Smallest first-section vertex count | **3** |
| Triangle counts | `vertex_count / 3` for every first section |
| Index buffers | Big-endian 16-bit, sequential 0…vertex_count−1 in tested sections |
| Numeric representation | IEEE 754 **big-endian float32** |
| Models with zero-length vertex normals | **3** |
| Individual zero-length vertex normals | **196** |
| Nonzero vertex normals | Unit length within floating-point tolerance |
| Stored face normals | Unit length within floating-point tolerance |

## Observed byte records

The original model starts with `0B 09 00`, followed by a small integer
(candidate component count), then `01 20 00`, a one-byte name length, and
the first shape's UTF-8 name.

For **the first shape** the records appear consecutively:

| Tag | Next bytes | Decoded representation |
| --- | --- | --- |
| `0x02` | 16-bit BE `N` | `N` triples of big-endian f32 **positions** `x,y,z` |
| `0x05` | 16-bit BE `N`, `00 03` | `N` pairs of big-endian f32 **UVs** `u,v` |
| `0x10` | 16-bit BE `N` | `N` triples of big-endian f32 **vertex normals** |
| `0x15` | 16-bit BE `N/3` | `N/3` triples of big-endian f32 **face normals** |
| `0x04` | 16-bit BE `N` | `N` big-endian 16-bit **indices** |

Following these five array sections, an `0x0F`-prefixed field is frequently
seen. Its nested semantics (materials, extra weights, skinning, additional
shapes, etc.) are **not** recovered yet.

## Face winding and real exceptions

For all first-shape triangles where geometry yields a nondegenerate cross
product, **320,683** stored face normals are anti-aligned with the positive
cross product from the sequential vertices within a 0.98 dot-product
threshold; **0** are aligned, **122** are less closely anti-aligned, and
**5** triangles are near-degenerate using the 1e−5 cross-magnitude threshold.

This is strong evidence that an OBJ exporter will commonly need to flip
triangle winding to align visible faces and stored normals. The converter
therefore offers optional `--reverse-winding`; the raw indexing is
preserved by default.

**196 zero-length vertex normals** occur in three real models:
`catapult.bmodel`, `iron_maiden_close.bmodel`, and
`skeleton_01.bmodel`. These are legitimate input variants; a correct
parser should preserve zero values rather than rejecting the models.

## First actual mesh rendered

File: `data/actors/npc/archery_target_character.bmodel`

- First shape: `archery_targetShape_0`
- **1,167 vertices, 389 triangles**
- Geometry bounds `x` ≈ −10.813…0.616, `y` ≈ −0.883…23.991,
  `z` ≈ −12.214…12.704.
- All sampled UV pairs fall within 0…1.
- A local, independently generated 3D diagnostic view displays the genuine
  mesh from two camera angles. Provisional atlas colors were derived by
  sampling the *user's locally held* `archery_target.tga` DDS asset at each
  triangle's UV centroid.

The 3D preview is **not** proof of correct in-game shaders, materials,
texture filtering, per-vertex interpolation, scene transforms, lighting or
Switch hardware rendering.

## Tool and reproducible command

The safe source-code-only decoder is
[tools/decode_bmodel_geometry.py](../tools/decode_bmodel_geometry.py).

Summary only (no exported asset):

```sh
python3 -m tools.decode_bmodel_geometry \
  "/path/to/NPEB00148.pkg.zip.001" "/path/to/NPEB00148.pkg.zip.002" \
  --asset "data/actors/npc/archery_target_character.bmodel"
```

To opt in to **local-only** export of the first shape to OBJ:

```sh
mkdir -p local-data/models
python3 -m tools.decode_bmodel_geometry \
  "/path/to/NPEB00148.pkg.zip.001" "/path/to/NPEB00148.pkg.zip.002" \
  --asset "data/actors/npc/archery_target_character.bmodel" \
  --reverse-winding --output "local-data/models/archery_target_first.obj"
```

The exporter requires a **new, explicit output path**, refuses overwriting,
and never writes game bytes to GitHub. Test fixtures in
[tests/test_decode_bmodel_geometry.py](../tests/test_decode_bmodel_geometry.py)
are wholly synthetic.

### Limitations before claiming a playable port

The research decoder currently handles only the *first* shape. It does not
automatically reconstruct entire characters with multiple shapes, original
material assignments, morphs, weights, skeleton, animations, camera,
gameplay, AI or map events.

Next step: decode subsequent `0x0F`-prefixed fields and locate next shape
record boundaries, followed by local C/ARM64 triangle rendering of the
user-owned OBJ or a verified portable binary mesh format.
