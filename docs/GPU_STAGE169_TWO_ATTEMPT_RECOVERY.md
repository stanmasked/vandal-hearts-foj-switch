# Stage 169 — compare two private GPU CPU startup attempts

**This tool is an offline comparison of two user-supplied CPU checkpoint
logs. It does not start a Nintendo Switch, attest an operator, verify
GPU scanout or prove the full game runs.**

Stage 168 introduced fixed, exclusive-new text logs with sequential names:

    sdmc:/switch/foj/gpu/foj-boot-00.txt
    sdmc:/switch/foj/gpu/foj-boot-01.txt
    ...
    sdmc:/switch/foj/gpu/foj-boot-15.txt

After a failed launch and a subsequent test of the same research NRO,
copy **only the two selected logs** into a private local directory.
No directory crawling, upload, video recording or resource extraction
is performed by the analyzer.

From the repository root:

    python3 -m tools.foj_stage169_two_attempt_recovery \
      --before ./private/foj-boot-00.txt \
      --after ./private/foj-boot-01.txt

The earlier slot must be numerically lower than the later slot.
The tool allows intervening logs but **does not assume that the two
slots are consecutive in wall-clock time**. Each input file must
have a fixed name, a bounded size, exact numeric line layout, two
identical descriptor-anchored reads, unchanged file metadata and
strictly ordered enter/outcome/exit events. Direct symlinks, FIFO
entries, malformed records, forged duplicate outcomes, decreasing
frame counts and reversed slot order are rejected.

### What the comparison means

- `later_attempt_reached_clean_cpu_exit` — the first log contains
  at least one CPU-recorded failure, while the second contains an
  orderly exit after reaching the CPU presentation stage with a
  positive recorded presentation-call count and no failed stages.
  This is **CPU-only progress**, not evidence of pixels displayed.
- `followup_failure_recorded` — the second attempt still records
  at least one error; its stage can differ from the first.
- `followup_log_incomplete` — the later log lacks a complete exit.
  It cannot support a clean-recovery interpretation.
- `no_first_attempt_failure_recorded` — no logged failure in the
  earlier record, so there is no known failure to recover from.
- `later_attempt_progressed_but_not_presenting` and
  `no_confirmed_cpu_progress` describe remaining CPU-only cases.

An early interruption can leave a partial last line: by design the
strict audit **fails closed** instead of inventing an orderly
shutdown or repair. The first failed stage and latest reached
stage are reported as generic labels such as `queue`,
`swapchain`, `shaders` or `presentation`; absolute paths,
private bytes, console identifiers and user-entered free text are
not included in its JSON output.

Every report retains these explicit evidence limits:

    "hardware_gpu_presentation_verified": false
    "original_foj_assets_verified": false
    "switch_gameplay_verified": false

### C/Python conformance regression

The stage-169 Python regression compiles the **actual native
`gpu/gpu_boot_journal.c` writer** with a tiny generated-only C
fixture. It records a synthetic queue failure, then a second
synthetic CPU startup progressing through stage 10 and five
present-call checkpoints. The Python reader validates the exact C
output and compares it against deliberately malformed stage and
outcome sequences.

No private SD files, PS3 resource bytes, DKSH data, screenshots or
real Switch observations are present in these CI tests. A passing
unit test verifies the two software components' compatibility,
**not** console recovery.

For physical testing, first follow
[the stage-168 early boot instructions](GPU_STAGE168_EARLY_BOOT_JOURNAL.md),
then the [stage-166 on-console observation sheet](GPU_STAGE166_HARDWARE_OBSERVATIONS.md).
The actual colors, on-screen checkerboards, device environment and
exit behavior must be witnessed and recorded separately. Do not
publish private logs or original game data to GitHub.
