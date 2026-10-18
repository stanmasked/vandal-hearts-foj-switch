# Stage 201 — actual NeXium execution of the generated-SD actor NRO

## Objective

Stage 200 verified the owner-local data path on the portable host:
FOJRM001 model, one/two BANIMs, original C parser, experimental
animation player and CPU wireframe renderer. Stage 201 exercises **the
actual compiled `foj-rigged-actor-research.nro`** in NeXium with
generated-only FOJRM001 + BANIM files on its virtual SD card.

This test deliberately **does not use any real PS3 assets**, original
game screenshots, or user-private models. Its success cannot establish
fidelity to Vandal Hearts: Flames of Judgment.

## Verified NeXium virtual SD path

NeXium's source (`nexium-common/src/paths.rs`) defines
`NEXIUM_DATA_ROOT` as a data-root override and
`sdmc_dir() = data_root()/sdmc`. The filesystem host layer
(`nexium-kernel/src/fs_host.rs`) translates guest
`sdmc:/switch/foj/rig/preview.fojrm` to the corresponding host path.
The GUI default keyboard mapping defines **E as the Switch R button**,
Z as Y and X as B.

The CI creates a new, temporary data root and then these files:
```text
<NEXIUM_DATA_ROOT>/
  sdmc/
    switch/
      foj/
        rig/preview.fojrm
        anims/preview.banim
        anims/preview_b.banim
```

The generator `tools/foj_stage201_generated_sd.py` creates every byte
from independently invented, checked-in test fixture generators.
**It cannot accept any paths to user game data.** Stage 200's full
FOJRM001 + BANIM compatibility validator is reused. An existing
NeXium data root is never overwritten.

## NeXium workflow

`.github/workflows/stage201-nexium-sd-rigged-actor.yml`:

1. Builds **the original-data-capable actor NRO**, not the Stage193
   separately fabricated synthetic player NRO, in devkitA64 and
   checks the binary NRO structure.
2. Downloads the external NeXium nightly to the Ubuntu runner;
   captures its archive SHA-256 for reproducibility.
3. Runs six local generated-fixture setup unit tests and six synthetic
   screenshot verifier tests before launching the emulator.
4. Creates an isolated `NEXIUM_DATA_ROOT` under the ephemeral runner's
   temp directory. This is separate from the repo and **never** included
   in uploaded CI artifacts.
5. Starts the actor NRO with the guest-provided synthetic virtual SD,
   performs Switch R steps (E key), reset (X) and optional fade (Z/Y).
6. Captures **ten actual guest screenshots** to prove that source
   files are loaded by the guest filesystem, that animation changes
   its wireframe, pause keeps the mesh still, fade changes between
   clip A and B, and reset returns to frame zero.
7. Checks the screenshots with a fail-closed verifier, then uploads
   only the generated guest screenshots and sanitized count-only JSON
   receipt (never the virtual SD input files).

Screenshot marker colors on the real actor NRO indicate:
amber for owner-data-capable, experimental math; blue if optional second
clip was accepted; yellow if a crossfade is currently active. They
**do not** mark original PS3 animation behavior as confirmed.

The image checker `tools/foj_stage201_nexium_sd_actor_frame_check.py`
will fail if one guest frame is missing, model wireframe is absent,
files are not accepted, the pose fails to move, pausing drifts,
initial/reset poses do not match, or the crossfade does not animate.
Its six independent tests use artificial local PNG fixtures;
they are not NeXium guest evidence by themselves.

## Evidence boundaries

The following must be stated separately:

- **Native host test:** Stage 200 has already executed production
  portable C on invented files.
- **Emulator guest test:** only a successful Stage201 NeXium workflow
  confirms that the generated-SD actor NRO was executed and the
  compiled guest code actually loaded the generated files.
- **Original game test:** not performed. Real BMODEL/BANIM association,
  source-game joint rules, original screenshots and accurate movement
  remain unverified.
- **Physical Nintendo Switch:** not tested.

A successful build **alone** is not guest evidence. The NeXium
workflow must produce and validate actual guest PNG frames before
claiming guest playback.

Owner-private data can instead be staged using Stage 200's private
SD preparer and examined locally. **Never upload original exports,
user-authored PPM/PNG evidence or game-derived model/animation data to
GitHub Actions.**

Next: if Stage 201 passes, run the same research controller through
more robust generated edge cases on NeXium, and separately compare
authorized private original-game footage against experimental frames.
