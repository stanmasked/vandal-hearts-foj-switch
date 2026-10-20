# Stage267 — actual three-material deko3d source-over alpha experiment

This **Draft**, stacked above Stage266 (#150) and Stage265 (#149),
expands the existing GPU research NRO to one opaque rear triangle and
**two translucent triangles**. Only invented FOJRM001/FOJMAT01 and
generated RGBA8 DDS samples are used. All original PS3 resources remain
outside GitHub and CI.

## Isolated NRO

```sh
make -f gpu/three_layer_blend.mk verify
make -f gpu/Makefile triangle-verify
# build/foj-deko3d-three-layer-blend-proof.nro
```

The opt-in `FOJ_GPU_THREE_LAYER_BLEND` build enables three private
texture slots only inside this target. The three contiguous geometry
sections arrive in semantic order: violet (0), warm (1), cool (2).
GPU commands **submit the opaque cool rear first (material 2)** with
Z-test GREATER and depth-write enabled, then warm (1) and violet (0)
back-to-front with depth test enabled, depth-write disabled, and
straight SrcAlpha/InvSrcAlpha RGB blending enabled. The other NRO
configurations and Stage265's two-slot draw command remain unchanged.
The research stream maps their distinct camera depths into GPU [0,1].

Stage267's 3-slot intake is fail closed: it requires all 3 DDS files,
the matching three-section actor/material table, and both UAM DKSH
shader modules. A unique temporary root is generated per emulator run,
never copying users' private game data into public Actions.

## Independent RGB acceptance

All three cases use *identical* geometry/UVs/camera and input RGB. Only
near violet or middle warm alpha changes.

| Generated case | Near violet alpha | Middle warm alpha | Opaque cool alpha | Expected overlap RGB |
|---|---:|---:|---:|---|
| both-half | 128 | 128 | 255 | (111,100,162) |
| no-middle | 128 | 0 | 255 | (59,137,210) |
| no-near | 0 | 128 | 255 | (127,128,123) |

The COOL-only wing must remain (21,202,219) for every case.

GitHub Actions has separate stages for real **devkitA64 NRO/UAM
compilation** and real **NeXium guest execution**. The latter must
capture two different clear-color phases per case, at genuine
1280×720 framebuffer size. The independent RGB pixel checker requires
at least **116/121** correct pixels at each of two overlap regions and
an unaffected rear-only wing, with absolute per-channel tolerance 8.
The six screenshots and JSON receipt are uploaded as artifacts only
when the guest process runs; Python/PIL fixtures exercise the verifier
but **do not** establish real emulator output.

Run host-only tests:

```sh
python3 -m unittest discover -s tests/emulator -p 'test_stage267_gpu_three_layer.py' -v
```

## Hard limitations

Even if CI succeeds, this establishes only ordered compositing of two
flat, mutually non-intersecting transparent triangles over one opaque
triangle with known scalar depth. It does not establish unsorted scene
rendering, intersecting polygons, original FoJ gameplay or PS3 shader
semantics, arbitrary depth peeling, correct linear/sRGB blending, or
compatibility with retail Nintendo Switch hardware.

Until an Actions guest job actually passes, **the three-layer RGB
numbers above are mathematical reference values, not measured pixels**.
Do not merge the stacked PRs until all inherited and new CI regressions
pass and real GPU evidence exists.
