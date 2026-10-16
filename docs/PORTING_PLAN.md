# Porting plan (research gates)

## Target

Create a native **Nintendo Switch homebrew** implementation of
*Vandal Hearts: Flames of Judgment*, preserving the original game experience
to the extent technically and legally feasible.

PS3 Cell/PowerPC binaries **cannot** simply be relabeled as Switch ARM64 NROs.
The source code has not been obtained. A recreation/port may require substantial
reverse engineering, new platform code, and clean-room implementations.

## Milestones

### Gate 0 — Package identification (active)
- [x] New independent GitHub repository.
- [x] Read-only PKG header parser and synthetic tests.
- [ ] Validate the user's local reconstructed ZIP.
- [ ] Confirm raw package magic, revision, type, content ID, bounds and SHA-256.
- [ ] Save a redacted/asset-free technical report.

**Exit criterion:** reproducible report for a real file; no proprietary data in Git.

### Gate 1 — Asset and engine feasibility
- [ ] Establish lawful access to game resources for local research.
- [ ] Catalog file tree, compression, and candidate format signatures.
- [ ] Determine actual renderer, mesh/texture/animation/audio formats.
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
