# Stage 165 — ready-to-copy generated-only Switch GPU research ZIP

**Research-only, not a playable game. No physical Nintendo Switch test has been performed.**

The stage-165 CI build publishes `foj-stage165-gpu-sd-smoke.zip` within
the **foj-gpu-native-research** artifact of the
[Native Switch GPU NRO and DKSH build](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/workflows/gpu-native-build.yml)
workflow. It is generated after devkitA64 has validated both NROs and
UAM has compiled the DKSH modules. This is a convenient manual test
package, **not** evidence that the NRO runs on a physical console.

## Exact ZIP layout

The archive contains only these fixed, repository-generated entries:

| ZIP path | Intended use |
| --- | --- |
| `switch/foj/foj-deko3d-clear-smoke.nro` | Shader-free GPU clear-color check |
| `switch/foj/foj-deko3d-triangle-research.nro` | Two-material DDS/GPU command test |
| `switch/foj/gpu/foj_actor.vert.dksh` | Generated research vertex shader |
| `switch/foj/gpu/foj_triangle.frag.dksh` | Generated research fragment shader |
| `switch/foj/gpu/material0.dds` | Synthetic 8×8 red/yellow checkerboard |
| `switch/foj/gpu/material1.dds` | Synthetic 8×8 blue/cyan checkerboard |
| `README_STAGE165.txt` | Safety limits and short manual instructions |
| `MANIFEST_STAGE165.json` | File sizes and SHA-256 for these seven entries |

The ZIP is fixed-layout and does **not** recursively include content
from the repository, source directories, PS3 archives, user texture files,
private trace logs or original game assets. NRO/DKSH metadata is structurally
validated before staging. The scripted builder refuses to overwrite a
previously created ZIP. ZIP entries have canonical timestamps and ordering;
the same fixed input binaries yield a byte-identical package. The
checksums are for detecting accidental transport changes, **not** proof
of original game provenance, source legitimacy or console execution.

## Create from a local verified build

From the repository root, after running the normal native build:

    make -f gpu/clear.mk verify
    make -f gpu/triangle.mk verify
    make -f gpu/Makefile triangle-verify
    python3 -m tools.foj_stage165_sd_bundle --repo-root . --output build/foj-stage165-gpu-sd-smoke.zip

For CI builds, select a successful workflow run and download the
`foj-gpu-native-research` artifact. Extract the inner
`foj-stage165-gpu-sd-smoke.zip`, and then copy **only the contents**
of its `switch/` directory to the root of your SD card on an
*authorized homebrew Nintendo Switch*. Do not copy `switch/switch/`
or overwrite existing user-owned files without checking their names.

## Stage 166 — record what actually happened on Switch

The native GitHub Actions artifact now also includes an entirely EMPTY
`foj-stage166-blank-observations.json`. Fill it **only after physically
observing frames** on an authorized homebrew Switch. The offline tool
`python3 -m tools.foj_stage166_hardware_observations` can bind the
worksheet to the structural/cryptographic manifest of the generated
stage-165 ZIP and compare declared colors in A–E, including a separate
category for black-screen or pre-frame boot failure. The audit never
claims to have independently verified actual hardware execution.
Full instructions: `docs/GPU_STAGE166_HARDWARE_OBSERVATIONS.md`.

## Manual hardware checks

1. Launch `foj-deko3d-clear-smoke.nro`; verify alternating full-screen
   colors. Return to Homebrew Menu with **+** after visible frames.
2. Launch `foj-deko3d-triangle-research.nro`; with both included
   synthetic textures, expect **green for material 0** during frames
   0–119, **green for material 1** during 120–239, then two distinct
   red/yellow and blue/cyan checkerboard quads.
3. Repeat the A–E cases in
   [the original hardware observation plan](GPU_STAGE162_SD_SMOKE.md)
   (missing files, one DDS, both DDS, malformed DDS, recovery).
   For an intentionally invalid DDS, never edit private source files.
4. Record hardware model, homebrew version, exact Git commit, artifact
   run ID, observed colors, whether they transition as expected,
   whether images are visible/correctly oriented, and any error code.
   Enter **Not tested** for anything not actually observed.

**Stage-165 command-list model:** a pure C test verifies the actual
native command-selection function under 4096 submitted/presented
frames for each of three DDS scenarios (healthy pair, early failure,
second-slot failure). It simulates two potentially non-alternating
swapchain buffer acquisitions and ensures a failure never selects
normal scene commands. GCC, Clang and sanitizer tests cover this
model; it does not simulate actual GPU execution or VRAM.

This project still has **no verified extraction/mapping of original
Flames of Judgment textures, gameplay, or GPU presentation on real
Switch hardware**. Do not redistribute original PS3 resources.
