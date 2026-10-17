# Stage 170 — manually align CPU boot checkpoints with observed GPU screens

**Still no hardware attestation.** This is a PRIVATE, offline research
comparison, not a playable Nintendo Switch game or physical GPU test.
The program does not capture screenshots, authenticate a console,
read original PS3 resources or establish which frames actually appeared.

## Why explicit linking is essential

Stage 169 produces a CPU-side comparison of two startup journals
(`foj-boot-00.txt` and a later `foj-boot-01.txt`, for example).
Stage 166 produces a separate, manually completed observation sheet
for the five synthetic GPU scenarios A–E. Those scenarios may have
been run **at different times**, even with a different NRO build.

It would be incorrect to infer that an observation in the A–E sheet
belongs to the CPU log with the same expected colors, or that a
CPU `present` call guarantees real display on Switch.

The stage-170 comparison therefore requires a **third, explicit
operator-only association**. Its default value is completely blank.
No implicit or automatic association is permitted.

## Stage 171 — guard against mixing different research builds

Stage 171 separately validates the SHA-256 of the complete generated
stage-165 SD ZIP, the two research NRO binaries and the two DKSH
shaders, and binds the CI commit/run ID to all *filled* stage-166
build-metadata fields. This rejects inconsistent build combinations
without automatically associating operator scenarios with a run.
An optional local SD NRO copy can be compared by bytes, but it cannot
prove the console executed the file or presented the observed colors.
See `docs/GPU_STAGE171_BUILD_IDENTITY.md`.

## Local usage

From the repository root, create a new private form:

    python3 -m tools.foj_stage170_cpu_visual_alignment \
      --init-link ./private/cpu-screen-link.json

The file starts with only null fields:

```json
{
  "association_basis": null,
  "boot_slot": null,
  "schema": "foj-stage170-operator-scenario-link-v1",
  "visual_scenario": null
}
```

**Do not fill it merely because CI passed.** After physically performing
the research test, and only if you actually know which local
`foj-boot-XX.txt` session belongs to a specific A–E scenario in
your own stage-166 sheet, fill for example:

```json
{
  "association_basis": "operator_reports_same_launch",
  "boot_slot": 1,
  "schema": "foj-stage170-operator-scenario-link-v1",
  "visual_scenario": "C"
}
```

This is merely a statement that the operator associates the records;
the program cannot verify that association. If unsure, keep all fields
`null` and get an explicitly unlinked report.

Run the analyzer against **exactly two** separately copied local CPU
logs, your filled stage-166 private observation sheet and the link:

    python3 -m tools.foj_stage170_cpu_visual_alignment \
      --before ./private/foj-boot-00.txt \
      --after ./private/foj-boot-01.txt \
      --ledger ./private/gpu-observations.json \
      --link ./private/cpu-screen-link.json

If both boot logs describe a CPU recovery and the linked operator
scenario reports all three expected screens, the result can be
`cpu_and_operator_declarations_consistent_unverified`. Other
outcomes include:

| Comparison | Interpretation |
| --- | --- |
| `not_linked` | Blank association form; no claim that the logs refer to a selected visual scenario |
| `no_operator_visual_observation` | Explicitly linked scenario, but no visible result entered |
| `incomplete_operator_visual_observation` | One or two of three stage observations entered |
| `operator_visual_differs_from_test_expectations` | Operator's description differs from the synthetic scenario, even if CPU checkpoints advanced |
| `cpu_journal_does_not_support_visual_sequence` | The linked boot log does not record presentation-stage readiness with a positive call count, or includes an early initialization failure |
| `cpu_and_operator_declarations_consistent_unverified` | Two *human-supplied* accounts are internally consistent; actual screen display remains unverified |

The result always carries:

    "hardware_execution_verified": false
    "gpu_scanout_verified": false
    "original_foj_assets_verified": false
    "switch_gameplay_verified": false

It prints no private source path, screenshot, hardware identifier or
raw operator input. Link files cannot contain free-form notes or
arbitrary fields, reject duplicate JSON properties, symlinks and
invalid slots and are never overwritten when using `--init-link`.

## Boundaries of the evidence

A stage-166 A–E worksheet is not a per-run event stream: it is five
separate test scenarios. Binding one named scenario to one
CPU log is only a **manual assertion**, not a verified temporal
association. A screenshot SHA-256 declared by an operator is likewise
not machine-verified evidence. Two CPU records with ascending slot
numbers can have intervening attempts, and log files can be copied
from another test session.

Any apparent disagreement must be investigated using independent,
actually witnessed on-console behavior. A failure to record a CPU
checkpoint could arise from disabled SD logging or an interrupted
write; an on-screen result cannot be conclusively disproved by an
incomplete CPU journal.

Synthetic CI fixtures generate apparent successful recovery and
synthetic green-green checkerboards **entirely in code** to verify
comparison logic. These are not real Switch observations.

See also [stage 168 CPU checkpoints](GPU_STAGE168_EARLY_BOOT_JOURNAL.md),
[stage 169 two-attempt audit](GPU_STAGE169_TWO_ATTEMPT_RECOVERY.md)
and [stage 166 operator observation sheet](GPU_STAGE166_HARDWARE_OBSERVATIONS.md).
