# Stage 162 — manual Nintendo Switch DDS GPU smoke test

**This test has NOT been run on physical Switch hardware.** It uses two generated checkerboards, not PS3 game assets. A successful native NRO build is not an execution result.

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

## Step 3: Run five independent cases

| Case | DDS presence in sdmc:/switch/foj/gpu | Expected |
| --- | --- | --- |
| A | Neither material0.dds nor material1.dds | Two different synthetic fallback textured quads |
| B | Only generated material0.dds | Red/yellow checkerboard on one quad, other quad uses fallback |
| C | Both generated DDS files | One red/yellow and one cyan/blue checkerboard |
| D | Valid material0.dds and intentionally invalid synthetic material1.dds | Triangle NRO rejects startup; invalid texture must not be silently used |
| E | Restore both generated DDS files | Successful startup and two checkerboard quads again |

For case D, use a NEW synthetic seven-byte file containing the literal word invalid. Do not edit or deliberately damage any user-owned original DDS or PS3 assets. Observe on-screen presentation, possible channel flips, tiling, missing shader errors and any freeze or abnormal exit. Press + to exit only after frames have been displayed in A/B/C/E, if possible. Record screenshots only from the synthetic tests.

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

## Security and interpretation

The stage-162 C loader re-reads the bounded DDS file from the SAME open stream and compares its exact bytes before closing and decoding. This detects ordinary concurrent edits and unexpected append/truncation. It is **not** an atomic filesystem snapshot, protects neither against an adversarial rewrite-and-restore race nor malicious path substitutions, and native fopen still follows symlinks. The stage-161 local Python preflight uses no-follow access, but it does not protect against future replacement on SD. Use trusted, user-controlled paths.

Even after a verified all-green hardware smoke test, this only confirms GPU rendering of TWO generated research materials. It does not establish any original Flames of Judgment material mapping, scene rendering, gameplay or completed Nintendo Switch port.
