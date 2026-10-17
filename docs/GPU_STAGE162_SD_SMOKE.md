# Stage 162 — manual Nintendo Switch DDS GPU smoke test

**This test has NOT been run on physical Switch hardware.** It uses two generated checkerboards, not PS3 game assets. A successful native NRO build is not an execution result.

## Stage 165 — reproducible SD smoke ZIP and checked command scheduling

A new **generated-only SD-ready ZIP** is published by the native
devkitA64/UAM build, with both research NROs, exactly two runtime
DKSH shaders and two invented checkerboard DDS images. No original FoJ
game assets are packaged. See `docs/GPU_STAGE165_SD_RELEASE.md`
for its fixed SD layout, checksums, extraction and download procedure.

The native shader-backed NRO now uses a shared command-list planner.
A host-only model verifies the first two 120-frame status phases, scene
transition, fatal-status hold and the exact acquired framebuffer for
4096 presentation decisions per scenario. Only an actual Switch test
can verify correct GPU scanout and responsiveness.

## Step 1: Prepare two synthetic files

From the repository root run the following commands on your development computer:

    python3 -m tools.foj_stage162_synthetic_dds ./stage162-smoke-dds
    python3 -m tools.foj_gpu_local_dds_preflight ./stage162-smoke-dds

The generator requires a NEW directory and will not overwrite existing files. It creates two distinct **8×8 classic RGBA8** DDS images, each 384 bytes (128-byte header plus 256 pixels). Material slot 0 is a red/yellow checkerboard; slot 1 is a cyan/blue checkerboard. The preflight must classify both as classic-dds-compatible.

## Step 2: Install your own successful native research build

Place the NRO and required shader files at these exact locations on the SD card of an authorized homebrew Switch:

    sdmc:/switch/foj/foj-deko3d-clear-smoke.nro
    sdmc:/switch/foj/foj-deko3d-triangle-research.nro
    sdmc:/switch/foj/gpu/foj_actor.vert.dksh
    sdmc:/switch/foj/gpu/foj_triangle.frag.dksh

The separate foj_actor.frag.dksh is not needed by the triangle research NRO. First launch the clear-smoke NRO and confirm that alternating colors are visible. Never infer a successful hardware test from CI alone. Files are copied manually; no project script accesses the console.

## Stage 164 — on-screen DDS intake diagnostics (not yet tested on Switch)

The shader-backed *research* NRO now presents **two full-screen status colors**
before showing the normal synthetic textured quads. It does not require
stderr, a font file or an additional DKSH shader. The **first 120 presented
frames are material slot 0**; the **next 120 presented frames are slot 1**.
After 240 frames, supported DDS uploads and synthetic fallback material
quads appear as before. Frame counts, not wall-clock seconds, determine
the transition; on-console frame pacing is unverified.

| Screen color | DDS intake status |
| --- | --- |
| Green | Classic DDS successfully CPU-decoded |
| Blue | Optional DDS missing; synthetic material fallback |
| Yellow/amber | Present DDS malformed or unsupported |
| Purple/magenta | Unsafe path, e.g. symlink/directory |
| Bright red | DDS read or close failed |
| Orange/red | DDS changed during reading |
| Dark red | Invalid internal DDS loader arguments |

**A failed DDS does not silently fall back.** For material 0 failure the
first status color remains visible until exit. For material 1 failure,
slot 0 appears during the first 120 frames, then the slot 1 error color
remains visible indefinitely. The triangle-research NRO retains a
nonzero exit status (5) for fatal DDS errors even if the user exits
normally with +. Only statuses from slots actually checked determine
the visible error sequence. A missing/invalid DKSH or other *earlier*
GPU initialization error can still prevent **any** status screen from
appearing; these colors diagnose DDS intake, not arbitrary boot failures.

The separate clear-only NRO remains unchanged and does not show this
new diagnostic prelude. Every status frame is issued by the GPU through
a persistent deko3d color-clear command list. CPU host tests verify
the fixed color legend, 120-frame transitions, failed-slot hold and
invalid input handling. The devkitA64 build verifies code generation,
not actual GPU scanout or visual correctness.

For stage-162 manual cases A–E, expect: A blue then blue, B green then
blue, C green then green, D green then amber (held), E green then green.
After each nonfatal pair, normal textured quads should become visible.
Observe the exact color sequence and whether it remains on the failure.
No private DDS bytes, file paths, game data or user text are drawn.

## Step 3: Run five independent cases

| Case | DDS presence in sdmc:/switch/foj/gpu | Expected |
| --- | --- | --- |
| A | Neither material0.dds nor material1.dds | Two different synthetic fallback textured quads |
| B | Only generated material0.dds | Red/yellow checkerboard on one quad, other quad uses fallback |
| C | Both generated DDS files | One red/yellow and one cyan/blue checkerboard |
| D | Valid material0.dds and intentionally invalid synthetic material1.dds | Triangle NRO rejects startup; invalid texture must not be silently used |
| E | Restore both generated DDS files | Successful startup and two checkerboard quads again |

For case D, use a NEW synthetic seven-byte file containing the literal word invalid. Do not edit or deliberately damage any user-owned original DDS or PS3 assets. Observe on-screen presentation, possible channel flips, tiling, missing shader errors and any freeze or abnormal exit. Press + to exit only after frames have been displayed in A/B/C/E, if possible. Record screenshots only from the synthetic tests.

## Stage 166 — optional private observation ledger

The workflow publishes an explicitly blank JSON worksheet next to the
stage-165 research SD ZIP. You may enter actual seen screen colors for
A–E and separately record any black screen before the first triangle
frame, plus-exit behavior or a freeze. The offline tool checks the
fixed sequence and (optionally) the SHA-256 of the exact local ZIP,
without asserting it can verify real Switch hardware. See
`docs/GPU_STAGE166_HARDWARE_OBSERVATIONS.md`. Do not invent outcomes
from CI builds or commit private screenshot files.

## Hardware observation log (not yet executed)

| Observation | Result |
| --- | --- |
| Switch hardware model and homebrew environment | Not tested |
| Test date and native GitHub Actions artifact | Not tested |
| Clear NRO presents alternating frames | Not tested |
| A: synthetic fallback materials | Not tested |
| B: single DDS + fallback | Not tested |
| C: two checkerboard DDS materials | Not tested |
| D: invalid file rejected | Not tested |
| E: recovery after restoring file | Not tested |
| Correct colors, orientation and texture sampling | Not tested |
| + exit cleanly terminates research NRO | Not tested |

## Stage 163 — native DDS path safety and status diagnostics

The updated native reader checks the final DDS pathname with `lstat`,
opens a regular file through a descriptor, and compares file identity and
timestamps with `fstat` before and after the two full byte reads. Where
supported by the Switch C runtime, `O_NOFOLLOW` prevents the final
pathname component from being a symbolic link at open. Direct symlinks,
dangling links, directories and FIFOs are rejected; only an **absent**
file activates the synthetic fallback. Native `O_NOFOLLOW` availability
is platform-dependent, so **do not assume race-free handling of ancestor
directory substitution or malicious concurrent file replacement**.

Each material slot emits a generic diagnostic to stderr when supported
by the homebrew environment. Messages have the form:

    FoJ GPU DDS material 0: classic DDS decoded
    FoJ GPU DDS material 1: optional texture absent

Other possible codes: `unsafe texture path`, `texture read or close
failed`, `texture changed during read`, `unsupported or invalid DDS`
and `invalid arguments`. These codes do not contain user paths,
filenames, texture bytes, source hashes, or original-game content.
**stderr is not guaranteed to be visible on a physical Switch**.
If the environment exposes logs, capture only these generic messages;
otherwise record the observed startup result. Do not interpret a
successful read as proof of GPU sampling or PS3 game assets.

The existing five manual scenarios (A–E) still apply. Expected status
pairs, in slot order: A absent/absent, B decoded/absent, C decoded/decoded,
D decoded/invalid DDS, E decoded/decoded. In scenario D the application
must not display a falsely successful second material.

## Security and interpretation

The stage-162 C loader re-reads the bounded DDS file from the SAME open stream and compares its exact bytes before closing and decoding. This detects ordinary concurrent edits and unexpected append/truncation. It is **not** an atomic filesystem snapshot, protects neither against an adversarial rewrite-and-restore race nor malicious path substitutions, and malicious path substitutions. The stage-163 native loader rejects final-component symlinks and uses O_NOFOLLOW when available; ancestor substitution and later replacement on SD are still not fully excluded. Use trusted, user-controlled paths.

Even after a verified all-green hardware smoke test, this only confirms GPU rendering of TWO generated research materials. It does not establish any original Flames of Judgment material mapping, scene rendering, gameplay or completed Nintendo Switch port.
