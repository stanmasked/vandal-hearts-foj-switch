# Stage 194 — private model + two compatible animation clips on Switch

This stage extends the **existing** original-data-capable
`foj-rigged-actor-research.nro` instead of replacing the Stage 193
generated-only animated demo. A new borrow-only portable
`core/rigged_actor_session.c/.h` validates both clip hierarchies and
exposes the Stage 192 playback controller to CPU skinning.

## Required private SD content

Primary model and animation remain:

```text
/switch/foj/rig/preview.fojrm
/switch/foj/anims/preview.banim
```

Optionally supply a second, **distinct**, structurally compatible clip:

```text
/switch/foj/anims/preview_b.banim
```

All bytes originate from user-owned PS3 assets exported privately with
existing `tools.export_local_rigmesh` and `tools.export_local_banim`.
Do **not** commit or upload FOJRM001, BANIM, original BMODEL, PSARC,
PKG, licenses, executable content or texture exports.

Before copying to SD, run locally (no network operations):

```sh
python3 -m tools.check_local_rig_clip_set \
  local-data/rig/preview.fojrm \
  local-data/anims/preview.banim \
  --secondary local-data/anims/preview_b.banim
```

This bounded preflight checks each complete FOJRM001/BANIM structure
and exact parent arrays by independently parsing the two pairs. Its
JSON prints **only structural counts and explicitly false evidence
flags**; it suppresses filenames, original transforms, keyframes,
content hashes and exact local paths. It never writes back to the
original files. It rejects duplicate animations and incompatible
hierarchies. The optional `--secondary` may be omitted to inspect
the existing single-clip workflow.

Matching topology only demonstrates the **possibility** of using the
two clips with the same research skeleton. It does not establish the
correct original PS3 actor association, exact bind-pose matrices,
retargeting, synchronization, animation state transitions or semantics.

## Native viewer

| Switch button | Action |
| --- | --- |
| A | Toggle pause/resume |
| B | Reset to primary at time zero, paused |
| Y | Request a 0.5-second local-pose crossfade to the other clip |
| X | Switch immediately to the other clip |
| R (while paused) | Advance playback / fade 0.125 second |
| D-pad left/right/up/down | Rotate camera and adjust elevation |
| ZL / ZR | Zoom |
| Plus | Exit |

NRO reads the second file only from local SD; an incompatible supplied
secondary clip is rejected and never used. The legacy primary clip
continues working without any secondary file. A red diagnostic marker
indicates a provided but unusable alternate, blue marks accepted
alternate, amber marks an experimental original-data rig and yellow
indicates an active fade. None of these indicators means the original
PS3 blend rules or graphics have been reproduced.

The render path now flows through production code:

`foj_actor_init → foj_player_advance/switch → foj_player_palette → foj_skin_deform → foj_obj_wireframe`

Play time uses the same **nominal** 1/60 second per rendered iteration
as Stage 193, which is not synchronized to verified game or Switch
wall-clock timing. At the clip end the research controller saturates;
no loops are inferred. No proprietary assets are embedded in NRO.

## Synthetic evidence and scope limits

The research Python CI discovers
`tests/test_foj_stage194_private_clip_set.py`, including compilation
and execution of `tests/test_foj_stage194_actor_session.c` against
**the actual production portable C modules**. It checks compatible
clips, exact hierarchy rejection, unchanged session state after
invalid intake, paused geometry, exact no-jump fade start, changing
skinned vertices during fade, transition finalization, instant switch,
malformed weights fail-closed and single-clip backwards compatibility.
Python checks local preflight failure and privacy contract.

The Switch CI compiles and validates the updated
`foj-rigged-actor-research.nro`. Existing NeXium workflows run only
generated-only NROs; they **do not** emulate a local original-data
session for this stage. A successful native build is not evidence of
rendering an actual PS3 model in NeXium, on physical Switch or matching
the original game.

**Next evidence gate:** perform private local verification with two
independently sourced user-owned compatible clips; compare captured
poses to authorized source-game footage or instrumented recordings.
Keep all source assets private and never infer authenticity from
hierarchy match alone.
