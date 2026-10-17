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

## Stage 71: default GPU host-check coverage

- [x] Make `host-triangle-check` a prerequisite of the default `gpu/clear.mk` `host-check`, ensuring the actual shader-backed source receives a strict C11 syntax check during routine SDK-free GPU verification.
- [x] Re-run standalone DKSH transactional generated-data tests locally with strict C11 warnings and with ASan/UBSan (both pass).
- [ ] Confirm the full `host-check` suite in a complete checkout and CI. Existing GitHub workflow runs remain unverified; no CI success is implied by a committed Makefile.
- [ ] Compile genuine UAM DKSH and ARM64 NRO with devkitPro, followed by hardware frame inspection.

## Stage 72: dedicated GitHub GPU host regression workflow

- [x] Add `.github/workflows/gpu-host-regression.yml` with pull request, main-branch path-filtered push, and manual triggers.
- [x] Run existing `make -f gpu/clear.mk host-check` followed by `host-mock-sanitized` on a GitHub-hosted Ubuntu runner when workflow execution is available.
- [x] Grant workflow only `contents: read` and set a 15-minute job timeout.
- [ ] Verify actual workflow dispatch/job steps and passing results on GitHub; a committed workflow alone is not evidence of a successful CI run.
- [ ] Validate genuine UAM shader compilation and ARM64/deko3d linking on a properly provisioned runner.
- [ ] Confirm first GPU frame on physical Nintendo Switch hardware.

## Stage 73: GPU host CI diagnostics (2026-10-17)

- [x] Make the dedicated GPU-host GitHub workflow retain separate strict-C11 and ASan/UBSan logs, preserving the failure status with Bash pipefail.
- [x] Emit an always-run GitHub Actions step summary showing each suite outcome and clarifying that SDK-free host checks do not prove Switch hardware compatibility.
- [x] Upload logs as a short-lived diagnostic artifact, including when a suite fails.
- [ ] Confirm GitHub Actions actually schedules a push workflow run and that the new steps execute; PR-only workflow-run lookup returned no PR runs, and commit statuses were empty, which do not establish the status of push-triggered runs.
- [ ] Perform genuine UAM + ARM64 build and physical GPU frame test.

## Stage 74: independent sanitizer diagnostics

- [x] Give the dedicated GPU-host workflow Checkout a step identifier.
- [x] Use an explicit non-cancelled + successful-checkout condition for ASan/UBSan so an earlier strict C11 failure does not suppress sanitizer diagnostics.
- [x] Keep per-suite outcomes, saved logs, and existing workflow failure propagation.
- [ ] Verify an actual GitHub Actions run. Empty combined commit statuses do not establish workflow execution or outcome.
- [ ] Validate real UAM DKSH and ARM64 GPU NRO compilation with installed Switch toolchain, then observe physical hardware output.

## Stage 75: cross-compiler host CI (2026-10-17)

- [x] Expand dedicated SDK-free GPU workflow to GCC and Clang matrix jobs with fail-fast disabled.
- [x] Set `HOSTCC` per compiler, show selected compiler version and retain compiler-specific CI log artifacts.
- [x] Confirm committed workflow content through GitHub connector.
- [ ] Confirm actual Actions job execution and pass/fail logs; neither a committed workflow nor empty commit statuses proves a run occurred.
- [ ] Verify genuine UAM shader compilation, devkitA64 NRO link, and first physical Switch GPU draw.

## Stage 76: synthetic DKSH GPU two-slot integration (2026-10-17)

- [x] Add generated-only integration test `tests/test_gpu_dksh_integration.c` combining the real DKSH file loader and GPU shader layout calculator.
- [x] Cover maximum 126,976-byte vertex/fragment stages, disjoint shader slots, preserved gap/tail, and refusal to replace a valid loaded fragment with a damaged module.
- [x] Wire test into strict host-check, sanitizer host suite, and clean targets via `gpu/clear.mk`.
- [ ] Run the new integration test on a full checkout / CI runner; GitHub connector writes and source review do not prove successful C compilation or test execution.
- [ ] Validate actual UAM DKSH modules, ARM64 NRO and first physical Switch GPU frame.

## Stage 77: local two-slot DKSH execution (2026-10-17)

- [x] Locally reconstructed the standalone loader, layout planner and generated two-slot integration test from the GitHub source, using system GCC and Clang.
- [x] Passed the synthetic DKSH two-slot test with GCC strict C11 and GCC ASan/UBSan.
- [x] Passed the same test with Clang strict C11 and Clang ASan/UBSan.
- [ ] Execute the entire repository host suite and confirm GitHub Actions results; direct GitHub clone from the test container remains DNS-inaccessible.
- [ ] Compile actual UAM DKSH modules and ARM64 NRO; verify GPU output on physical Switch.

Host test execution does not establish deko3d hardware rendering or proprietary-game compatibility.

## Stage 78: broaden SDK-free sanitizer coverage (2026-10-17)

- [x] Extend `gpu/clear.mk` sanitized host target to include `test_gpu_smoke_plan.c` (allocation and frame/palette scheduling) and `test_deko3d_api_contract.c` (mock API compatibility assertions).
- [x] Wire both new sanitized executables into the `clean` target and retain GCC/Clang matrix execution in existing CI workflow.
- [ ] Run the entire strict/sanitized host suite from a full checkout and confirm actual CI results. Direct container checkout still fails DNS resolution for github.com.
- [ ] Compile DKSH with UAM, cross-link ARM64 NRO against real deko3d and verify on physical hardware.

No claim of a full host suite pass or hardware draw is made for this stage.

## Stage 79: GPU integration test CI trigger audit (2026-10-17)

- [x] Found missing GitHub Actions path-filter entry for `tests/test_gpu_dksh_integration.c` despite the source being a dependency of host-check and sanitized targets.
- [x] Add the test path to both main push and pull-request workflow triggers, so edits to the integration test itself schedule the dedicated SDK-free GPU jobs.
- [ ] Observe actual workflow execution and run the complete GPU host suite. No CI success is claimed from the trigger change alone.
- [ ] Validate UAM shader compilation, Switch ARM64 cross-build and physical GPU rendering separately.

## Stage 80: occupied DKSH slot stage-guard regression (2026-10-17)

- [x] Extend the generated two-stage integration test with an otherwise structurally valid vertex module presented to an already populated fragment slot. Require rejection, unchanged caller byte count, byte-for-byte preservation of the fragment module and unchanged protected tail.
- [x] Commit test to main; the dedicated GPU workflow path filter includes this test source.
- [ ] Execute the updated test and full GPU host suite on a complete checkout. Local GitHub DNS is unavailable; status/PR workflow queries expose no confirmed pass or fail for push runs.
- [ ] Confirm genuine UAM DKSH, ARM64 NRO and physical Switch GPU frame independently.

## Stage 81: independent host execution of updated DKSH integration (2026-10-17)

- [x] Reconstruct current standalone DKSH loader, GPU layout and updated integration scenario using source retrieved from GitHub connector.
- [x] Compile/run synthetic two-slot integration with GCC and Clang under strict C11 and under ASan/UBSan: four passing executions after formatting the local test reconstruction to meet `-Werror`.
- [x] Verify wrong-stage vertex module cannot replace the loaded fragment stage and damaged DKSH cannot modify its existing content.
- [ ] Run complete repository `make -f gpu/clear.mk host-check` and `host-mock-sanitized` on a real checkout/CI runner. This container cannot resolve GitHub for cloning.
- [ ] Compile real UAM shader DKSH, link ARM64 NRO, and validate first physical GPU triangle.

This evidence covers reconstructed host-only modules, not real deko3d GPU execution.

## Stage 82: GPU smoke host execution and slot-preservation regression (2026-10-17)

- [x] Locally compile and run reconstructed `gpu/smoke_plan.c` + its generated-only host test with GCC and Clang in strict C11 modes: two passes.
- [x] Run the same source and tests with AddressSanitizer and UndefinedBehaviorSanitizer on GCC and Clang: two passes.
- [x] Extend the two-slot DKSH test to assert both the original vertex module and loaded fragment module, slot gap, and reserved tail survive failed fragment replacement attempts.
- [ ] Execute updated full GPU host test suite in a repository checkout / GitHub Actions, and validate the newly added slot assertions: no pass is claimed yet.
- [ ] Compile genuine UAM shaders, devkitA64 GPU NRO and observe the actual hardware frame.

Local tests use manually reconstructed source, not a full repository checkout or real Nintendo Switch.

## Stage 83: verified updated DKSH slot preservation (2026-10-17)

- [x] Retrieved current DKSH loader, shader layout and updated integration-test source through the GitHub connector.
- [x] Reconstructed the standalone C sources in a local test directory and executed the complete two-slot integration scenario using GCC and Clang with strict C11 warnings: both passed.
- [x] Repeated the same integration scenario with GCC and Clang ASan/UBSan: both passed (four total executions).
- [x] Verified that a wrong-stage or corrupted fragment replacement preserves both loaded GPU shader slots, the unused gap, protected tail and output byte count.
- [ ] Run the complete repository host-check and CI workflow on an actual checkout; clone from this container is blocked by DNS resolution.
- [ ] Build real UAM DKSH and ARM64 NRO, then validate rendering on physical Switch hardware.

These results are limited to the locally reconstructed standalone host test, not deko3d device execution.

## Stage 84: native triangle rebuild dependency correctness (2026-10-17)

- [x] Add optional `GPU_EXTRA_DEPS` to the GPU ELF target in `gpu/clear.mk` without changing the standalone clear smoke-test variant.
- [x] Declare `gpu/dksh_module.h` and `gpu/shader_layout.h` as native triangle build dependencies in `gpu/triangle.mk` so editing either header invalidates the ARM64 ELF target.
- [ ] Verify these make dependencies on a complete repository checkout, run full GCC/Clang host suites and inspect actual GitHub Actions results.
- [ ] Compile shaders with real UAM, cross-compile devkitA64 NRO and observe GPU draw on real Nintendo Switch.

Configuration changes do not prove compiler or device execution.

## Stage 85: native triangle Makefile dependency regression (2026-10-17)

- [x] Confirm with a local GNU Make dependency reproduction that a newer shader layout header makes the native triangle ELF out of date (`make -q` exits 1).
- [x] Add `tests/test_gpu_make_dependencies.sh` to check both shader headers and a current-ELF control case in a temporary SDK-free workspace.
- [x] Include the regression in dedicated GCC/Clang GPU CI strict step; log errors together with the existing host suite and update path filters.
- [ ] Confirm the new regression against the complete GitHub checkout and actual CI results.
- [ ] Run UAM DKSH compilation, devkitA64 GPU NRO link and physical Switch triangle draw.

The local dependency reproduction was not a full real SDK build.

## Stage 86: GPU Makefile regression fixture correction (2026-10-17)

- [x] Fix the timestamp fixture in `tests/test_gpu_make_dependencies.sh`: copied Makefiles inherited current mtimes and could incorrectly trigger the baseline ELF rebuild assertion. Normalize both Makefiles to the fixture's old timestamp before dry-running make.
- [x] Make the common GPU build depend on `gpu/clear.mk` and the triangle variant also depend on `gpu/triangle.mk`, so future compiler/linker flag edits invalidate the corresponding ELF.
- [x] Extend the SDK-free Makefile dependency regression to cover both Makefiles in addition to DKSH and shader-layout headers.
- [ ] Confirm complete test execution on a GitHub checkout and validate actual Actions logs; source commits alone are not proof of a passing test run.
- [ ] Validate real devkitA64/UAM compilation and a physical Switch GPU frame.

## Stage 87: executed GPU triangle Makefile dependency regression (2026-10-17)

- [x] Retrieved the current Makefile dependency regression and GPU variant configuration through GitHub connector.
- [x] Recreated the pertinent native GPU ELF dependency and compile rule locally, using GNU Make dry-run mode; validated all four change cases: `dksh_module.h`, `shader_layout.h`, `triangle.mk`, and `clear.mk`.
- [x] Confirmed control case: unchanged headers and Makefiles do not cause ELF recompilation. The SDK-free regression passed locally after replacing an older local placeholder rule with the actual compiler-shaped rule.
- [ ] Execute the exact script within a complete repository checkout/CI environment; this is not an end-to-end Makefile execution on cloned repository files.
- [ ] Verify GitHub Actions logs, actual UAM DKSH, devkitA64 NRO output, and GPU draw on physical Switch.

## Stage 88: early Switch GPU NRO packaging preflight (2026-10-17)

- [x] Inspected UAM shader Makefile, shader-backed triangle variant and shared GPU NRO build rules.
- [x] Add early `gpu/clear.mk preflight` checks for executable `elf2nro`, executable `nacptool`, and the libnx `switch.specs` linker spec (in addition to existing devkitA64/deko3d checks). Both GPU variants share these rules.
- [x] Checked this execution environment: devkitA64 compiler, elf2nro, nacptool, and switch.specs are all absent; `uam` is not installed and command-line cloning from GitHub fails DNS. An ARM64 build and DKSH shader compile are not possible here.
- [ ] Verify GPU NRO compilation and on-hardware graphics with the real devkitPro/UAM toolchain.
- [ ] Obtain actual GitHub Actions pass/fail results for the full GPU host regression workflow.

No NRO or DKSH files were produced in this stage.

## Stage 89: SDK-free GPU preflight regression (2026-10-17)

- [x] Add `tests/test_gpu_preflight.sh`: create a temporary fake devkitPro tree, verify the six diagnostic failures (cross-compiler, elf2nro, nacptool, switch.specs, deko3d.h, libdeko3dd.a) sequentially, then verify a complete fake presence-only preflight passes.
- [x] Include it in both dedicated GPU CI matrix host strict jobs, with automatic triggers for edits to the script.
- [ ] Execute the new test in an actual checkout and inspect GitHub Actions results; changes committed via GitHub connector do not demonstrate execution.
- [ ] Build with real UAM / devkitA64 and test hardware GPU output.

The fake toolchain is suitable for validating diagnostic presence checks only. It cannot produce ARM64 binaries or verify SDK compatibility.

## Stage 90: executed SDK-free GPU preflight test (2026-10-17)

- [x] Reconstructed the current `gpu/clear.mk` preflight rules and `tests/test_gpu_preflight.sh` inside a temporary local host workspace, then executed the six missing-component and complete-presence fixtures: PASS.
- [x] Strengthen the committed preflight regression with three distinct non-executable tool cases (devkitA64 gcc, elf2nro, nacptool).
- [x] Executed the strengthened nine-failure-case regression and complete-presence control using the same exact preflight rules: PASS.
- [ ] Repeat from a full repository checkout and obtain actual GitHub Actions logs. Local reconstructed preflight-rule testing does not prove end-to-end host-suite success.
- [ ] Compile real UAM shaders and ARM64 NRO; test actual GPU output on Nintendo Switch.

No real SDK packages were installed, and the fake presence-only toolchain cannot compile any ARM64 program.

## Stage 91: purge rejected DKSH shader outputs (2026-10-17)

- [x] Add GNU Make `.DELETE_ON_ERROR` to `gpu/Makefile` so a failed UAM compile or a failing `tools.validate_dksh` invocation cannot leave the target DKSH artifact as a valid-looking, up-to-date build output.
- [x] Verify locally with GNU Make in a generated temp fixture: a recipe writes a bad DKSH file, fails, and make emits `Deleting file 'output.dksh'`; the target does not remain on disk.
- [ ] Run actual UAM / validator failure on a full repository checkout; the local test only confirms GNU Make deletion semantics.
- [ ] Run complete host CI suite and verify devkitA64 NRO plus on-device GPU frame.

## Stage 92: shader rejection cleanup CI regression (2026-10-17)

- [x] Add `tests/test_gpu_shader_failure_cleanup.sh`. Runs a copy of the *actual* `gpu/Makefile` in an isolated SDK-free directory, simulates a UAM compiler that produces an invalid DKSH file, then has a stub DKSH validator reject it.
- [x] Assert the build fails, no malformed target remains, and GNU Make reports deleting the target; wire the test into GCC/Clang GPU CI and both workflow path filters.
- [ ] Confirm this regression executes successfully in a full checkout / GitHub Actions environment.
- [ ] Compile authentic shader with UAM, ARM64 NRO with devkitA64 and verify hardware GPU output.

The simulated shader and stub validator do not prove genuine UAM or GPU compatibility.

## Stage 93: execute DKSH build failure cleanup on host (2026-10-17)

- [x] Reconstruct the actual relevant `gpu/Makefile` target and stage-92 cleanup test locally; confirmed a validator-rejected synthetic DKSH is deleted by GNU Make.
- [x] Extend committed cleanup test to simulate a UAM process which writes DKSH and exits with error code 17; assert the partial target is also deleted.
- [x] Re-run both failure-mode scenarios against the locally recreated Makefile target: both PASS.
- [ ] Run exact expanded test against a full GitHub checkout/Actions; no full CI pass is implied by this isolated local run.
- [ ] Validate authentic UAM-generated DKSH and devkitA64 NRO on Nintendo Switch hardware.

## Stage 94: correct the simulated UAM compiler-failure scenario (2026-10-17)

- [x] Audit stage-93 shader cleanup regression: the environment variable `FAKE_UAM_FAIL=1` was previously unused, so the alleged compiler-failure branch actually exercised another validator rejection.
- [x] Fix fake UAM to write a malformed DKSH and then exit with status 17 when requested. Assert its failure is visible in Make diagnostics, and confirm GNU Make removes the partial output.
- [x] Execute corrected isolated test locally, using the shader Makefile and script restored under `/mnt/data/vh93`: both validator-rejection and UAM write-then-fail cases passed.
- [ ] Execute whole CI host matrix and compile real UAM/ARM64 NRO on real SDK; local fake UAM does not prove GPU runtime compatibility.

## Stage 95: ensure validator is skipped after UAM failure (2026-10-17)

- [x] Extended `tests/test_gpu_shader_failure_cleanup.sh` with a validator-call log. Require one invocation when fake UAM writes DKSH successfully (then validation fails), and no additional invocation when fake UAM writes DKSH but exits with code 17.
- [x] Executed the same two scenarios and validator-call assertions in a local reconstructed GPU Makefile test directory: both passed.
- [x] Committed the additional assertions and reviewed the saved GitHub file.
- [ ] Run the exact test and full GPU host suite in GitHub Actions; no CI pass is established by the local reconstruction.
- [ ] Verify UAM/devkitA64 build and physical Nintendo Switch GPU draw.

## Stage 96: expand UAM failure-cleanup coverage to all shader targets (2026-10-17)

- [x] Expand `tests/test_gpu_shader_failure_cleanup.sh` across `foj_actor.vert.dksh`, `foj_actor.frag.dksh` and `foj_triangle.frag.dksh` (six compiler/validator failure runs in total).
- [x] For each generated-only target, require failed validation or write-then-fail UAM to remove the output, and check the validator invocation count remains exactly one for the pair.
- [x] Locally executed the extended test with matching three-target GNU Make shader rules reconstructed in the existing host test workspace: PASS.
- [ ] Run the exact committed script from full repository checkout and inspect real GitHub Actions jobs. The local workspace's originally reduced Makefile required restoration of both fragment rules.
- [ ] Generate actual DKSH with UAM; cross-link and run a native GPU NRO on Switch.

These synthetic tests do not validate Maxwell shader code or hardware draw calls.

## Stage 97: DKSH success and incremental-build regression (2026-10-17)

- [x] Extend the SDK-free shader Makefile regression across three DKSH targets to cover the successful compiler-and-validator path, not only two rejection modes.
- [x] For each stage, assert the validated output remains present, the validator was invoked exactly once, and a second unchanged Make invocation does not revalidate/recompile the target.
- [x] Preserve the existing UAM write-then-fail and validator rejection cases, and commit the upgraded regression.
- [ ] Run the exact updated script within a complete checkout/CI and verify outcomes; no GitHub Actions success is claimed.
- [ ] Compile actual UAM Maxwell programs, link a Switch GPU NRO and verify a hardware frame.

## Stage 98: executed DKSH success and incremental host regression (2026-10-17)

- [x] Reconstructed the existing three-target GPU shader Makefile and the fake-UAM/fake-validator regression locally under `/mnt/data/vh97`.
- [x] Verified failing validator removes generated DKSH, and fake UAM's write-then-fail branch removes DKSH; both PASS.
- [x] Exercised newly introduced stage-97 successful fake validation, retained output and second incremental no-op build for vertex, actor fragment and triangle fragment: all three PASS.
- [ ] Repeat exact committed test from a complete GitHub checkout, run full host suite and check actual GitHub Actions logs.
- [ ] Run real UAM, devkitA64 and physical Switch GPU display checks.

The locally executed Makefile was a reconstruction of the relevant shader rules; no actual SDK-generated DKSH was produced.

## Stage 99: verify DKSH incremental builds and source-change rebuilds (2026-10-17)

- [x] Extend `tests/test_gpu_shader_failure_cleanup.sh`: count fake UAM invocations and assert an unchanged target does not invoke UAM; changing a shader source must invoke UAM and the validator exactly once more and leave a DKSH output.
- [x] Exercise all three shader targets locally with isolated reconstructed Makefile rules: failed-validator cleanup PASS, compiler write-then-fail cleanup PASS, successful no-op + source-triggered rebuild PASS (three targets).
- [x] Use source timestamps relative to the created DKSH (+2 seconds) to avoid fixed far-future timestamps. The updated local test passed all three shader targets.
- [ ] Execute exact new committed test from a full GitHub checkout and obtain CI host matrix results; GitHub DNS unavailable in this local container.
- [ ] Validate UAM-generated actual shader programs, native ARM64 NRO build and Switch hardware frame. devkitA64 is not installed in this local container.

## Stage 100: additional real C GPU DKSH integration boundaries (2026-10-17)

- [x] Review current native GPU draw setup and DKSH two-slot loader in the GitHub repository.
- [x] Extend the committed `tests/test_gpu_dksh_integration.c` with two negative cases: truncated (128-byte) replacement and a valid maximum-size DKSH rejected due to insufficient destination capacity. Both must preserve the previous fragment and vertex slots and leave `bytes_written` unchanged.
- [x] Compile and run a locally reconstructed form of the updated two-slot test against local copies of `gpu/dksh_module.c` and `gpu/shader_layout.c` using GCC and Clang with ASan/UBSan: both PASS.
- [ ] Verify exact current repository checkout / full host suite and confirm GitHub Actions jobs; direct GitHub clone failed DNS in this environment.
- [ ] Build authentic UAM shaders and devkitA64 NRO, then verify a rendered frame on Nintendo Switch.

The local test sources come from the previous reconstructed stage-83 workspace, amended with the same new cases; this is not a verified full repository build.

## Stage 101: transactional DKSH loader invalid-input regression (2026-10-17)

- [x] Extend `tests/test_gpu_dksh_integration.c` with NULL file path, NULL destination, invalid shader stage, insufficient capacity and a missing file after unlink; confirm rejected attempts keep output byte count and both loaded shader slots unchanged.
- [x] Locally reconstruct this expanded regression including prior truncated/capacity negative cases from GitHub; compile with strict C11 GCC and Clang, each using ASan and UBSan. Both runs PASS.
- [ ] Execute exact file from full checkout in GitHub Actions and validate the whole GPU host suite; local source is a reconstruction based on the stage-83 files with equivalent new cases.
- [ ] Build authentic DKSH using UAM, native ARM64 NRO with devkitA64, and physically verify deko3d draw.

## Stage 102: ensure transactional GPU loader test survives NDEBUG (2026-10-17)

- [x] Identify test correctness defect: `assert(foj_dksh_read_file(...))` and file I/O calls inside assertions silently disappear when compiling with `-DNDEBUG`.
- [x] Add explicit `#undef NDEBUG` before importing `assert.h` inside `tests/test_gpu_dksh_integration.c`, keeping every side-effecting check active.
- [x] Locally compile and execute reconstructed DKSH integration sources under `-DNDEBUG` with strict C11, GCC and Clang, each with ASan/UBSan: PASS.
- [x] Add a dedicated `HOST_DKSH_INTEGRATION_NDEBUG` host target to `gpu/clear.mk`, invoked from `host-check` and removed by `clean`. Existing GPU CI matrix now includes it automatically via host-check.
- [ ] Run the exact current full repo host suite in CI; no actual GitHub Actions result is confirmed.
- [ ] Compile actual DKSH with UAM and run native GPU NRO on Switch hardware.

This test verifies host-side validation/integration, not real Switch GPU execution.

## Stage 103: shader GPU code-memory layout regression with NDEBUG (2026-10-17)

- [x] Fix `tests/test_shader_layout.c` so `-DNDEBUG` cannot suppress side-effecting calls to `foj_gpu_shader_layout` inside assertions.
- [x] Add `HOST_SHADERS_NDEBUG` executable to `gpu/clear.mk host-check` and its clean rule, so both GCC/Clang CI host jobs exercise shader slot invariants with this build flag.
- [x] Locally rebuild a matching shader-layout C/header/test subset and execute `-DNDEBUG` GCC and Clang, strict C11, AddressSanitizer and UndefinedBehaviorSanitizer: PASS for both.
- [ ] Run whole repo host-check/CI and real devkitPro/UAM build, physical Switch draw. The isolated test is not proof of full SDK/hardware compatibility.

## Stage 104: GPU smoke must present at least one frame (2026-10-17)

- [x] Fix the optional deko3d clear/triangle application's Plus exit path: only report success if at least one frame was actually submitted and presented. An immediate Plus exit retains setup/no-frame status 3.
- [x] Extend `tests/test_deko3d_clear_host.c` with an immediate-Plus scenario expecting zero presented frames, status 3 and complete resource cleanup; update expected scenario count to 15.
- [ ] Execute the full stateful deko3d mock from an up-to-date checkout and inspect GitHub CI logs. The local reconstructed `deko3d_clear_main.c` was empty, and no claim of test pass is made.
- [ ] Build with real devkitA64/UAM and verify GPU output on Switch hardware.

## Stage 105: GPU lifecycle early applet exit and NDEBUG guard (2026-10-17)

- [x] Add `FAIL_APPLET_EARLY` to the stateful deko3d lifecycle mock, where `appletMainLoop()` returns false immediately. Assert no frame was presented, exit code remains 3 (not GPU success), and resources are balanced. The mock now lists 16 scenarios.
- [x] Keep mock-side `assert` expressions active when `-DNDEBUG` is supplied, matching the DKSH/shader-layout test protections from earlier stages.
- [x] Commit changes to `tests/test_deko3d_clear_host.c`.
- [ ] Run exact 16-scenario host mock in a complete checkout and inspect real GitHub Actions logs. This environment cannot resolve github.com for git clone and does not contain a nonempty local GPU main C source; no execution pass is claimed.
- [ ] Build NRO with devkitA64/UAM and verify first deko3d GPU frame on Switch hardware.

## Stage 106: deko3d lifecycle mock under NDEBUG (2026-10-17)

- [x] Add `HOST_MOCK_NDEBUG` target in `gpu/clear.mk` for the full stateful deko3d lifecycle mock, compiled with `-DNDEBUG`; call it from `host-check` and remove it with `clean`.
- [x] Review the stored Makefile to confirm the target, compiler command and host-check invocation are present. Existing GPU CI host-check now includes the new variant automatically.
- [ ] Confirm successful execution of all 16 mock scenarios in both ordinary and NDEBUG configurations from a complete repository checkout / GitHub Actions. No completed CI run or native test execution was verified here.
- [ ] Build and execute the real GPU NRO with devkitA64/UAM and Switch hardware.

## Stage 107: swapchain acquisition boundaries (2026-10-17)

- [x] Add `FAIL_ACQUIRE_OOB` case to stateful GPU mock: an invalid acquired image index 2 (two-frame swapchain) after three successful frames must lead to exit status 4; no extra frame is presented and resources must be freed. This increases mock cases to 17.
- [x] Require submitted and presented command-list counts to match in every mock scenario, preventing a silent unpresented submission on error exits.
- [x] Commit changed host mock to GitHub.
- [ ] Run ordinary, NDEBUG and ASan/UBSan lifecycle host mock from a full checkout; no successful execution was confirmed this stage. Direct git clone failed due to DNS in current environment.
- [ ] Cross-compile GPU NRO with devkitA64/UAM and test hardware output.

## Stage 108: boundary after first GPU frame and direct host checks (2026-10-17)

- [x] Add `FAIL_APPLET_AFTER_ONE` lifecycle test case: the applet loop runs exactly once, expecting one submitted/presented GPU frame, exit status 0, and balanced allocations. Mock cases now total 18.
- [x] Execute four SDK-free C11 tests from existing local reconstructed source trees, including `-DNDEBUG`: two-slot DKSH integration and shader layout with both GCC and Clang; all four PASS.
- [ ] Execute the full current 18-scenario lifecycle mock from an exact repository checkout or GitHub Actions; no full mock run has yet been verified.
- [ ] Build actual UAM shaders, devkitA64 NRO and validate a real Switch GPU frame.

The local tests use reconstructed sources from stages 102/103; they are not a full checkout nor a native GPU build.

## Stage 109: extend release-style assertion safety to all GPU host tests (2026-10-17)

- [x] Found remaining `assert()`-dependent smoke-plan, DKSH intake and deko3d API contract tests; added `#undef NDEBUG` before `assert.h` to preserve calls and invariants when building with `-DNDEBUG`.
- [x] Added dedicated `HOST_TEST_NDEBUG`, `HOST_ABI_NDEBUG`, and `HOST_DKSH_NDEBUG` targets to `gpu/clear.mk`, invoked by `host-check` and removed by `clean`. The existing GPU CI matrix inherits these checks.
- [x] Reproduced an old smoke-plan test's `-DNDEBUG -Werror` unused-variable compilation failure in a local stage-82 source copy, then patched the assert guard there and built and ran it with GCC and Clang: PASS in both cases.
- [ ] Run exact current checkout's complete GPU host-check, including 18-scenario deko3d mock, and inspect actual CI logs; DNS prevents git clone here.
- [ ] Real UAM DKSH generation, devkitA64 NRO and Switch hardware GPU test remain unverified.

Local smoke-plan verification used an older reconstructed source, not the current GitHub checkout.

## Stage 110: DKSH output-pointer failure invariant (2026-10-17)

- [x] Add negative integration case to `tests/test_gpu_dksh_integration.c`: passing a NULL `bytes_written` pointer must reject loading without changing the existing fragment and vertex GPU shader slots.
- [x] Exercise the equivalent case in the local restored stage-102 shader integration workspace with strict C11 GCC and Clang, `-DNDEBUG` and UBSan: both PASS. An initial local fixture comparison used the vertex buffer as its reference and failed; regenerated the correct fragment reference and reran successfully.
- [ ] Execute current full checkout and 18-scenario GPU lifecycle mock in GitHub Actions. No GitHub CI success has been verified and git clone continues to fail local DNS resolution.
- [ ] Build authentic UAM-generated DKSH and devkitA64 GPU NRO; validate on Switch.

The local host test uses a reconstructed subset, not the exact full repository checkout.

## Stage 111: oversized DKSH input protection (2026-10-17)

- [x] Add an integration regression for a generated DKSH file larger than `FOJ_DKSH_MAX_BYTES` by 256 bytes. Rejected loads must preserve both shader-memory slots and leave `bytes_written` unchanged.
- [x] Commit the new coverage to `tests/test_gpu_dksh_integration.c`.
- [ ] Execute the exact GitHub test against a complete source checkout and obtain GitHub Actions results; local direct GitHub clone fails DNS.
- [ ] Run all 18 deko3d lifecycle mock scenarios and build native NRO with real devkitA64/UAM before claiming hardware GPU compatibility.

- [x] Follow-up local execution: stage-110 reconstructed two-slot C test with the new oversize case compiled and passed under strict C11, `-DNDEBUG`, UBSan using GCC and Clang. This confirms the isolated loader behavior, not the full GitHub checkout.

## Stage 112: NACP metadata dependency invalidation (2026-10-17)

- [x] Fix `gpu/clear.mk` so `$(OUT).nacp` depends on shared `gpu/clear.mk` and `$(GPU_EXTRA_DEPS)` (includes `gpu/triangle.mk` for triangle variant). Title/version changes in these files must now regenerate metadata.
- [x] Extend `tests/test_gpu_make_dependencies.sh` to check a current synthetic triangle NACP remains up-to-date, but touching either GPU Makefile triggers `nacptool --create` in dry-run output.
- [x] Validate the same NACP Make dependency mechanism with a local minimal GNU Make fixture: current NACP no-op; touched triangle Makefile triggers build recipe.
- [ ] Run complete repository test and inspect CI results; local GitHub cloning is blocked by DNS and no full repository run is confirmed.
- [ ] Verify actual SDK UAM/ARM64/NRO compilation and Nintendo Switch GPU output.

## Stage 113: ELF/NACP -> NRO packaging dependency regression (2026-10-17)

- [x] Extend `tests/test_gpu_make_dependencies.sh` to verify the NRO packaging dependency chain using GNU Make dry-runs: an up-to-date triangle NRO does not invoke `elf2nro`, while a newer NACP or a newer ELF triggers repackaging.
- [x] Locally execute the three corresponding dependency scenarios in an isolated minimal GNU Make fixture: PASS.
- [ ] Execute the full updated regression from an exact GitHub checkout/Actions; local minimal fixture is not equivalent to the complete Makefile or SDK toolchain.
- [ ] Confirm native ARM64 NRO build and deko3d GPU rendering on Switch hardware.

## Stage 114: complete GPU metadata-to-NRO dependency chain (2026-10-17)

- [x] Extend `tests/test_gpu_make_dependencies.sh` to check that updating either shared `gpu/clear.mk` or `gpu/triangle.mk` schedules both the NACP generation and NRO packaging commands, with all other synthetic outputs older than NRO.
- [x] Run the same chain conditions in an isolated minimal GNU Make fixture: both common and variant Makefile changes trigger NACP and NRO recipes (PASS).
- [ ] Execute the exact committed regression in a full repository checkout / GitHub Actions; this environment cannot resolve github.com for cloning.
- [ ] Build real UAM shaders and an ARM64 NRO with devkitA64, then validate actual Switch GPU presentation.

Because both Makefiles are ELF prerequisites, configuration changes may also recompile ELF. The test intentionally does not require compiler reuse.

## Stage 115: cover both native GPU packaging variants (2026-10-17)

- [x] Audited current GitHub GPU build dependency test. The regression only exercised the triangle variant, leaving the independent clear-smoke NRO's NACP dependencies untested.
- [x] Extended `tests/test_gpu_make_dependencies.sh` with an unchanged clear-smoke NRO control and a changed shared Makefile case, expecting NACP regeneration followed by NRO repackaging.
- [x] Committed the new GPU build regression in GitHub.
- [ ] Execute the exact changed regression from a full checkout / GitHub Actions. Current local reconstruction lacks the latest packaging targets and git clone fails DNS; no full test pass is asserted.
- [ ] Compile authentic UAM DKSH and ARM64 NRO with devkitA64 and verify GPU presentation on physical Nintendo Switch.

## Stage 116: source-only clear-smoke incremental rebuild (2026-10-17)

- [x] Inspect the current GPU host CI workflow: GCC/Clang matrix is configured and uploads strict/sanitized logs, but actual Actions runs could not be fetched or verified in this session.
- [x] Add a regression to `tests/test_gpu_make_dependencies.sh` for editing only `gpu/smoke_plan.c`: the clear-smoke ELF compiler and NRO packaging must run, but NACP metadata generation must not run.
- [x] Verify the incremental GNU Make dependency pattern in a small local fixture: baseline no recipes; source edit recompiles ELF and repackages NRO without NACP regeneration (PASS). This is not a run of the exact committed test.
- [ ] Run full GPU host suite and its 18-scenario stateful deko3d lifecycle mock from the full checkout; inspect actual CI outputs.
- [ ] Build native ARM64 GPU NRO with devkitA64/UAM and verify on Nintendo Switch hardware.

## Stage 117: separate GPU binary and NACP metadata dependencies (2026-10-17)

- [x] Fix a real incremental-build issue: `gpu/triangle.mk` lists shader headers in `GPU_EXTRA_DEPS`, which previously also fed the NACP target; touching code headers unnecessarily rebuilt app metadata.
- [x] Introduce `GPU_METADATA_DEPS` in the shared clear Makefile, set it to `gpu/triangle.mk` for triangle, and retain `GPU_EXTRA_DEPS` for ELF compilation only. Editing either build-config Makefile continues to regenerate metadata.
- [x] Add dependency regressions proving DKSH/layout header edits cause ELF rebuild but not NACP regeneration.
- [x] Execute an isolated GNU Make fixture exercising both invariants: shader header triggers ELF only; triangle metadata config triggers NACP (PASS). This fixture is not the full repository test.
- [ ] Execute full repository GPU host-suite and inspect actual GitHub Actions logs; still unverified.
- [ ] Native ARM64 build/UAM DKSH and real Switch rendering remain unverified.

## Stage 118: shader-header changes must repackage NRO, not metadata (2026-10-17)

- [x] Add a full triangle NRO dry-run regression for shader header updates in `tests/test_gpu_make_dependencies.sh`: changing either DKSH/layout header must rebuild ELF, repackage NRO and leave NACP unchanged.
- [x] Execute an isolated GNU Make reproduction of this dependency chain: up-to-date NRO schedules no recipes; after header touch it schedules ELF + NRO and no NACP (PASS).
- [ ] Run the exact committed test in a current full repository checkout / GitHub Actions. The locally available files are from stage 87 and cannot verify current GitHub tests.
- [ ] Run the 18-case deko3d lifecycle suite, compile ARM64 NRO and inspect output on Switch hardware.

## Stage 119: clear-smoke header-only incremental NRO update (2026-10-17)

- [x] Add a negative metadata regression for `gpu/smoke_plan.h`: changing the C header must cause the clear-smoke ELF and packaged NRO to rebuild without rerunning `nacptool --create`.
- [x] Execute an isolated GNU Make fixture with the corresponding dependency graph: unchanged inputs caused no rebuild; after touching the header, only ELF and NRO recipes were printed (PASS).
- [ ] Execute the entire updated `tests/test_gpu_make_dependencies.sh` from the exact current checkout and verify GitHub CI results; this local fixture does not qualify as that full test.
- [ ] Run the full deko3d mock suite and build/verify real ARM64 NRO on Nintendo Switch with devkitPro/UAM.

## Stage 120: cleanup coverage for GPU host test binaries (2026-10-17)

- [x] Read current GPU Makefiles and regression script from GitHub. The full current checkout remains unavailable for direct local execution due to github.com DNS resolution.
- [x] Execute the available earlier stage-87 `tests/test_gpu_make_dependencies.sh` with GNU Make (PASS); this older test does not cover subsequent stage 88–120 changes.
- [x] Add a dry-run `make -f gpu/clear.mk -n clean` regression to `tests/test_gpu_make_dependencies.sh` to assert that all eight important lifecycle, NDEBUG and sanitizer host binaries are removed; protects against stale test executables.
- [ ] Run the exact updated GPU dependency regression and complete 18-case deko3d host mock in a current checkout or GitHub Actions and inspect CI logs.
- [ ] Build real ARM64 NRO and UAM DKSH with devkitPro and confirm on Nintendo Switch hardware.

## Stage 121: variant-specific GPU build cleanup (2026-10-17)

- [x] Add checks in `tests/test_gpu_make_dependencies.sh` that `make -f gpu/triangle.mk -n clean` includes triangle ELF/NACP/NRO and `make -f gpu/clear.mk -n clean` includes clear-smoke ELF/NACP/NRO.
- [x] Execute an isolated GNU Make fixture representing the shared clear Makefile and triangle override: all six output-path checks passed. The entire exact GitHub regression was not executed locally.
- [ ] Run the exact host regression and the 18-scenario deko3d mock suite from a full current checkout; GitHub Actions run outcome remains unverified.
- [ ] Produce ARM64 GPU NRO with devkitA64/UAM and verify real display output on Switch hardware.

## Stage 122: execute clean and verify cross-variant isolation (2026-10-17)

- [x] Strengthen `tests/test_gpu_make_dependencies.sh`: after the pre-existing `make -n clean` checks, actually execute `make -f gpu/clear.mk clean` in the disposable copied-Makefile fixture; confirm it deletes all three clear-smoke ELF/NACP/NRO files but preserves all three triangle outputs.
- [x] Execute `make -f gpu/triangle.mk clean` in the same disposable fixture and require the three triangle artifacts to be removed.
- [x] Commit the added executable assertions. These do not invoke devkitPro and never clean a user's real build directory, because the test changes directory into its own mktemp fixture.
- [ ] Verify the *exact updated* test script and full host suite in a current checkout or GitHub Actions; neither successful CI run nor all 18 lifecycle scenarios has been observed here.
- [ ] Build actual GPU NRO with devkitA64/UAM and test presentation on physical hardware.

## Stage 123: prove host-test binaries are removed by make clean (2026-10-17)

- [x] Extend the existing disposable-fixture regression to create eight representative host mock, sanitizer and NDEBUG output files, run the real `make -f gpu/clear.mk clean` command and assert each file no longer exists.
- [x] Preserve existing isolation checks ensuring clear clean does not delete triangle ELF/NACP/NRO output files.
- [ ] Execute the exact updated regression in the current checkout and verify actual GitHub CI logs; this stage only commits executable test coverage, not confirmed results.
- [ ] Verify the 18-scenario deko3d GPU mock and build actual ARM64 NRO with devkitPro/UAM and hardware rendering.

## Stage 124: GPU clean must preserve unrelated build files (2026-10-17)

- [x] Added a non-GPU sentinel (`build/keep-unrelated-gpu-data.bin`) to the disposable `tests/test_gpu_make_dependencies.sh` fixture. Both real `clear.mk clean` and `triangle.mk clean` calls must leave its contents unchanged.
- [x] Retained checks that the actual ELF, NACP, NRO and host mock binaries are deleted and that clearing one GPU variant does not remove another variant.
- [ ] The exact updated regression and full GPU host suite have not been run or verified in this environment. Local /mnt/data contains no current checkout and the available GitHub connector does not offer a direct checkout into this container.
- [ ] Actual devkitA64/UAM NRO build and Switch GPU rendering remain unverified.

## Stage 125: fix sentinel fixture false-failure (2026-10-17)

- [x] Found real shell bug in the GPU clean test: `printf 'KEEP_GPU_SENTINEL\\\\n'` printed literal backslash+n, whereas the test compared `cat` output with `KEEP_GPU_SENTINEL`.
- [x] Changed the fixture to `printf '%s\\n' 'KEEP_GPU_SENTINEL'`, which writes a newline stripped by command substitution. No change to actual GPU clean rules was necessary.
- [x] Executed an isolated Bash reproduction: the old literal-backslash format failed its comparison; the corrected format passed.
- [ ] Run the full updated `tests/test_gpu_make_dependencies.sh` and the 18-case GPU host mock in a current checkout; neither is verified yet.
- [ ] Cross-compile and validate an actual ARM64 GPU NRO with devkitPro/UAM and test on Switch.

## Stage 126: repair blocker in actual GPU lifecycle host mock (2026-10-17)

- [x] Found a literal backslash + n in `tests/test_deko3d_clear_host.c` within `appletMainLoop` ternary expression; this is invalid C syntax and blocks the lifecycle mock build.
- [x] Replace it with a real newline. Preserve the 0 / 1 / 242 loop cases for early exit, one-frame exit, and regular 242-frame execution.
- [x] Compile and run the corrected ternary-expression/loop boundary logic in a standalone C11 fixture with `gcc` and `clang`, `-Wall -Wextra -Werror -pedantic`: both PASS.
- [ ] Compile and execute the full actual 18-scenario mock and inspect GitHub Actions; the standalone fixture does not validate the entire test harness.
- [ ] Build UAM DKSH and devkitA64 GPU NRO; test real Switch GPU presentation.

## Stage 127: verify GPU queue idle in all 18 host lifecycle scenarios (2026-10-17)

- [x] Inspect current stateful deko3d lifecycle mock and native GPU cleanup path after the C syntax repair. Main cleanup calls `dkQueueWaitIdle(queue)` whenever a queue exists, before releasing GPU resources.
- [x] Extend `run_case` invariants: no queue wait for device/queue creation failures; exactly one wait for every scenario after queue creation. This complements existing allocation, command-submission and presentation counts.
- [x] Commit the new lifecycle assertion to GitHub.
- [ ] A GitHub commit combined status lookup returned no classic statuses, which is not proof of Actions success or failure. The exact 18-scenario suite has not been run here.
- [ ] Confirm host CI execution, native devkitA64/UAM build and Switch display separately.

## Stage 128: isolate GPU Make dependency CI diagnostics (2026-10-17)

- [x] Split `tests/test_gpu_make_dependencies.sh` out of the chained strict C11 CI step into its own GitHub Actions job step, with `gpu-host-dependencies.log` uploaded as a separate artifact.
- [x] Add its outcome to the per-compiler GitHub Actions job summary. Strict C11 and sanitizer checks remain independent follow-on steps even if the Make dependency test fails.
- [x] Preserve GCC/Clang matrix and synthetic SDK-free host test scope; no proprietary assets or native Switch output are involved.
- [ ] Inspect actual CI outcomes and run the full 18-scenario lifecycle test; the present GitHub connector exposes source changes but no confirmed push-triggered Actions run.
- [ ] Build ARM64 NRO and validate actual GPU output with devkitPro and Switch hardware.

## Stage 129: DKSH validator changes must invalidate generated shaders (2026-10-17)

- [x] Found an actual dependency gap: generated DKSH targets in `gpu/Makefile` depended only on their GLSL-like source, so changing `tools/validate_dksh.py` left previously validated binaries untouched.
- [x] Add validator script as a prerequisite of all three UAM DKSH targets (actor vertex, actor fragment, triangle fragment); subsequent `make` re-invokes compiler and validator after a validator change.
- [x] Extend `tests/test_gpu_shader_failure_cleanup.sh` to bump the validator timestamp and assert all three targets are recompiled and revalidated exactly once.
- [ ] Run the exact updated shell test from the current checkout and obtain verified CI results; no such full run was completed here.
- [ ] Cross-compile native GPU NRO with devkitA64/UAM and verify on Switch hardware.

## Stage 130: validator policy change must reject stale DKSH (2026-10-17)

- [x] Extend `tests/test_gpu_shader_failure_cleanup.sh` with a regression for previously accepted DKSH files: after validator source becomes newer, simulate a stricter validator rejecting each of the three shaders, and require Make's `.DELETE_ON_ERROR` to remove the formerly accepted output.
- [x] Assert replacement validator runs exactly once per stage and that no rejected DKSH remains on disk.
- [ ] Execute the exact full shader-failure regression and the 18-scenario deko3d lifecycle suite in a complete checkout / CI; neither has been verified in this environment.
- [ ] Compile real UAM DKSH and devkitA64 GPU NRO, then test on Switch hardware.

## Stage 131: recover rejected DKSH and verify incremental reuse (2026-10-17)

- [x] Extend `tests/test_gpu_shader_failure_cleanup.sh` for all three shader targets: after a stricter validator rejects and deletes each DKSH, accepting policy must regenerate the file with exactly one compiler and validator invocation.
- [x] Re-invoking Make without changes must then leave the successful DKSH untouched, without a second compiler or validator invocation.
- [x] Run a minimal isolated GNU Make `.DELETE_ON_ERROR` scenario with validator rejection, cleanup, successful rebuild and incremental reuse: PASS. This is not the exact full repo shell test.
- [ ] Run current shader regression and deko3d mock from a complete checkout; CI results and physical Switch NRO are still unverified.

## Stage 132: execute exact DKSH host test and isolate CI result (2026-10-17)

- [x] Retrieved `gpu/Makefile` and `tests/test_gpu_shader_failure_cleanup.sh` from current GitHub repository into an isolated local workspace and verified their **Git blob hashes** against GitHub:
  - `gpu/Makefile`: `d5955d6a6e02bce5a74b6bebefb1859ab5668119`
  - `tests/test_gpu_shader_failure_cleanup.sh`: `14591f0125190a9f0ff168338605623e695a3418`
- [x] Executed `bash tests/test_gpu_shader_failure_cleanup.sh` on those exact files: **PASS**, covering all three synthetic shader targets through compiler/validator rejection, `.DELETE_ON_ERROR`, successful compile, incremental reuse, input edits, validator edits, rejected-output recovery and reuse. This is a **host-only test** with intentionally fake UAM and DKSH payloads.
- [x] Performed local negative mutation checks: removing `.DELETE_ON_ERROR:` caused the test to FAIL on retained rejected DKSH; removing the `tools/validate_dksh.py` prerequisite caused it to FAIL on skipped rebuild. Both important regressions are detected.
- [x] Split shader failure/recovery regression into its own GitHub Actions step `shaders`; logs are saved as `gpu-host-shaders.log` and its result is shown in job summary (GCC/Clang matrix unchanged).
- [ ] Confirm GitHub Actions runs and the separate full GPU mock C11 suite: no actual CI logs inspected here.
- [ ] Compile real DKSH with UAM, build ARM64 GPU NRO using devkitA64 and test presentation on physical Switch.

## Stage 133: actual 18-case deko3d GPU host CI passes (2026-10-17)

- [x] Opened PR #16 (`stage133-gpu-lifecycle-ci`) to expose the stateful deko3d lifecycle mock as its own `lifecycle` Actions step, run ordinary and `-DNDEBUG` executables for GCC and Clang, publish `gpu-host-lifecycle.log`, and report results in the job summary.
- [x] Retrieved **actual pull-request GitHub Actions job logs** (not just status flags): all 18 scenarios printed `Host deko3d lifecycle mock: all 18 scenarios passed` in the ordinary and `-DNDEBUG` executables under both GCC and Clang.
- [x] First CI attempt exposed a GCC `-Werror=enum-compare` issue in a GPU shader capacity static assertion; cast both enum constants to `size_t` and confirmed this pattern with GCC and Clang C11 locally.
- [x] First CI attempt also exposed a Make dependency regression test bug: after entering its temporary directory, `target` still held an absolute file path which bypassed the relative GNU Make target rule. Reset `target` to `build/foj-deko3d-triangle-research.elf` after `cd "$tmp"`.
- [x] Removed `grep -q` on pipelines from the Make regression to avoid premature-pipe-closing false negatives with `pipefail`.
- [x] **Actual CI run 39026135352: GPU host regression checks SUCCESS**, both GCC and Clang jobs successful in all steps: Make dependencies, synthetic DKSH regression, strict C11 / GPU triangle syntax, 18-case deko3d lifecycle (normal + NDEBUG), ASan/UBSan.
- [x] **Actual CI run 39026135587: Research tools tests SUCCESS** for the same PR head commit `2f2fe56b376814a0d5c7afa5227837d173b5a91f`.
- [x] PR #16 merged via squash to main: merge commit `2e51078cb834e6633ea1033e6a2bf8a5e3f38007`.
- [ ] These confirmed results are **SDK-free host-only tests**; real UAM DKSH generation, devkitA64 GPU NRO cross-compilation and GPU presentation on Switch hardware remain unverified.

## Stage 134: native GPU NRO cross-compilation and real UAM DKSH — CI SUCCESS (2026-10-17)

- [x] Added independent `.github/workflows/gpu-native-build.yml` on PR #17 using official `devkitpro/devkita64:20260219` and strict real devkitA64/UAM tools, with NRO0/DKSH verification and downloadable artifact. SDK-free host suite remains independent.
- [x] First native CI run **39026722840** failed compiling `DkDeviceFlags_YAxisPointsUp`, which is not defined in the installed public SDK headers (the up-axis convention requires no flag). Removed the nonexistent zero-valued flag; retained explicit zero-to-one depth and upper-left origin.
- [x] Actual native CI run **39026793109: SUCCESS**. Compiled and validated `build/foj-deko3d-clear-smoke.nro` (262200 bytes), `build/foj-deko3d-triangle-research.nro` (274488 bytes), and real UAM `foj_actor.vert.dksh`, `foj_actor.frag.dksh`, `foj_triangle.frag.dksh`. UAM and both NRO validators ran successfully.
- [x] GitHub Actions uploaded the five generated files as artifact `foj-gpu-native-research`, artifact ID **12099185278**, available for seven days at https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39026793109/artifacts/12099185278.
- [x] Same PR head also passed `GPU host regression checks` (39026793120) and `Research tools tests` (39026793124); all three workflows `success`.
- [x] Merged PR #17 into `main`, merge commit `a82be0b408a90c772b577b91bc62f76968afcd8d`.
- [x] Added `docs/GPU_SWITCH_SMOKE_TEST.md` with exact SD shader paths, visual verification checklist and limits of the evidence.
- [ ] Neither native NRO has been launched on physical Nintendo Switch; frame presentation and true GPU behavior remain unverified.
- [ ] The current research GPU binaries do not implement actual FoJ game rendering, PS3 asset loading, or playable game logic.

## Stage 135: six-vertex research geometry through actual GPU stream (2026-10-17)

- [x] Added synthetic six-vertex/two-triangle geometry `gpu/research_mesh.{c,h}` calling the existing `foj_gpu_prepare_stream` and producing one ordered draw batch. No original FoJ models, copyrighted textures or PS3 resource data.
- [x] Connected the optional shader-backed GPU NRO to the new stream output, uploaded the exact six-float-per-vertex buffer and issued a single six-vertex `dkCmdBufDraw` call. The independent clear-only GPU NRO's original smoke data and behavior remain unchanged.
- [x] Updated `gpu/triangle.mk` to cross-compile `gpu/research_mesh.c` and `core/gpu_vertex_stream.c` and track their headers; bumped experimental triangle metadata to 0.12.0.
- [x] Added `tests/test_gpu_research_mesh.c` asserting strict capacity checks/no partially mutated output, six projected vertices, UV bounds, consistent shared edges and one batch. Integrated normal, `-DNDEBUG` and ASan/UBSan variants in `gpu/clear.mk` host suites and cleanup.
- [x] **Actual GitHub Actions PR #18 GPU host regression run 39028292741 SUCCESS** under GCC and Clang. Logs show `GPU synthetic six-vertex research mesh: PASS` in normal, NDEBUG and sanitizer builds on both compilers. Existing 18-case deko3d mock and build dependency regression also pass.
- [x] **Actual native devkitA64/UAM CI run 39028292878 SUCCESS**, compiling and validating both NROs and all three DKSH modules. Updated triangle-research NRO: **278584 bytes**; unchanged clear-smoke NRO: **262200 bytes**. Artifact `foj-gpu-native-research` ID **12099815118**: https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39028292878/artifacts/12099815118
- [x] **Research tools tests run 39028292870 SUCCESS**. PR #18 merged into `main`, squash commit `144a7f67bfd9c732443a72f943e7b14d3ec1bed0`.
- [x] Updated `docs/GPU_SWITCH_SMOKE_TEST.md` with newer artifact and revised six-vertex/two-triangle visual expectation.
- [ ] Hardware visual confirmation on a physical Switch remains outstanding: successful real devkitA64/UAM compilation does not prove deko3d presentation.
- [ ] Real FoJ geometry import and material/texture bindings, game logic and an actual playable port remain outstanding.

## Stage 136: ordered two-batch GPU draw plans — CI SUCCESS (2026-10-17)

- [x] Replaced one synthetic quad with two separate quads (12 vertices, four triangles) generated by `foj_gpu_prepare_stream`; stream sections are `{first=0,count=6,texture_index=0}` and `{first=6,count=6,texture_index=1}`.
- [x] Added portable `core/gpu_draw_plan.{c,h}`, translating stream section metadata into contiguous, triangle-aligned draw ranges. Validates total coverage, out-of-bounds/gaps/overlaps, and material-index bounds before modifying output.
- [x] Native shader-backed research mode uploads 12 vertices and submits **two ordered `dkCmdBufDraw` calls per prerecorded framebuffer/phase command list**. Section IDs are metadata only; both sections use the same UV-gradient shader. No actual texture/material binding yet.
- [x] Added negative-path tests for invalid capacity, bad second-section boundary, invalid material index, incomplete coverage and excessive vertex count; output buffers are unchanged on errors. Included in normal / NDEBUG / ASan+UBSan host matrix.
- [x] **GitHub Actions GPU host regression run 39034956704 SUCCESS**, GCC and Clang; job logs show `GPU ordered two-batch synthetic research mesh: PASS` three times per compiler.
- [x] **Native devkitA64/UAM run 39034956773 SUCCESS**: ELF/NRO cross-compiled for both GPU variants, DKSH modules compiled and validated; NRO header validation also passed. Shader-backed research NRO remains 278584 bytes (alignment dominates file size); clear NRO remains 262200 bytes. Artifact ID **12101922180**: https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39034956773/artifacts/12101922180.
- [x] **Research tools tests 39034956711 SUCCESS** and **Synthetic isometric image preview 39034956716 SUCCESS**. PR #19 merged into `main` via squash as `16f0db7adbece5fc61cef5d3734030ad6f48e512`.
- [x] Updated `docs/GPU_SWITCH_SMOKE_TEST.md` with the stage 136 artifact and expected two-quads visual.
- [ ] Physical Nintendo Switch execution, GPU frame presentation and framebuffer capture are **not verified**.
- [ ] Actual FoJ model/material bindings, atlas textures, PS3 asset import and gameplay integration are still outstanding.

## Stage 137: deko3d per-material RGBA8 research images — native CI SUCCESS (2026-10-17)

- [x] Added `gpu/research_texture.{c,h}`, creating two deterministic distinct 8x8 RGBA8 research textures without proprietary game assets. Strict `tests/test_gpu_research_texture.c` covers invalid inputs with no destination mutation, repeatability, alpha and expected RGB separation.
- [x] Connected the shader-backed native research mode to actual deko3d image memory blocks and an independent CPU-visible staging/descriptor pool; command buffer copies pixels into each image, waits for upload to finish, records persistent image and sampler descriptor bindings, and binds a different `dkMakeTextureHandle(material_index,0)` before each validated ordered draw.
- [x] Changed synthetic `gpu/shaders/foj_triangle.frag` from UV debug gradient to `sampler2D` lookup of the bound research image. Original actor shader, clear-only GPU NRO, nine legacy CPU viewers, and any PS3 game assets remain unaffected.
- [x] Updated `gpu/triangle.mk` sources/dependencies, bumped experimental GPU triangle metadata to `0.14.0`, added mock deko3d C declaration checks and normal/`-DNDEBUG`/ASan+UBSan texture-generator test targets.
- [x] First PR #20 CI exposed missing `<stdbool.h>` for `false` in the C11 host SDK mock. Fixed and reran.
- [x] **Actual GPU host CI run 39035732164: SUCCESS** under GCC and Clang; the new `GPU synthetic two-material RGBA8 textures: PASS` appears in normal, NDEBUG and sanitizer logs for both.
- [x] **Actual native devkitA64/UAM CI run 39035732156: SUCCESS** with NRO0 validation and DKSH stage checks: shader-backed NRO **290872 bytes**, shader-free clear NRO **262200 bytes**. Generated artifact `foj-gpu-native-research` ID **12102067683**: https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39035732156/artifacts/12102067683
- [x] **Research tools tests run 39035732221: SUCCESS**. PR #20 merged to `main` as squash commit `8b819d233d8e40e7b30bea19f1556c29a6709178`.
- [x] Updated `docs/GPU_SWITCH_SMOKE_TEST.md` with exact latest artifact and the expected two different synthetic textures.
- [ ] **Unverified on real Switch hardware:** image copy/synchronization, descriptor programming, texture sampling and GPU frame presentation. CI confirms compilable native code, not actual console output.
- [ ] Real FoJ textures, material parsing, DDS atlas uploads, user-owned local game assets and gameplay renderer integration remain future work.

## Stage 138: bounded private RGBA8 DDS atlas input for GPU materials — CI SUCCESS (2026-10-17)

- [x] Added portable `gpu/atlas_dds.{c,h}`, accepting only classic, uncompressed, contiguous 32-bit RGBA8 DDS files with exact header masks, width 8..256 (multiple of 8), height 1..256, single image, at most one mip level, exact pitch and payload length. Explicitly rejects unsupported formats including common BC/DXT compression and DX10.
- [x] Added transactional `foj_atlas_dds_decode` and bounded file API `foj_atlas_dds_try_read`: absent file returns 0, accepted file 1, corrupt/unsupported/I/O error -1; any failure preserves output pixel buffer and metadata. File size is capped at 128+256*256*4 bytes.
- [x] In the optional native shader-backed GPU NRO, each research material can now source pixels from private SD card paths `sdmc:/switch/foj/gpu/material0.dds` and `material1.dds`. When missing, retain generated synthetic 8x8 textures. When present but invalid, exit research application rather than silently use unintended data. Image layouts and buffer-to-image copy rectangles use accepted file dimensions.
- [x] Increased independent CPU-visible RGBA8 staging pool to 0x90000 with two 0x40000 pixel slots. DDS width multiple-of-8 guarantees 32-byte aligned RGBA8 linear-row pitch. Existing per-draw material descriptor bindings are unchanged.
- [x] New `tests/test_gpu_atlas_dds.c` exercises invalid masks/flags/dimensions/size, omitted and truncated file, maximum 256x256 bounds, transactional rejection and real synthetic test files. Integrated GCC and Clang, strict C11, NDEBUG, ASan/UBSan, and clean/dependency fixtures.
- [x] **Actual GPU host CI run 39036526010 SUCCESS** (GCC and Clang), three `Private RGBA8 DDS atlas bounds, flags, file intake: PASS` outputs per compiler.
- [x] **Actual native devkitA64/UAM build run 39036526057 SUCCESS**: clear-smoke NRO 262200 bytes, texture-research NRO 290872 bytes, all three UAM DKSH modules built and validated. Artifact **12102068939**: https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39036526057/artifacts/12102068939.
- [x] **Research tools tests run 39036526025 SUCCESS**. Merged PR #21 into `main` as `566fd80578a77c6b496d270a1fb88387fc1a3331`.
- [x] Updated `docs/GPU_SWITCH_SMOKE_TEST.md` to describe private SD paths, supported format constraints and absence/failure behavior.
- [ ] Real PS3 compressed DDS (BCn/DXT) and PS3 layout/swizzling conversion remain unsupported. No PS3 content added to GitHub.
- [ ] Actual user-owned game atlas tests, physical Switch image upload/sampling, material correctness and presented pixels remain unverified.

## Stage 139: CPU-decode classic BC1/BC3 DDS into GPU RGBA8 — CI SUCCESS (2026-10-17)

- [x] Extended the existing user-local `gpu/atlas_dds.c` pipeline to accept classic DDS FourCC `DXT1` (BC1) and `DXT5` (BC3), decoding block data to tightly packed RGBA8 using the already bounded 256 KiB staging buffers. Existing uncompressed RGBA8 input remains supported.
- [x] Implemented RGB565 palette conversion; BC1 4-color and 3-color-with-transparent modes; BC3 unconditional 4-color mode; BC3 8-level and 6-level alpha interpolation and the special zero/255 alpha indexes, using endian-safe block loads.
- [x] Validates exact DDS header flags, FourCC, block-aligned height, linear compressed byte size, pixel flags, zeroed classic DDS masks, single image/mip and exact file length *before writing any output*. No BC2, BC4/5/6/7, DX10, mip chains, proprietary tiling or PS3 assets.
- [x] Expanded `tests/test_gpu_atlas_dds.c` with generated BC1 and BC3 synthetic blocks, endpoint interpolation/alpha checks, transparent texels, negative malformed headers and compressed file-read tests. Fixed the old negative helper to pass the full destination capacity so header-rejection tests cannot trivially pass just because capacity is too small.
- [x] Initial host CI caught incorrect arguments in a new test helper `put32`; repaired that compiler error and reran all checks.
- [x] **Actual GPU host regression run 39037261332: SUCCESS**, GCC and Clang ordinary, NDEBUG, ASan/UBSan. Logs report `Private RGBA8/BC1/BC3 DDS atlas decode, alpha and bounds: PASS` three times per compiler.
- [x] **Actual native devkitA64/UAM run 39037261317: SUCCESS**; shader-backed research NRO **294968 bytes**, independent clear NRO **262200 bytes**; 3 validated UAM DKSH modules; downloadable artifact `foj-gpu-native-research` ID **12102557872** at https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39037261317/artifacts/12102557872.
- [x] **Research tools tests run 39037261302: SUCCESS**. PR #22 merged into `main` as squash commit `02fbf3528ec0d5c993c4614f65db4daca8b75f9f`.
- [x] Updated `docs/GPU_SWITCH_SMOKE_TEST.md` with stage 139 compressed format constraints, behavior, current artifact and explicit runtime verification limitations.
- [ ] No physical Switch verification, no actual FoJ PS3 texture ingest, and no validation of PS3-specific swizzle/tiling/mip data yet. Native toolchain success is **not** proof of correct GPU output.

## Stage 140: classic DDS BGRA8 + validated mipmap tails — native CI SUCCESS (2026-10-17)

- [x] Extended `gpu/atlas_dds.c` to accept the classic 32-bit BGRA8 channel mask layout (R=0x00ff0000, G=0x0000ff00, B=0x000000ff, A=0xff000000) and normalize loaded base-level pixels to tightly packed RGBA8.
- [x] Added complete classic DDS mip-chain validation for existing RGBA8, BGRA8, BC1/DXT1 and BC3/DXT5 paths: exact DDSD_MIPMAPCOUNT/DDSCAPS flags for multiple levels, valid count 1..9, exact total file bytes, block-rounded BC tail sizes and base-level pitch/linear compressed size. No writes to output until all headers/bounds validate.
- [x] The renderer continues to upload only top-level pixels to the same GPU deko3d image and sampler; it does **not** allocate additional mip levels, enable GPU mip filtering or load proprietary PS3 formats. Source DDS file size is now bounded at 384 KiB to accept complete 256×256 chains; decoded RGBA8 remains at most 256 KiB.
- [x] Expanded `tests/test_gpu_atlas_dds.c`: BGRA channel swizzle, missing/extra bytes, invalid masks/count/flags/caps, full uncompressed 8×8 four-level mip chain, BC1/BC3 multi-level compressed tails and a complete 256×256 nine-level DDS loaded from a synthetic local test file.
- [x] **Actual GPU host regression run 39037930668 SUCCESS** with GCC and Clang. All three variants (ordinary, NDEBUG, ASan/UBSan) print `Private RGBA8/BGRA8/BC1/BC3 DDS + complete mip-chain intake: PASS` for each compiler.
- [x] **Actual native devkitA64/UAM run 39037930630 SUCCESS**: research GPU NRO **294968 bytes**, independent clear NRO **262200 bytes**, all three UAM DKSH modules compiled and validated; artifact `foj-gpu-native-research` **12103085997**: https://github.com/stanmasked/vandal-hearts-foj-switch/actions/runs/39037930630/artifacts/12103085997.
- [x] **Research tools tests 39037930657 SUCCESS**. PR #23 merged to `main` as `150db82e2ddc5e5a7c77a067b9abc20dcf5801ab`.
- [x] Updated `docs/GPU_SWITCH_SMOKE_TEST.md` with current supported DDS variants, level-0-only restriction and latest native artifact.
- [ ] No physical Switch verification of pixel sampling/presentation, and no original FoJ PS3 atlas has been checked. PS3-specific layout/swizzle and unsupported DDS variants remain future work.

## Stage 141: evidence-first private FoJ PS3 texture candidate inventory — CI SUCCESS (2026-10-17)

- [x] Reviewed accessible project/repository files: original FoJ PS3 multipart package contents are **not accessible in this checkout**, so the original game's texture formats, container indexes, swizzling and per-resource atlas dimensions **cannot yet be identified as confirmed facts**. Historical texture libraries for the 1996 *Vandal Hearts* are a distinct project and must not be mistaken for *Flames of Judgment*.
- [x] Added read-only, metadata-only `tools/foj_texture_probe.py`: scans user-local extracted directory files in 1-MiB chunks with 127-byte overlap; identifies candidate DDS headers at file start or embedded offsets; parses plausible dimensions, FourCC/raw channel layouts, mip count and estimated linear payload sizes. Labels the results explicitly as candidates, never as verified FoJ textures.
- [x] Scanner defaults are 20,000 scanned regular files, file-size cap 512 MiB and up to 128 magic occurrences per file; follows no symlinks, extracts no content and does not upload any data. Outputs only a user-requested local JSON report with relative filenames and metadata; recommended path `local-data/foj-texture-candidates.json` is gitignored.
- [x] Added seven standard-library synthetic tests `tests/test_foj_texture_probe.py`: classic BC1 and BC3 candidates, BGRA8 masks/mip-size computation, invalid and unknown FourCC, a header split across a 1-MiB chunk boundary, deterministic inventory order, file limits and a CLI report excluding original byte strings and absolute paths.
- [x] Added `.github/workflows/texture-probe-tests.yml`, independently checking Python **3.10 and 3.12**. **Actual GitHub Actions run 39038809095 SUCCESS**, both jobs reporting **7 tests OK**.
- [x] First full research tests reported `TypeError: unhashable type: bytearray` when the parser received a mutable header fixture. Corrected FourCC lookup by converting the slice to `bytes`.
- [x] **Actual Research tools tests run 39038809102 SUCCESS** on Python **3.11 and 3.13**; 124 tests passed per environment.
- [x] Added `docs/FOJ_TEXTURE_RESOURCE_RECON.md` with private local workflow, explicit interpretation limits and requirements for validating actual PS3-specific formats. PR #24 merged to `main`, squash commit `078bb0e5378a0978c07bc498839b90186fdc54ab`.
- [ ] Run metadata inventory against user-owned, locally extracted **actual FoJ PS3** resource files and independently verify candidate formats; no such input was available to test this stage. No original game data has been uploaded to GitHub.
- [ ] Physical Switch testing of texture uploads, presentation and the actual FoJ game renderer remains outstanding.

## Stage 142: offline DDS candidate container spans and possible pointer hints — CI SUCCESS (2026-10-17)

- [x] Added `tools/foj_texture_relations.py`, a **metadata-only follow-up** to `tools/foj_texture_probe.py`. It reads the stage-141 local candidate JSON and groups entries by relative container filename; produces tentative DDS end offsets, adjacent/separated/overlapping ranges, next header offsets and explicit unknown-size entries.
- [x] Added an **optional** bounded read-only scan of each candidate-bearing file's first 64 KiB (configurable, maximum 1 MiB), looking for **4-byte aligned LE/BE 32-bit words** that coincide with same-file embedded DDS candidate offsets. Matches within candidate image spans are excluded, and only 16 hints per candidate are emitted by default. These are numerical coincidences, **not** established material/model links.
- [x] Paths taken from input JSON must be safe relative filenames; path traversal, symlink targets and unexpected non-regular files are rejected. Private source bytes and absolute root paths are never emitted. Input assets remain outside GitHub; JSON reports are written only to user-designated local files.
- [x] Added `tests/test_foj_texture_relations.py` with six SDK-free synthetic tests: range grouping/overlap, unknown-size handling, explicit LE/BE pointers at embedded offsets and skipped DDS payload words, hard caps, unsafe filenames/symlinks, and CLI metadata-only mode.
- [x] Expanded `.github/workflows/texture-probe-tests.yml` for both old and new probe test sets. First CI run exposed a test fixture window too short to hold a complete 32-bit pointer; changed the test prefix to 8 bytes.
- [x] **Actual private texture CI run 39039589895: SUCCESS** under Python 3.10 and 3.12; each passed the seven stage-141 tests and six new stage-142 tests (**13 per Python version**).
- [x] **Actual Research tools tests run 39039589884: SUCCESS** under Python 3.11 and 3.13, **130 tests per interpreter**. PR #25 merged to `main` as `388a734839d906e179dc6be84fb63c17a85075fa`.
- [x] Updated `docs/FOJ_TEXTURE_RESOURCE_RECON.md` with the two-stage offline commands, pointer-prefix options and interpretation limits.
- [ ] No original FoJ PS3 resource dump was available, so no true FoJ DDS header, container pointer structure or texture/material/model association has been confirmed.
- [ ] Switch hardware rendering and correct texture sampling are not verified.

## Stage 143: private DDS reference-table hypotheses — CI SUCCESS (2026-10-17)

- [x] Added `tools/foj_resource_table_hypotheses.py`, which reads **only** the stage-142 numeric JSON report and looks for maximal fixed-stride runs of file-relative DDS candidate offsets, separately for little-endian and big-endian hints (4, 8, 12, 16, 24, 32-byte strides). Default minimum is **three distinct target candidates**.
- [x] Discards ambiguous word positions and redundant subset stride-runs. Validates report schema, paths, file offsets, prefix bounds, alignment, endian labels and numeric sizes. Caps input containers/candidates/reference hints and table output. Neither original game assets nor plaintext resource bytes are needed, decoded or uploaded.
- [x] Added `tests/test_foj_resource_table_hypotheses.py` with **seven wholly synthetic tests**: end-to-end probe→relation→table pipeline with distinct LE/BE reference runs, repeated targets, suppressing shorter alternative strides, ambiguous addresses, malformed/untrusted reports, output bounds, separate containers and local CLI privacy.
- [x] Extended `.github/workflows/texture-probe-tests.yml`: **actual GitHub Actions run 39040334555 SUCCESS**, with 7 probe + 6 relations + 7 new table tests (**20 tests each**) under Python **3.10 and 3.12**.
- [x] **Actual Research tools CI run 39040334552 SUCCESS**: **137 tests each** under Python **3.11 and 3.13**.
- [x] Documented the optional purely local follow-up command and its interpretation limits in `docs/FOJ_TEXTURE_RESOURCE_RECON.md`.
- [x] PR #26 merged into `main` as squash commit `ebb41d833763a49d036eb4e338135d2e46ad3da9`.
- [ ] No real FoJ PS3 resource dump has been examined: repeated aligned values are only **numeric coincidences**, not an established texture/material/model relationship or a confirmed original container format.
- [ ] No new GPU NRO or hardware-side functionality was added this stage; physical Switch GPU rendering remains unverified.

## Stage 144: DDS index-like columns and negative-control sampling — CI SUCCESS (2026-10-17)

- [x] Added `tools/foj_index_column_controls.py`, a bounded **read-only** follow-up to stage-143 fixed-stride DDS pointer-table hypotheses. It inspects aligned 32-bit words adjacent to a pointer position in each candidate row, using the same little-/big-endian convention as the hypothesized table.
- [x] Requires four or more candidate rows and a record stride of at least eight bytes by default; labels exact `0..N-1` ascending patterns or zero-based permutations. Repeated fields, arbitrary increasing values and pointer-only (four-byte) rows are **not** treated as evidence of a material or model index.
- [x] Compares candidate index-like columns to up to 256 bounded, same-stride **independent windows** sampled from the file prefix, excluding windows that overlap the suspected table. Reports a `index-like-with-control-matches` warning if similar dense patterns occur elsewhere. This is a descriptive negative control and not a probability, statistical confidence score or proof of actual FoJ formats.
- [x] Validates JSON schema, candidate table bounds, byte order, target counts, numeric limits, relative paths, and symlink restrictions. Reads at most 64 KiB of local binary input per file by default (maximum 1 MiB); output includes only numeric summaries and relative filenames, never proprietary image/model bytes.
- [x] Added eight synthetic tests `tests/test_foj_index_column_controls.py`: complete invented DDS probe→relations→table→column pipeline, LE/BE and permuted indexes, repeated/out-of-range numbers, independent decoy windows, pointer-only rows, untrusted/invalid table input, symlinks/capacity and CLI output privacy.
- [x] **Actual GitHub Actions private texture CI run 39048074873 SUCCESS** for Python 3.10 and 3.12: previous 7 + 6 + 7 and new 8 tests = **28 passing tests per version**.
- [x] **Actual Research tools CI run 39048074863 SUCCESS** for Python 3.11 and 3.13, **145 passing tests per version**.
- [x] Documented offline use and evidence limitations in `docs/FOJ_TEXTURE_RESOURCE_RECON.md`; PR #27 merged to `main` as squash commit `6d49dce8c4ddfd41fc92c13beab28abdea0d5566`.
- [ ] Original FoJ PS3 files were not available in this stage; no candidate table/index or texture→material→model association has been confirmed from actual game data.
- [ ] This stage does not change NRO builds or verify hardware. Physical Switch presentation and real game rendering remain untested.

## Stage 145: cross-report FoJ texture candidate consistency and false-positive triage — CI SUCCESS (2026-10-17)

- [x] Added `tools/foj_evidence_triage.py`, a **metadata-only** reconciler for the stage-142 DDS span/pointer report, stage-143 fixed-stride table hypotheses and stage-144 index-column/negative-control observations. It reads JSON only, not proprietary PS3 game assets.
- [x] Reconciles exact relative filenames, per-table start/stride/count/endian, individual row positions and DDS destinations against actual prior pointer hints, classified DDS spans and index/control observations. Validates schema ancestry, path safety, numeric capacities, count invariants and limits.
- [x] Generates deterministic reason-coded internal triage labels: `internally-contradicted` for absent target/pointer matches or known-size overlapping DDS candidates; `insufficient-or-ambiguous` for unknown image sizes, missing/negative/ambiguous indices or matching negative-control windows; `internally-consistent-for-private-review` only when none of these internal warnings applies. **These reports are dependent on the same original scanner, not independent confirmation**, probabilities, confidence estimates or real FoJ format recognition.
- [x] Added nine wholly invented test cases in `tests/test_foj_evidence_triage.py`, exercising complete DDS→layout→pointer table→index controls→triage pipeline, LE/BE, negative controls, no-index cases, corrupted pointers, overlaps vs unknown sizes, missing records, malformed metadata, empty manifests and CLI output privacy.
- [x] Initial CI exposed a gap in sampled negative controls: the synthetic decoy position lay between the default 256 sampled windows. Updated the small fixture to use 1024 windows (exhaustive at that fixture size) and explicitly documented that no sampled control hits **does not guarantee** absence of coincidences.
- [x] **Actual dedicated GitHub Actions run 39049324713 SUCCESS**, Python 3.10 and 3.12: 7 previous metadata tests + 6 relation + 7 table + 8 index + 9 new triage = **37 passing tests per interpreter**.
- [x] **Actual research tools CI run 39049324701 SUCCESS**, Python 3.11 and 3.13, **154 tests per interpreter**.
- [x] PR #28 merged to `main` via squash as `7c7b23c1fd138e1a2c5f21d26836ddfd7346f485`. Documented local stage-145 CLI usage and evidence limitations in `docs/FOJ_TEXTURE_RESOURCE_RECON.md`.
- [ ] No privately extracted real FoJ PS3 files available for analysis; original material/model mappings, native resource formats and container structures remain unknown.
- [ ] No new GPU NRO features or on-console Switch testing this stage; hardware frame presentation remains unverified.

## Stage 146: private split-cohort DDS hypothesis repeatability — CI SUCCESS (2026-10-17)

- [x] Added `tools/foj_holdout_replication.py`, a **read-only, aggregate-only** comparer of **two stage-145 reports from separate local cohort roots**. It compares candidate fixed-stride pointer-table shapes by stride and byte order, ignoring absolute file offsets and row counts, and labels patterns as repeated-but-unverified, not reproduced, ambiguous, contradicted, holdout-only or insufficient.
- [x] Strengthened accidental data reuse protection: roots must exist, must differ and must not be nested; source files must be ordinary regular files reached without symlink traversal; shared hardlink device/inode identities across cohorts are rejected. Source bytes and file contents are **never published or included in JSON output**. Distinct inodes do not prove content independence; copied files and genuine PS3 provenance remain unverified.
- [x] Validates metadata-only input schemas, triage/summary invariants, reason codes, endian/stride, row counts, file paths and size/count bounds. Accepts `--min-consistent` to require more internally consistent table occurrences before labeling repeated patterns. No original PS3 assets or copyrighted bytes are included.
- [x] Added ten generated tests in `tests/test_foj_holdout_replication.py`, including repeated patterns in separate roots, different offsets, non-reproduction, holdout contradictions, ambiguity, minimum repeat thresholds, nested/symlink/hardlink reuse rejection, corrupted report claims, empty reports, metadata-only CLI and full end-to-end DDS→relations→table→index→triage→holdout using **different synthetic source files**.
- [x] Initial CI exposed an overly strict expected label: one holdout hit below the two-occurrence threshold is **insufficient reproducibility**, not complete non-observation. Fixed the test, added end-to-end integration, then reran all CI.
- [x] **Actual GitHub Actions dedicated run 39050122009 SUCCESS**: Python 3.10 and 3.12, **47 tests per interpreter** (7+6+7+8+9+10).
- [x] **Actual Research tools run 39050121941 SUCCESS**: Python 3.11 and 3.13, **164 tests per interpreter**.
- [x] Added the local split-cohort workflow and limitations to `docs/FOJ_TEXTURE_RESOURCE_RECON.md`; **PR #29 merged** to `main` as squash commit `031166ebb4977f208f420436e6568290c05c2afc`.
- [ ] Real user-owned original FoJ PS3 resource archives and their extracted data were **not** available in this session. No actual game DDS container, material index or model binding has been verified from original content.
- [ ] No GPU NRO changes were made this stage, and framebuffer presentation / texture sampling on physical Nintendo Switch remain unverified.

## Stage 147: deterministic synthetic structural-stability matrix — CI SUCCESS (2026-10-17)

- [x] Added `tools/foj_stability_matrix.py`: a **synthetic-only** deterministic harness that creates tiny invented DDS files in two short-lived local cohort directories, runs the existing DDS candidate → span/pointer relation → hypothetical table → adjacent index/control → evidence triage → holdout comparison pipeline, and checks expected descriptive labels. All generated binary files are deleted with the temporary directories.
- [x] Seven authored regression scenarios vary row count (3, 4, 6, 8), pointer-table stride (8 vs 16), LE vs BE encoding, zero-based index permutation, repeated index values, and a separate independent decoy dense-index control window. Unexpected heuristic labels are explicitly reported and cause the CLI to exit nonzero; the JSON contains **synthetic aggregate statistics only**.
- [x] Added nine tests `tests/test_foj_stability_matrix.py`: seven-case matrix success, deterministic identical reports, purposeful expected-label regression detection, short-three-row underdetermination, false-positive control detection, invalid parameter rejection, temporary binary fixture bounds, request bounds and metadata-only CLI output.
- [x] Updated Python 3.10/3.12 private texture workflow, SDK-free syntax checks, and `docs/FOJ_TEXTURE_RESOURCE_RECON.md` with the local synthetic-only command and explicit non-game evidence caveats.
- [x] **Actual dedicated GitHub Actions run 39051066035 SUCCESS**, both Python **3.10 and 3.12** jobs, **56 tests each** (7+6+7+8+9+10+9).
- [x] **Actual Research tools CI run 39051066019 SUCCESS**, Python **3.11 and 3.13**, **173 tests per interpreter**.
- [x] PR #30 merged into `main` as squash commit `6113fd66ff26d4bd307e8ee0ac661e4976b23c84`.
- [ ] No actual original FoJ PS3 game assets were available: observed stability applies **only to invented fixtures** and does not prove real game container formats, texture/material/model relationships, or sample provenance.
- [ ] Native GPU NRO was unchanged at stage 147; physical Nintendo Switch texture sampling, image readback and frame presentation remain unverified.

## Stage 148: corrupted DDS/container and truncated-payload controls — CI SUCCESS (2026-10-17)

- [x] Extended stage-142 `tools/foj_texture_relations.py` to preserve the optional stage-141 `payload_check` field in local candidate relation metadata. Validates allowed classifications and remains backward compatible with metadata reports lacking the field.
- [x] Extended stage-145 `tools/foj_evidence_triage.py` to emit `dds-payload-truncated` and mark a candidate table as `internally-contradicted` whenever a known-size DDS advertises an image payload beyond the source file's final byte, even if a plausible table still points at the header.
- [x] Added `tools/foj_corrupt_container_matrix.py`, a deterministic **12-scenario synthetic-only** generator exercising corrupt DDS signature/header size/width, two broken headers, missing or unaligned reference words, incomplete last header, truncated image, unknown FourCC, shifted-but-valid embedded DDS and trailing container bytes. Uses the whole existing scan→relations→table→index→triage pipeline and fails on unexpected candidate counts or heuristic labels.
- [x] Added **11 generated tests** in `tests/test_foj_corrupt_container_matrix.py` validating all authored scenarios, reproducibility, exact truncated-payload reason, no invented pointer links, partial headers, unaligned embedded DDS acceptance, invalid metadata/check labels, unknown FourCC, intentional regression detection, invalid matrix parameters and metadata-only CLI.
- [x] First GitHub CI found an overly strict privacy test that disallowed the harmless literal phrase `DDS ` in the report description. Updated it to reject embedded binary control escapes instead; no game source data is included or copied to GitHub.
- [x] **Actual dedicated private texture CI run 39051728025 SUCCESS**, Python 3.10 and 3.12, **67 tests each** (previous 56 plus 11).
- [x] **Actual Research tools CI run 39051728037 SUCCESS**, Python 3.11 and 3.13, **184 tests each** (previous 173 plus 11).
- [x] Updated `docs/FOJ_TEXTURE_RESOURCE_RECON.md` with synthetic corruption command, truncated-DDS detection, unknown-format limits and alignment nuances. PR #31 merged to `main` as squash commit `ca466f15d56cfc2608ede5e4ab232cdb68c0de28`.
- [ ] No original FoJ PS3 binary/container was available for direct research, so no original material/model/texture map or game resource format has been identified.
- [ ] Stage 148 changes only the offline diagnostic tools. GPU NRO, real on-console frame presentation and texture-sampling verification are unchanged/unverified.
