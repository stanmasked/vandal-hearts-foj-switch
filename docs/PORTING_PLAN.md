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
