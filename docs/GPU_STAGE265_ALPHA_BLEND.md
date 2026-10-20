# Stage265 — generated GPU straight-alpha blend on actual NeXium frames

Stage264 proved a binary fragment discard for fully transparent pixels, not
partial transparency. Stage265 adds a **separate opt-in** deko3d research NRO:

```sh
make -f gpu/blend_draw.mk verify
make -f gpu/Makefile triangle-verify
# build/foj-deko3d-alpha-blend-proof.nro
```

It uses the already verified shader (`foj_triangle.frag.dksh`) and
Stage263's Z24S8/GREATER depth image. Only with
`FOJ_GPU_ALPHA_BLEND` does it override the research draw order:
**opaque COOL rear material 1 drawn first, translucent WARM front
material 0 drawn second**. It binds real deko3d `DkBlendState`
SrcAlpha / InvSrcAlpha in RGB (default straight-alpha blending),
enables blending for the front draw, and disables depth writes on that
draw while retaining the depth test. The rear opaque draw has blending
off and depth writes on. All preexisting shaders and NRO targets retain
their unchanged behavior.

Only fabricated FOJRM001 / FOJMAT01 / classic RGBA8 DDS assets
are used. The near/far Z, camera, triangles, RGB and material indices
are identical across THREE separate virtual SD/NeXium runs; only the
entire near warm DDS alpha changes among **0, 128, 255**.

The independently predicted source-over RGB at the overlapping
screen-space probes (640,400) and (600,400) is:

| Warm alpha | Far COOL | Near WARM | Expected RGB at overlap |
|---|---|---|---|
| 0 | (21,202,219) | (232,55,28) | (21,202,219) |
| 128 | (21,202,219) | (232,55,28) | (127,128,123) |
| 255 | (21,202,219) | (232,55,28) | (232,55,28) |

A third probe at (760,400) must remain far COOL in all cases.
The independent verifier demands at least 116/121 correct RGB values
per probe, max channel tolerance 8 for half blend and 5 for controls,
and two actual NeXium screenshots per case (**six real PNGs**) with a
genuinely changed GPU clear-color background. The score is not derived
from GPU output; the oracle computes it mathematically from input RGBA.

Negative generated-only PIL fixtures reject source-over disabled,
wrong painter order, material swap, missing rear and non-independent
screenshots. Those fixtures are classifier tests, not emulator proof.

**Limits:** This tests only a single translucently rendered front
layer over a static opaque back layer with correct submission order.
It does not establish robust sorting for arbitrary transparent meshes,
multiple translucent layers, correct color-space/sRGB compositing,
the visual equivalence of original PS3 materials, true Switch hardware,
or a playable Vandal Hearts: Flames of Judgment port. Original game
assets never enter public CI, GitHub artifacts or repository commits.

The last Stage264 main-push rerun had 11/12 successes; inherited
Stage261 occasional same-background-phase failure is a preexisting
capture timing issue. The new Stage265 driver explicitly polls until
two different clear-color phases appear without relaxing the GPU pixel
oracle; it does not modify older test scenarios.
