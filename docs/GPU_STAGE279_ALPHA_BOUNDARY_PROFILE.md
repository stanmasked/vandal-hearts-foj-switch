# Stage279 — Real GPU Transparency Boundary Profile

**Verified base:** [Stage278 exact-head CI #39595379714](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39595379714) passed 3/3 dedicated jobs, with four independently audited NeXium frames showing four constant-alpha bands. Stage279 uses the **identical** native NRO and DKSH shaders, changing only the public, synthetic RGBA8 DDS fixture and its verification harness.

## New question

A real game texture can contain a boundary between transparent and opaque texels. Stage278 validated the interior of four alpha bands; it deliberately did **not** test pixel behavior at the discontinuities. Stage279 measures the **actual rasterized spatial alpha profile** across a single hard 0↔255 transition at DDS U=48/64 = 0.75.

Two fresh generated-only SD roots contain the same original three-triangle actor, the same opaque cyan rear and half-alpha warm middle material, and the same violet near-material RGB (96,72,201):

| Case | DDS x=0–47 | DDS x=48–63 |
|---|---|---|
| `boundary-clear-left` | alpha 0 | alpha 255 |
| `boundary-clear-right` | alpha 255 | alpha 0 |

Only the 4096 alpha bytes of near `material0.dds` differ from the reference uniform alpha128; no RGB or header bytes are changed. Input SHA-256 is checked against the generated formula **before and after** each guest, not trusted from a manifest alone.

## Framebuffer proof, deliberately without a sampler-mode assumption

The source-over baseline calculated independently with the Stage266 model is RGB (127,128,123) for **alpha 0** and (96,72,201) for **alpha 255**. The two stable 9×9 control probes at (647,400) and (673,400) must have the expected appropriate endpoint color (at least 75/81 pixels within ±8 RGB), and the rear-only probe (760,400) remains RGB (21,202,219).

The new profiler samples **27 consecutive real framebuffer pixels x=647..673 at y=400** across the transition. It projects each observed RGB sample onto the expected three-channel alpha-blend vector and independently requires:

- The profile moves monotonically from one correct endpoint to the other; inverted case reverses direction.
- Each sample stays within the source-over color envelope (per-channel residual ≤8), rejecting false black stripes, wrong material colors or contradictory sources.
- The 50%-opacity crossing occurs in a grounded window x=654..667, near the measured geometric U=0.75 crossing at x≈660.
- Any intermediate 10–90%-opacity region, if present, remains confined to the expected neighborhood rather than leaking across most of the polygon.
- Both inversion cases and both framebuffer phases must be present, with the same material profile but a distinct GPU background clear color.

**This experiment does not assert nearest or bilinear texture filtering by name.** Nearest-neighbor-like and filtered transition profiles can both pass if they satisfy the physical monotonicity and color-envelope controls. The profiler reports the number of intermediate samples and the observed transition pixel; it leaves `sampler_filter_mode` explicitly `NOT_INFERRED`. Identifying the configured sampler's filter through GPU API introspection is a separate follow-up.

## CI and provenance

[Stage279 CI](../.github/workflows/stage279-alpha-boundary.yml) rebuilds the unchanged research NRO using devkitA64 and reruns earlier native C11 GCC/Clang material/alpha/DDS tests, including Stage278, plus **10 new Stage279 regression tests**. The new suite compiles the production C11 DDS decoder with both compilers, compares the full 4096-pixel binary-alpha source mask, checks truncated-input rejection without output modification, tests source-over mock profiles (including nearest-like and gradual transitions), and rejects forged markers, oscillations, wrong crossing position and stale frames.

Two **actual NeXium guest runs**, with **four genuine 1280×720 frame captures**, are required. Each new SD root must be generated from public fixtures. Guest must write exact native `FOJ_NATIVE_SORT_V1 2,1,0\n` and `FOJ_NATIVE_ALPHA_PASS_V1 2:0:1:1 1:1:1:0 0:1:1:0\n`, while contradictory rear-alpha and topology-reject witnesses are forbidden. The independent final Python checker recomputes byte-level DDS identities and inspects every pixel of the preserved four frames.

**Status:** Draft until its exact-head dedicated CI and original NeXium artifact ZIP are independently audited. Mock screenshot tests never constitute guest proof. No PS3 PKG, copyrighted assets or user-private data are stored in the repository. This does not demonstrate original game rendering, physical-console operation or a playable port.
