# Stage287 — native C parity for the private three-DDS bridge

**Stacked on:** [Stage286 PR #171](https://github.com/stanmasked/vandal-hearts-foj-switch/pull/171), passing [Stage286 exact-head CI #39644590471](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39644590471).

## Why this matters

Stage286 verifies three owner-private DDS through Python intake, binds the two translucent and one opaque material to the invented FOJRM001/FOJMAT01 actor, and successfully creates a local SD fixture alongside authentic public DKSH shaders in devkitA64. Stage287 independently exercises the **actual native C implementation** `foj_gpu_private_bundle_load()` and `foj_gpu_opaque_rear_atlas()`, rather than trusting only Python-side predictions.

The generated fixture has exactly three invented 64×64 classic RGBA8 DDS images, the invented three-triangle actor and a public three-slot FOJMAT01 table. No game PKG, texture, executable, private source directory, shader or owner-owned content is read or uploaded. Test-generated files live solely inside ephemeral GitHub Actions runner storage.

## Checks

Compiled with GCC and Clang using C11, strict warnings, and `FOJ_GPU_THREE_LAYER_BLEND=1`.

The native loader must independently report:
- Nine GPU vertices and three batches.
- Texture bindings `0,1,2` with vertex ranges `0..2`, `3..5`, `6..8`.
- Material upload mask `7` and three decoded 64×64×4 RGBA8 surfaces.
- Correct first-pixel colors and alpha from *invented* violet/warm/cool textures.
- Entire rear atlas alpha=255 as verified by the production opaque-rear guard.
- Successful release of all retained pixel buffers and draw data.

Three negative fixtures must all be rejected: a damaged DDS header, a **single nonopaque texel at the end of the rear DDS**, and a material table mapping the third batch to the wrong texture.

The standalone C checker prints only generic PASS/reject markers, never pixel contents, hashes, source paths or actor structure.

## Evidence limitations

The C loader and Stage286 Python intake share the same research resource format but their successful interpretation of synthetic data **does not prove** an original FoJ PS3 format, a lawful original-resource conversion, a correct source-game material mapping, texture filtering behavior, a real NeXium GPU image using private data or physical Switch playback.

Original PS3 resources must remain in the owner's local, ignored directory. CI contains no original source files and uploads no DDS or output manifest artifacts.
