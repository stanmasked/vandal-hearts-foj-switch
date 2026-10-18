# Stage 178 — read-only six-file SD copy preflight

**Status: research-only; no physical Nintendo Switch execution or
GPU scanout is proven by this tool.** No original PS3 game resources
are copied or required.

Stage 171 could compare an explicitly supplied local copy of the
triangle NRO. Stage 178 independently checks the **entire six-file**
generated runtime tree expected from the stage-165 SD ZIP. This is
intended for a local SD card or an extracted synthetic test tree.

## Run offline on your own mounted SD copy

Obtain the matching *generated-only* ZIP and stage-171 receipt from
the **same** CI run, and determine their commit and run ID from the
actual GitHub Actions run. Then on a development computer:

    python3 -m tools.foj_stage178_sd_copy_preflight \
      --sd-root /path/to/mounted/SD \
      --bundle /path/to/foj-stage165-gpu-sd-smoke.zip \
      --receipt /path/to/foj-stage171-ci-build-receipt.json \
      --expected-commit <40-character-Git-SHA> \
      --expected-run-id <GitHub-Actions-run-ID>

Replace placeholders with real paths/identifiers. The command does
**not** write to the SD card, run any Nintendo Switch program, read
private game resources or upload diagnostics. It reports only fixed
relative project paths and SHA-256 values.

The expected SD layout is:

    switch/foj/foj-deko3d-clear-smoke.nro
    switch/foj/foj-deko3d-triangle-research.nro
    switch/foj/gpu/foj_actor.vert.dksh
    switch/foj/gpu/foj_triangle.frag.dksh
    switch/foj/gpu/material0.dds
    switch/foj/gpu/material1.dds

An exact, unchanged six-file tree inside `switch/foj` is required.
Files outside this dedicated directory are deliberately ignored so
the tool can be used on an SD card containing unrelated homebrew.
The fifth SDK shader, `foj_actor.frag.dksh`, was published as a
separate research artifact but is **not** needed by the stage-165 SD
bundle and must not be copied into this fixed six-file baseline.

The command validates the full original synthetic ZIP and stage-171
receipt, independently reads each SD copy twice through held,
nofollow file/directory descriptors, checks NRO/DKSH structure and
the precise SHA-256 of each of the four binaries and two generated DDS
textures, and compares the project directory listing and metadata
before and after the read.

## Important: intentional DDS test variants

This preflight describes the **unaltered baseline** (manual cases C
and E). Cases A, B and D deliberately remove or corrupt synthetic
DDS files for hardware diagnosis, so they are expected to fail this
six-file baseline check. Restore the generated DDS files and rerun
before interpreting a mismatch as unintended copying corruption.
Never modify any original PS3 assets.

## Synthetic regressions

    python3 -m unittest discover -s tests \
      -p 'test_foj_stage178_sd_copy_preflight.py' -v

These tests generate a small, independent NRO/DKSH fixture and DDS
bundle without accessing a console. They cover correct copies,
missing/extra files, altered binaries or DDS, symlink substitutions,
commit/run mismatches and read-only CLI behavior.

A matching SD folder only supports local **byte-equivalence at
check time**. It cannot prove Homebrew Menu loaded that copy,
that an SDK-built NRO is playable, or that real Switch display
hardware rendered a visible frame. Operator observations must be
recorded separately under stage 166/170.
