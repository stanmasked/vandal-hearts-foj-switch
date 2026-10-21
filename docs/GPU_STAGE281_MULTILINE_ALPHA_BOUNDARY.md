# Stage281 — Multi-row GPU alpha boundary coherence

**Stacked base:** Stage280 [PR #165](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/165), exact-head `4d3297926c4c5ced03c83de8f5ead5eda5823bc9`, dedicated [3/3 CI #39601590817](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39601590817).

Stage280 established that changing the *source* alpha boundary from DDS U=40/64 to U=52/64 moved the *real* NeXium boundary 60 pixels along screen row Y=440, within the predeclared ~62-pixel UV projection tolerance. This is a synthetic research test, not a PS3 game.

## New Stage281 question

A single-row screenshot classifier cannot exclude a one-row-only artifact or an edge that jumps/disappears just above or below the sampled scanline. Stage281 holds **both generated DDS masks, all three actor triangles, shader binaries, native NRO, camera and GPU pass states unchanged** and acquires two fresh NeXium GPU frames in each case.

The added independent audit examines **five rows: Y=436, 438, 440, 442, 444** and all **27 consecutive X pixels** centered on each expected boundary (U40: X=618; U52: X=680). This is **270 RGB samples across the four real frames** (5×27×2×2), in addition to the original Stage280 source and control checks. It never infers a sampler configuration.

For every row it demands:
- Both physically composited alpha endpoints occur in the correct left-to-right order.
- Every RGB belongs to the physically possible source-over curve (three-channel projection, bounded residual) and samples remain monotone; a sharp step or valid filter transition is allowed.
- Half-opacity crossing stays within ±4 X pixels of the independent UV projection and crosses consistently across all five adjacent rows (range ≤4).
- The observed separation between U40 and U52 is **62±4 X pixels on every row**, not just Y=440.
- All five row profiles are identical in both distinct GPU clear-color phases within a given case.

The verifier first runs the **entire Stage280 independent audit** (source DDS hash before/after real guest, source manifest, native sort/alpha-pass-state receipts, per-frame GPU controls, distinct backgrounds, original Y=440 profile). Only then may Stage281 pass its additional rows.

## CI contract

[Dedicated Stage281 workflow](../.github/workflows/stage281-multiline-boundary.yml) runs the inherited native GCC/Clang C11 tests and Stage276–280 fixture tests, **10 new synthetic-only Stage281 negative/positive Python tests**, rebuilds the same NRO/DKSH with devkitA64, then launches two real NeXium guests and preserves all four original PNG captures and both Stage280/281 independent JSON receipts.

The additional tests deliberately corrupt off-center rows, RGB curves, monotonicity, temporal invariance, source hashes, native receipts and duplicate frames. Host mock PNGs never count as proof of actual GPU execution.

**Stage281 remains Draft until exact-head three-job CI succeeds and original generated-only screenshot archives are independently reviewed.** No original PS3 PKG contents, copyrighted textures or private data are included. This does not claim physical Switch execution, playable game status, arbitrary DDS compatibility or verified sampler filtering.
