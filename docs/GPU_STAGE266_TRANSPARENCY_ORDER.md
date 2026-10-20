# Stage266 — multi-layer transparency ordering (CPU oracle only)

Stage265 demonstrates one generated translucent surface over a generated
opaque surface on deko3d/NeXium. Stage266 starts with a **host-only**
reference plan for one opaque rear layer and up to two translucent nearer
layers. No new NRO, shader, actual emulator capture, PS3 resource, or real
Nintendo Switch test is included in this pull request.

The renderer uses the experimental Stage263 GREATER convention: a larger
normalized depth is nearer. The plan submits the opaque rear first,
**with depth test and writes enabled, blending disabled**, followed by
translucent surfaces in increasing depth order (back-to-front), **with
depth test enabled, depth writes disabled, and straight-alpha RGB blending
enabled**.

For the invented three-layer scene:

| Draw | Depth | RGB | Alpha | Depth write | Blend |
|---|---:|---|---:|---|---|
| Rear COOL | 0.20 | (21,202,219) | 255 | on | off |
| Middle WARM | 0.55 | (232,55,28) | 128 | off | on |
| Near VIOLET | 0.85 | (96,72,201) | 128 | off | on |

Per-pass normalized SrcAlpha / InvSrcAlpha source-over RGB with 8-bit
framebuffer rounding predicts `(111,100,162)` after both translucent draws.
The one-transparent-layer regression retains Stage265's predictions:
alpha 0 → `(21,202,219)`, alpha 128 → `(127,128,123)`, alpha 255 →
`(232,55,28)`.

Run:

```sh
python3 -m unittest discover -s tests/emulator -p 'test_stage266_transparency_order.py' -v
python3 -m tools.foj_stage266_transparency_order
```

This oracle intentionally fails closed on duplicate depth/name, invalid
RGBA8, missing/transparent rear, missing depth testing, wrong blend/depth
write states, and reversed front layer order. Tests also cover zero-alpha,
full-alpha, and input-order independence.

**Scope limit:** one scalar depth per isolated generated layer; no
intersecting geometry, per-triangle sorting, depth peeling, alpha-to-coverage,
proper sRGB composition, real FoJ materials, or GPU/NeXium evidence for
multiple translucent layers yet. The next independent milestone must build
a real three-layer GPU scene and check captured NeXium pixels against this
CPU reference before this capability can be called hardware-validated.
