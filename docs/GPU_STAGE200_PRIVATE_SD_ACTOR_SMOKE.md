# Stage 200 — practical private actor SD intake and native wireframe smoke

This stage closes a practical integration gap between the bounded original
BMODEL/BANIM conversion tools, the Stage 194 libnx original-data-capable
`foj-rigged-actor-research.nro`, and Stage 192 playback controller.

There are now **two distinct tools**:

1. `tools/foj_stage200_prepare_private_sd.py` constructs the *exact*
   local SD folder hierarchy expected by the Switch viewer, after
   checking FOJRM001 and one/two complete BANIM files.
2. `tools/foj_stage200_actor_host_smoke.c` loads the same local SD
   layout into **production C** FOJRM001/BANIM parser, actor session,
   animation player, CPU skin deformation and wireframe renderer. It
   saves nine **private** diagnostic PPM frames and prints a count-only
   JSON receipt.

Original PS3 package, commercial BMODEL, BANIM, DDS and actual private
frames are **not uploaded to public GitHub Actions**. CI supplies its
own entirely invented two-bone rig and animation fixtures.

## Owner-local preparation

First privately export user-owned original-game resources using the
existing `tools.export_local_rigmesh` and
`tools.export_local_banim` commands described in
[original actor instructions](ORIGINAL_RIGGED_ACTOR_SWITCH.md).
All source and output paths must remain private, e.g. within the
Git-ignored `local-data/` directory. Check a second clip's skeleton
against the **same** rig; matching hierarchy is only structural
eligibility, not authentic actor-clip association.

From the repository root, on the owner's computer:

```sh
mkdir -p local-data

python3 -m tools.foj_stage200_prepare_private_sd \
  local-data/rig/preview.fojrm \
  local-data/anims/preview.banim \
  --secondary local-data/anims/preview_b.banim \
  --output-root local-data/stage200-private-sd
```

The secondary animation may be omitted, preserving the existing
one-clip viewer. The packager refuses to overwrite an existing target
directory, rejects invalid or identical secondary clips and validates
parent topology before writing. Resulting files have restrictive local
permissions. The folder structure is:

```text
local-data/stage200-private-sd/
  switch/foj/rig/preview.fojrm
  switch/foj/anims/preview.banim
  switch/foj/anims/preview_b.banim   (optional)
```

This directory contains game-derived original asset bytes if supplied
from an owner-held PS3 dump. **Do not upload it as a CI artifact,
publish it, add it to Git, or distribute it as a ZIP.**

The directory's `switch/foj` contents can be copied to the
corresponding SD card location for the existing NRO, but that NRO's
actual runtime behavior on physical hardware and original-asset
NeXium mounting has **not** been verified by this stage.

## Native host smoke with real production core

Compile the research smoke tool on a local Linux machine with a C11
compiler (GCC/Clang), no commercial SDK necessary:

```sh
cc -std=c11 -O2 -Wall -Wextra -Werror -pedantic -Icore \
  tools/foj_stage200_actor_host_smoke.c \
  core/rigged_actor_session.c core/anim_player.c \
  core/rigmesh_io.c core/banim_core.c \
  core/skeletal_skin.c core/obj_wireframe.c \
  -lm -o local-data/stage200-actor-smoke

mkdir -p local-data/stage200-frames
local-data/stage200-actor-smoke \
  local-data/stage200-private-sd \
  local-data/stage200-frames
```

Nine **PPM image frames** are created using the real core's CPU
wireframe renderer at 480 × 320. Output names are:

`initial`, `play_025`, `paused`, `fade_0`,
`fade_025`, `fade_050`, `fade_075`, `fade_done`, `reset`.

The test advances nominal playback by 0.25 seconds, then pauses
and checks the same source pose; it resets, requests an experimental
0.5-second crossfade, samples four steps at 0.125-second intervals,
then resets. Without a secondary clip the same script runs only the
primary clip; the `fade` labels are bookkeeping positions, **not**
a claim of a real two-clip crossfade in that mode.

The smoke tool fails closed on missing/incompatible original resources
and refuses to overwrite PPM frames. It prints only counts and
explicitly false authenticity flags. The PPM images themselves
**contain transformed silhouettes and are private user content**.
They must never be included in public logs, PRs, attachments or
GitHub artifact uploads.

## Public validation

`tests/test_foj_stage200_private_actor_smoke.py` constructs invented
rig and BANIM bytes, writes them into an ephemeral test directory
with the genuine SD layout, compiles the actual portable C modules
and checks 9 raster frames. Expected properties include:

- initial frame equals reset and zero-alpha fade;
- after play, the skeleton visibly changes;
- paused frame equals the preceding playing frame;
- two fade steps differ, and the completed fade differs from start;
- all files remain inside an ephemeral local workspace;
- original sources remain unchanged and overwrite attempts are refused;
- missing/malformed secondary and missing primary fail closed without
  claiming successful playback;
- single-clip backward compatibility remains available.

The current GitHub NRO build continues compiling
`foj-rigged-actor-research.nro` with devkitA64; Stage 200 did not
alter the underlying libnx application or insert game assets.

## Critical evidence boundary

This *practical end-to-end test* proves that real production C
parsers, playback logic, skinning math and CPU wireframe can operate
together on disk data, using **synthetic public CI fixtures**.

It does **not** establish that the owner's actual PS3 model/BANIM
pairs have been run here, that the original PS3 bind-pose convention
is correct, that actual graphics are equivalent, or that the
research NRO has rendered original assets in NeXium or on hardware.
Real motion authenticity still requires independent authorized
source-game recordings and private matched frame analysis.

The next realistic goal is an owner-local capture comparison of
the generated frames against identical PS3 animation states, or
a safely isolated NeXium SD fixture test with generated-only assets.
