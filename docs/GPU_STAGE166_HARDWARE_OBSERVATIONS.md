# Stage 166 — honest on-console GPU observation audit

**No Nintendo Switch has been operated or observed by this CI workflow.**
This stage adds a reproducible **private, offline operator worksheet** for
the research-only NROs. It does not read screenshots, perform computer
vision, prove an observer is genuine, or report successful physical
execution merely because someone typed the expected colors.

## Get the test binaries and an empty worksheet

Open a successful [Native Switch GPU NRO and DKSH build](https://github.com/stanmasked/vandal-hearts-foj-switch/actions/workflows/gpu-native-build.yml)
run and download the `foj-gpu-native-research` artifact. It contains
`foj-stage165-gpu-sd-smoke.zip` (research NROs, two compiled shaders and
synthetic checkerboard DDS images) plus
`foj-stage166-blank-observations.json`. The latter has **all hardware
observations set to null** and must never be interpreted as CI hardware
evidence. Follow [stage 165](GPU_STAGE165_SD_RELEASE.md) to copy the
contents of the ZIP's `switch/` directory manually to the SD card of
an authorized homebrew Switch.

Alternatively, create a fresh blank local worksheet already bound to
the exact validated ZIP you will place on SD:

    python3 -m tools.foj_stage166_hardware_observations \
      --init ./private-foj-gpu-observations.json \
      --bundle ./foj-stage165-gpu-sd-smoke.zip

This verifies that the ZIP has the expected fixed paths, generated
checkerboards, structurally valid NRO/DKSH files and internal SHA-256
manifest. The computed full-archive hash is inserted into the
worksheet. The tool **refuses to overwrite** a worksheet, does not
transfer anything to Switch, and does not fill the device information
or any visual observation.

## Record actual observations, not expected ones

Edit your **local private** JSON and enter the tested Git commit,
GitHub Actions run ID, Switch model, Homebrew Menu launch mode and
local test date. For each scenario A–E, observe the sequence of:

- `slot0` — first screen, expected during presented frames 0–119
- `slot1` — second screen, expected during presented frames 120–239
- `after_240` — expected scene with one/both synthetic quads, or
  error color held if the second DDS was invalid

Expected values:

| Scenario | slot0 | slot1 | after_240 |
| --- | --- | --- | --- |
| A: no DDS | blue | blue | two_fallback_quads |
| B: first DDS only | green | blue | checkerboard_plus_fallback |
| C: both synthetic DDS | green | green | two_checkerboards |
| D: malformed second DDS | green | amber | error_held |
| E: recovered both DDS | green | green | two_checkerboards |

The JSON `seen` fields use the literal strings shown in the table.
For unusual outcomes, use `black_screen` or `unexpected_output` rather
than pretending that a status was actually presented. **Do not fill
`seen` from the expected table before launching the actual console.**
The optional `capture_sha256` value can hold a locally calculated
SHA-256 of an original screen recording or screenshot. No media paths,
photos or videos are uploaded by this tool; capture hashes are only
declarations supplied by the operator, not proof of authenticity.

Record startup and initialization symptoms separately in `startup`:

- `clear_smoke_visual`: alternating_colors / black_screen /
  unexpected_output
- `triangle_launch_visual`: dds_status_screen / black_screen /
  unexpected_output
- `triangle_exit_observed`: plus_clean / plus_nonzero_reported /
  freeze_or_crash / not_visible_in_homebrew
- `failure_phase_observed`: before_first_frame / during_dds_status /
  during_textured_scene / no_failure_observed / unknown

A black screen **does not establish a DKSH or driver root cause**.
These are operator descriptions only. They do not instrument GPU
queues, title launch, or libnx error codes. An early failed shader
load can prevent any color diagnostic, as before.

## Audit and keep the result private

    python3 -m tools.foj_stage166_hardware_observations \
      --audit ./private-foj-gpu-observations.json \
      --bundle ./foj-stage165-gpu-sd-smoke.zip

The tool fails closed on duplicate JSON properties, unexpected keys,
malformed/hash-mismatched archive, invalid enum or out-of-order
scenario/stage records. Its output reports per-scenario
`not_observed`, `incomplete`, `matches_expected`, or
`differs_from_expected`. The output intentionally contains no
user-entered device data, local source paths, notes, screenshot
filenames, or screenshots.

**Crucial distinction:** even a fully filled worksheet whose colors
match the expected patterns returns
`"hardware_execution_verified": false` and
`"evidence_level": "operator-declared-only; no automatic hardware attestation"`.
The comparison tells you whether the user-entered report is internally
consistent with the predicted GPU smoke behavior, **not** that the
console actually presented those frames. Only separately inspected
real physical-console captures and reproducible hardware observations
could support a stronger statement.

Do not commit completed observations, photos, original PS3 files,
console-unique details or any commercial FoJ resource bytes to the
public repository.
