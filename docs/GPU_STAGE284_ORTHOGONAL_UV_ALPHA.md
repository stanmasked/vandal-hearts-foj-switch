# GPU Stage284 — Orthogonal U/V alpha boundaries in one generated DDS

**Stacked on:** [Stage283 PR #168](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/168), exact-head [3/3 CI #39625979479](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39625979479).

Stages280–283 verified U-driven horizontal displacement, row coherence, V-driven vertical displacement, and three-point V-axis linearity using separate generated DDS masks. Stage284 combines both axes into one RGBA8 DDS and one native material.

## Source mask and expected screen-space edges

The 64×64 generated texture changes only the 4096 alpha bytes from the canonical violet-alpha128 DDS. Its alpha is 0 when x<46 OR y<46, and 255 only in the lower-right quadrant where both coordinates are at least 46. DDS RGB and header bytes, actor geometry/UVs, NRO, shaders, camera, depth, sorting, blending and rear/middle materials remain unchanged.

| Probe | Source edge | Expected screen crossing |
|---|---|---:|
| Horizontal profiles at capture rows 439, 440, 441 | U = 46 | X ≈ 649 |
| Vertical profiles at capture columns 682, 684, 686 | V = 46 | Y ≈ 395 |

The U profiles are sampled below the V boundary so the U transition is visible. The V profiles are sampled just to the right of the U boundary so the V transition is independently visible. This is an orthogonal cross-mask, not a claim about texture filtering.

## Real guest evidence

The dedicated workflow builds the unchanged Stage275 research NRO, launches one real NeXium guest with the generated-only mask, and captures two distinct RGB frames. It checks 3 U rows × 27 X samples and 3 V columns × 27 Y samples in each frame, 324 measured RGB samples total.

The auditor requires:
- Both edge transitions to be monotone and consistent with the physically possible straight-alpha source-over RGB trajectory.
- U crossing at X≈649 across all three rows and V crossing at Y≈395 across all three columns.
- Clear/opaque endpoint controls on each axis and an unchanged rear-only color control.
- The measured 694-pixel capture viewport, two distinct frame phases, and unchanged material profiles between frames.
- Exact generated DDS SHA-256 before and after the guest, native sort receipt 2,1,0, native blend/depth receipt, and no contradictory native rejection markers.

Mock-image tests exercise the auditor but never count as GPU proof. No original PS3 resources are included; sampler filtering mode remains NOT_INFERRED. This experiment does not establish original-game texture behavior, a complete/playable Switch port, or physical-console execution.

## Acceptance

[Dedicated workflow](../.github/workflows/stage284-uv-cross.yml) runs GCC/Clang C11 checks, inherited Stage280–283 regressions, Stage284 host tests, devkitA64 NRO/DKSH validation, and the real NeXium evidence audit.
