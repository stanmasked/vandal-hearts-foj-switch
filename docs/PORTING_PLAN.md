# Porting plan (research gates)

## Target

Create a native **Nintendo Switch homebrew** implementation of
*Vandal Hearts: Flames of Judgment*, preserving the original game experience
to the extent technically and legally feasible.

PS3 Cell/PowerPC binaries **cannot** simply be relabeled as Switch ARM64 NROs.
The source code has not been obtained. A recreation/port may require substantial
reverse engineering, new platform code, and clean-room implementations.

## Milestones

### Gate 0 — Package identification (completed)
- [x] New independent GitHub repository.
- [x] Read-only PKG header parser and synthetic tests.
- [x] Read original uploaded ZIP as a virtual concatenated stream; full CRC32 matched.
- [x] Confirm raw package magic, non-finalized revision, type, content ID, bounds and SHA-256.
- [x] Save a redacted/asset-free technical report ([verified results](REAL_PKG_NPEB00148.md)).

**Exit criterion:** reproducible report for a real file; no proprietary data in Git.

### Gate 1 — Asset and engine feasibility (in progress)
- [ ] Establish lawful access to game resources for local research.
- [x] Prepare local-only, signatures-and-extensions inventory tool with synthetic tests.
- [x] Recover names and extents of 21 actual PKG items and the 3,212-entry PSARC manifest.
- [x] Verify PSARC/zlib layout and discover Lua, models, animations, texture and map filenames.
- [x] Summarize the first original 50×50 map's collision, visibility and placement structures.
- [x] Add portable C grid loader for observed COLL schema, plus generated 50×50 strict/sanitizer tests.
- [x] Compile a separate native Switch COLL heatmap inspector NRO (runtime still to be tested).
- [x] Validate five original BGRA8/DXT1 textures locally and publish format-only findings.
- [x] Add portable C DDS decoder, generated regression tests, and native viewer NRO.
- [x] Recover first-section XYZ/UV/normals/face normals/index data in all 583 original .bmodel files.
- [x] Export one original 3D model locally as OBJ and create a diagnostic render.
- [x] Compile a fifth native libnx NRO for a user-provided local OBJ wireframe.
- [x] Decode all 1,380 original mesh parts across 583 BMODEL files (583,431 triangles).
- [x] Validate 275 per-vertex bone-influence tables from 87 original models.
- [x] Resolve 895 genuine material/texture links including 143 same-name ambiguities.
- [x] Export a five-section authentic avatar as OBJ/MTL/PNG privately for Blender.
- [x] Update native Switch OBJ wireframe reader to accept material directives.
- [x] Recover BMODEL 0x0A bone hierarchy, quaternion/translation transforms (89 rigs, 2512 bones).
- [x] Parse all 450 BANIM clips into 16631 tracks / 1274805 validated keyframes.
- [x] Add portable C BANIM parser and shortest-path quaternion interpolation tests.
- [x] Compile sixth Switch NRO that reads user-local BANIM and samples track poses.
- [x] Match full parent hierarchy of 89 original BMODEL rigs against 449/450 BANIM clips.
- [x] Verify original skin weights reference in-range bones in all 87 weighted models.
- [x] Implement clean-room inverse bind palettes and 1–5 influence linear-blend skinning.
- [x] Compile a seventh ARM64 Switch NRO showing synthetic deforming two-bone mesh.
- [x] Add user-local original rigged mesh export (FOJRM001) with all sections, UV and bone weights.
- [x] Add strict portable C FOJRM001 loader, generated regression tests and sanitizer checks.
- [x] Privately pair original avatar_body (28 bones, 4722 vertices) with avatar_idle (28 tracks, 5600 keys).
- [x] Build eighth native ARM64 NRO that can consume actual user-local BMODEL-derived mesh and BANIM clip.
- [x] Produce three experimental desktop snapshots of source geometry animated by real BANIM keys.
- [x] Add portable C CPU rasterizer with interpolated UVs, alpha cutout and per-pixel depth buffer.
- [x] Decode original avatar_texture DDS 1024×1024 and render authentic original static mesh with it.
- [x] Produce experimental original-textured avatar_idle poses at 0, 3.317 and 6.603 seconds on desktop.
- [x] Compile ninth native NRO accepting private rigged mesh, BANIM clip and DDS atlas together.
- [x] Re-audit all 583 PS3 BMODEL material tables: 120 genuinely multi-atlas models, six with embedded skeletons.
- [x] Add private FOJMAT01 section-to-DDS mapping and user-local multi-atlas exporter.
- [x] Add shared-depth multi-texture triangle drawing to ninth native Switch NRO.
- [x] Add portable GPU-oriented XYZW/UV vertex + texture-batch preparation; test locally with C11, ASan and UBSan.
- [x] Validate real Daldren private geometry conversion (9066 vertices, six batches, two DDS atlases, all finite).
- [x] Add separate source-only UAM shader prototypes and optional shader-only Makefile.
- [x] Correct GPU Z projection to deko3d default [0,1] for single-model render: validate 9066 Daldren vertices; GREATER/clear 0 contract.
- [x] Add structural DKSH validator and synthetic integrity tests, invoked by optional UAM Makefile.
- [x] Implement separate source-only deko3d device, double-buffered RGBA8 swapchain, GPU clear queue and present loop without game assets.
- [x] Add optional GPU-only devkitPro debug build Makefile and isolated Actions workflow (first run failed before any steps; no GPU build success).
- [x] Match upstream deko3d static command-list lifecycle; pre-record 4 immutable 2-framebuffer × 2-color GPU clear commands.
- [x] Use correctly aligned GPU image allocations, full-screen scissor and GPU-only image memory flags.
- [x] Add devkitPro-free host-check with locally run C11 + ASan/UBSan tests of allocation and palette scheduling.
- [x] Execute real optional GPU smoke C entrypoint against host-only deko3d/libnx stateful fake; validate 242 frames and four GPU command lists.
- [x] Inject nine GPU allocation/queue/acquire failures; confirm no live mock resources after exit and pass C11/ASan/UBSan.
- [x] Wire mock API smoke verification into standalone Makefile and future GitHub CI (not yet run on GitHub due to zero-step failure).
- [x] Mock deko3d/libnx public calls while compiling the real optional GPU smoke entrypoint on desktop; 242 frame cycles, 9 simulated failures, and Plus exit exercised.
- [x] Validate no live resources in 11 host mock scenarios; strict C11 and ASan/UBSan passed locally, CI steps registered pending runner recovery.
- [ ] Produce and launch the optional GPU clear NRO on physical hardware, verify color-changing frame and Plus exit.
- [ ] Verify native UAM shader compilation, implement deko3d GPU draw calls and display actual frames on Switch.
- [ ] Reproduce PS3-original shader/sampler material parameters, pose and camera conventions.
- [ ] Validate actual FoJ pose composition, bind conventions, material mapping and skinned movement.
- [ ] Establish full semantic meanings for proprietary resource formats and original battle rules.
- [x] Identify BGRA8 and DXT1 DDS texture formats and validate actual images.
- [x] Identify recurring .bmodel and .banim header fields in bounded real samples.
- [x] Recover all static mesh vertex/index/UV arrays and material name tables.
- [x] Decode bone hierarchy/transforms and BANIM local tracks.
- [ ] Validate original inverse bind matrices/skin deformation and audio formats.
- [ ] Identify script/event/battle data formats and code architecture.
- [ ] Choose source-port, reimplementation, or other viable strategy.

**Exit criterion:** one actual game asset is decoded or displayed correctly,
with repeatable evidence and without bundling it in the source repository.

### Gate 2 — Portable game-data and rendering prototype
- [ ] Independent platform-neutral core (no PS3 binary code reused blindly).
- [ ] Load assets from a user-supplied local directory.
- [ ] Present a real 3D battle map with camera, materials and animations.
- [ ] Render via a verified Switch-compatible graphics backend.
- [ ] Validate controller actions.

**Exit criterion:** same reference scene renders on desktop and Switch.

### Gate 3 — Gameplay and audio
- [ ] Replicate battle turns, range, height, AI, skills and damage rules.
- [ ] Parse dialogues, scenes, localization and save-related structures.
- [ ] Audio and video path validated with representative legal local data.
- [ ] Controller UI / save and load integrated.

**Exit criterion:** one original battle can be completed reproducibly.

### Gate 4 — Complete homebrew
- [ ] Complete campaign evaluation, stability, performance and regression tests.
- [ ] Real Switch hardware validation in portable and docked modes.
- [ ] Deployment instructions requiring user-provided game assets where needed.

**Exit criterion:** comprehensive documented pass on actual hardware.

## Reusable work from the PS1 project

The separate PS1 repo has **infrastructure experiments** using devkitPro/libnx,
SDL2/GLES, input and CI. These may inform portability tooling, but they do not
supply a Flames of Judgment game engine or compatible asset parsers.

Do not claim running the original PS3 game merely because a probe builds an
NRO. Track independently: compiler success, emulation smoke test, real-hardware
result, and original-game compatibility.

## Known unknowns

Exact original engine; available asset formats; rights and access to
development materials; technical feasibility of code recovery; performance;
audio/video codecs; localization; and required work are **unconfirmed**.

- [x] Compare mock deko3d enum values against upstream header, correct RGBA8/UsageRender values and add nine native C11 ABI assertions.
- [x] Add offline devkitPro cross-build preflight, optional shader UAM detection, and four locally passed synthetic SDK tests.
- [ ] Restore GitHub Actions jobs, compile actual optional deko3d NRO against the real Switch SDK and inspect linker output.
- [ ] Verify first GPU-cleared frame on Nintendo Switch hardware.


## GPU vertex memory upload (2026-10-16)

- [x] Add shader-free deko3d GPU memory block for three generated XYZW/UV vertices (72-byte payload, 4096-byte allocation).
- [x] Reuse 24-byte FojGpuVertex record from the original-model GPU staging layer.
- [x] Add CPU/GPU address accessors and check upstream `DK_GPU_ADDR_INVALID == UINT64_MAX` with real SDK compile-time contract.
- [x] Extend stateful deko3d host mock to verify uploaded vertex bytes, with additional vertex memory/CPU/GPU address failure scenarios.
- [x] Independently confirm allocator calculations for 3, 9066 and 20000 vertices under C11 and ASan/UBSan.
- [ ] Run the new full 14-scenario mock executable and optional native deko3d build on a working GitHub runner; latest Actions jobs still start with zero steps.
- [ ] Bind generated triangle vertex attributes/shaders and issue an actual GPU draw call; observe the frame on real Switch hardware.
- [ ] Upload user-local original Daldren vertex stream and both DDS atlases only after real GPU rendering is validated.

## Shader-backed deko3d first triangle (2026-10-16)

- [x] Obtain and cross-check original `devkitPro/deko3d/source/dksh.h` layout: 24-byte header, complete 64-byte program records.
- [x] Strengthen `tools/validate_dksh.py` to reject corrupt tables/stage mismatch; update generated-only regression fixtures.
- [x] Add bounded portable C DKSH loader that validates UAM program stage, offsets and file size before loading from the user's SD card.
- [x] Run generated DKSH C tests under local strict C11 + ASan/UBSan.
- [x] Add synthetic UV-gradient fragment shader and optional UAM `triangle-verify` build target.
- [x] Implement independent `gpu/triangle.mk` NRO variant with `DkMemBlockFlags_Code`, `DkShaderInitialize`, vertex attribute binding and `dkCmdBufDraw` source path.
- [x] Add `tools/prepare_gpu_triangle_sd.py` with generated DKSH stage checks, file limits and no-overwrite semantics.
- [ ] Compile both genuine vertex/fragment DKSH modules using an installed UAM compiler; inspect stage metadata.
- [ ] Compile the separate triangle NRO against the real devkitPro SDK (GitHub Actions currently fails before any steps).
- [ ] Boot on physical Switch and **observe** the UV-gradient GPU triangle; validate button exit and resource cleanup.
- [ ] Only then submit original user-local Daldren mesh and DDS atlases to a tested hardware GPU renderer.

**The draw call exists in source, but no Switch GPU draw execution has been confirmed.**

## GPU triangle source and pixel-reference gate (2026-10-16)

- [x] Define XYZW/UV GPU layout with native `_Static_assert` for 24-byte stride and offsets 0/16; use named deko3d bitfield initializers.
- [x] Add independent strict C11 local test of vertex-bitfield initializer layout.
- [x] Add `host-triangle-check` target to syntactically validate the shader-backed source without Switch SDK, wired into research CI and optional GPU workflow.
- [x] Add theoretical 1280x720 triangle pixel/UV/color reference and four locally passed generated-data tests.
- [ ] Run the full host triangle mode with a working SDK/runner and compare its first physical frame to pixel probes.
- [ ] Compile real UAM DKSH modules and both ARM64 GPU test NROs; GitHub Actions still fails before steps execute.
- [ ] Observe UV-gradient GPU triangle and eventually six material draws of the authentic user-local Daldren model on physical Switch.


## GPU shader memory validation (2026-10-16)

- [x] Extract dedicated two-stage DKSH code-memory plan into `gpu/shader_layout.c`; 256 KiB pool, two 128 KiB slots, 126,976 B stage payload limit, 256 B alignment and 1 KiB forbidden tail.
- [x] Validate DKSH stage sizes before `dkShaderInitialize`; select offsets from checked plan, not duplicated constants.
- [x] Compile/run strict C11 and ASan/UBSan local tests for maximum sizes, alignment, overflow, protected tail and no-write-on-error.
- [x] Add module to shader-backed native `gpu/triangle.mk`; add CI tests and existing SDK-free `host-check` / `host-mock-sanitized` targets.
- [ ] Verify the full current GPU host integration suite when executable on a working runner.
- [ ] Verify real UAM DKSH shader compilation, real ARM64 deko3d native link, then first physical GPU triangle draw.

## GPU DKSH transactional intake (2026-10-16)

- [x] Change `foj_dksh_read_file` to stage SD data in temporary heap memory; copy into GPU-code memory only after complete read and stage/metadata validation.
- [x] Add generated-fixture regressions asserting rejected wrong-stage, insufficient-capacity and damaged-header DKSH input leaves both output buffer and byte count unchanged.
- [ ] Execute updated DKSH C11/ASan/UBSan host tests on a runner with repository checkout; this session cannot reach GitHub from its local test container.
- [ ] Confirm shader binaries with UAM and inspect first frame on physical Nintendo Switch; no runtime success claimed.

## GPU host DKSH integration (stage 70)

- [x] Include generated-only DKSH intake tests in `gpu/clear.mk` `host-check` and `host-mock-sanitized`; include both outputs in `clean`.
- [x] Confirm updated Makefile targets are present on GitHub.
- [ ] Run full targets on a real checkout/CI runner. Current sandbox cannot resolve `github.com` for cloning; this step is not claimed as passed.
- [ ] Verify UAM and devkitA64 builds, then physical Switch GPU triangle output.
