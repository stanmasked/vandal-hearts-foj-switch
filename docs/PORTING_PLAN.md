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
