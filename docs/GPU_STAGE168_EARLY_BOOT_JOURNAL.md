# Stage 168 — early GPU initialization breadcrumbs on private SD

**Not a hardware validation.** This is a best-effort, local-only
CPU checkpoint log for the experimental shader-backed research NRO.
No original Vandal Hearts: Flames of Judgment PS3 content is involved.

## Why this exists

Stage 167's persistent GPU colors require a valid device, queue,
framebuffer images, swapchain, and command buffer. A failure creating
any of these occurs **before the GPU could display an error color**.
Stage 168 optionally writes **fixed numeric startup events** to SD,
so a person with an authorized homebrew Nintendo Switch can distinguish
how far the NRO's CPU initialization progressed.

The triangle-research NRO attempts to mount the SD card *before*
`dkDeviceCreate`, then exclusively creates the first free file among:

    sdmc:/switch/foj/gpu/foj-boot-00.txt
    ...
    sdmc:/switch/foj/gpu/foj-boot-15.txt

Previously created files, including symlinks with those filenames,
are never followed, erased or overwritten. The file includes only
lines with the literal form:

    FOJBOOT1 slot=00 step=01 event=1 frames=0000000000

There are no arbitrary strings, paths, names, hardware IDs, timestamps,
game data, texture bytes, shader bytes or hashes. Up to 64 entries are
allowed per run. Records are appended and flushed after each stage.
A partial/truncated final record is rejected by the offline auditor.
Flush does **not** guarantee power-loss durability on every SD card.

If the mount fails, files cannot be created, or the 16 slots are
occupied, logging quietly disables. **The GPU program continues as
before.** This is intentional: diagnostics must not cause a boot
failure or alter a render result. No space reclamation is automatic;
inspect/archive/remove obsolete logs *manually* before later runs.

## Numerical stage and event legend

| Step | CPU-side operation |
| --- | --- |
| 01 | GPU device creation |
| 02 | Graphics queue creation |
| 03 | Framebuffer images |
| 04 | Swapchain creation |
| 05 | GPU command buffer |
| 06 | Synthetic vertex staging |
| 07 | DKSH shader loading and validation |
| 08 | Synthetic DDS texture staging |
| 09 | GPU command-list recording |
| 10 | GPU present loop |
| 11 | Program exit marker |

Events: `1` = entered, `2` = CPU-side ready,
`3` = failed/aborted, `4` = exited. A log ending with
an `entered` entry but lacking an exit can indicate an
interrupted or abruptly terminated run; it does not prove why.
The `frames` field counts completed CPU calls through the
research presentation path, **not actual visible hardware frames**.

## Safe manual recovery test

1. Back up your own files and install the latest synthetic-only
   [research SD bundle](GPU_STAGE165_SD_RELEASE.md). The directory
   `switch/foj/gpu/` must exist on your SD card.
2. Launch the clear-only NRO normally. It remains unchanged and does
   **not** create a stage-168 triangle boot journal.
3. Launch the triangle-research NRO. Even if the screen stays black,
   examine `foj-boot-00.txt` after returning safely to Homebrew Menu.
4. On a *temporary copy of generated assets*, rename only the
   vertex DKSH as described in
   [stage 167](GPU_STAGE167_DKSH_BOOT_SCREENS.md), relaunch, and check
   whether the next new file (`01`, etc.) reaches stage `07`.
5. Restore the DKSH, relaunch again, and check that the old files remain
   unchanged and a later slot is created. Observe the actual colors
   separately; do not infer successful GPU display from log entries.

For a copied local file (never use this tool to scan private SD directories):

    python3 -m tools.foj_stage168_boot_journal_audit \
      --file ./foj-boot-00.txt

The analyzer validates a strict file name, bound, line format, event
ordering, slot identity, and monotonic CPU presentation-call counter.
It reports only the last CPU stage, whether an exit marker exists and
the number of declared CPU present calls. It omits local paths and
never sets any GPU or hardware-verification flag true. Compare the
result with actual on-screen observations from the private
[stage-166 worksheet](GPU_STAGE166_HARDWARE_OBSERVATIONS.md).

The existing stage-167 color screens still handle DKSH failures
when swapchain rendering is available. Device, queue, framebuffer,
or swapchain creation errors may still have **no visible GPU screen**.
This journal cannot establish GPU correctness, original PS3 resource
compatibility, gameplay, or a playable Switch port. Keep actual
boot logs on your own SD/computer and out of the public GitHub repo.
