# Stage 203 — owner-private actor verification bundle

**No user-owned PS3 data or original-game frames are included or
processed by public GitHub Actions.** This stage creates a **single local,
non-uploading, offline** workflow joining previously independent
research tools into reproducible private evidence for an actual model
and one/two locally exported animation clips.

## What this actually establishes

The executable `tools/foj_stage203_private_actor_evidence.py`:

1. Reads bounded `FOJRM001` plus one or two `BANIM` byte streams,
   rejecting incompatible skeleton topology, duplicate second clips,
   corrupt inputs and nonfinite source transformations.
2. Uses the independent Stage195 quaternion-geometry implementation
   to calculate source-space pose displacement envelopes and test
   *research* bind-pose identity. **This is not verification of the PS3
   engine's animation mathematics or clip-to-character association.**
3. Creates a completely NEW private directory with restrictive local
   file permissions; it refuses to overwrite any existing directory.
   If the destination lies inside the repository it **must** be under
   the `local-data/` folder, excluded by `.gitignore`.
4. Uses Stage200 to create the exact private
   `switch/foj/{rig,anims}` input tree and verifies the stored bytes
   have not changed between original bounded intake and staging.
5. Compiles the real Stage200 **production-C** rig/BANIM parser,
   dual-clip player, experimental CPU skinning and wireframe renderer;
   runs it locally and verifies all nine actual PPM frames.
6. Checks that native paused/start/reset/zero-weight fade frames are
   exactly reproducible, that all nine images have a bounded valid PPM
   layout and visible wire geometry. Motion can legitimately be zero
   for an idle source clip; the tool records this rather than claiming
   successful animation movement.
7. Optionally evaluates actual, **operator-annotated** original-PS3
   versus research frame landmark observations using the existing
   private Stage196 matcher. For 8+ frames with valid timing data it
   attempts Stage197–198 lag/robustness checks. It optionally evaluates
   Stage199's 2–4 private motion windows. Reports remain operator
   claims; no screenshot or timestamp is independently authenticated.

Both original-game asset identity and actual original PS3 animation
fidelity are **explicitly false** in every report.

## Run locally with the owner's actual resources

First produce your own private exports by the previously documented
tools (`tools.export_local_rigmesh`,
`tools.export_local_banim`) and verify they remain inside an ignored
local directory. For example, **on your own computer only**:

```sh
mkdir -p local-data
python3 -m tools.foj_stage203_private_actor_evidence \
  --rig local-data/rig/preview.fojrm \
  --primary local-data/anims/preview.banim \
  --secondary local-data/anims/preview_b.banim \
  --output-root local-data/stage203-private-evidence
```

Omit `--secondary` for a single-clip examination. Use **a new output
directory for each run**; an existing one is never deleted, replaced,
reused or silently mixed with new observations.

The output includes:
- `private-switch-sd/switch/foj/rig/preview.fojrm` and
  `private-switch-sd/switch/foj/anims/preview*.banim` (original-byte
  duplicates; **never distribute**);
- `private-frames/*.ppm`: nine local images of the model silhouette;
- `private-pose-envelope.json`: independent source-coordinate pose
  displacements, calculated privately;
- `private-render-evidence.json`: observed geometry motion and
  pause/reset consistency measured from local PPM pixels;
- `private-evidence-status.json`: deliberately limited truth-status
  report, never presenting mathematical agreement as original-game
  authenticity;
- `private-actor-host-smoke`: compiled local native diagnostic.

All directory permissions are restricted and JSON files are written
with owner-only permission. PPM frames might reveal game content.
The tool emits only count/status metadata to stdout; it **never**
uploads anything, talks to GitHub, sends telemetry, or prints original
game paths, screenshot hashes, animation arrays or displacement values.
**Even aggregate private JSON reports must not be publicly shared.**
The cleanup path removes a newly created *partial* bundle on failure.

## Optional private original-game comparison

If the owner has independently captured real FoJ PS3 frames and
annotated their landmarks privately with the Stage196 schema, they can
pass that file:

```sh
python3 -m tools.foj_stage203_private_actor_evidence \
  --rig local-data/rig/preview.fojrm \
  --primary local-data/anims/preview.banim \
  --secondary local-data/anims/preview_b.banim \
  --observations local-data/observations/pose-landmarks.json \
  --output-root local-data/stage203-with-observations
```

For separately annotated motions, add
`--multiwindow local-data/observations/motion-windows-private.json`
with the Stage199 operator-supplied schema.

**Important:** The observation analyzer does not automatically annotate
or correlate the private PPM images to the PS3 captures. The operator
must ensure the same actor, camera angle, movement, clip and temporal
frame correspondences. A mathematically low 2D residual is not proof
of original-game skeleton conventions, animation scheduling, source
identity, authenticated video or physical Switch playback.

If no PS3 observations are supplied, the status is
`original_ps3_comparison_status=not_performed`. Do not invent input
frames to satisfy a test.

## Synthetic CI evidence

`tests/test_foj_stage203_private_actor_evidence.py` uses only
completely generated rig and two BANIM fixture byte streams.
It runs the actual C executable, checks all nine produced frames,
runs independent Python pose-envelope verification, tests
single-clip compatibility, optional *synthetic* Stage196/199 annotations,
strict filesystem permissions and cleanup, rejection of mismatched
animations and symlink/output overwrite attacks, and lack of paths or
sensitive numerical measurements in stdout.

CI exercises this **invented-only** pipeline. It does **not** process
the user's proprietary package or verify visual correctness against
original PS3 video.

## Remaining practical blockers

The user's genuine files must be examined on an owner-controlled
machine. No original PS3 snapshots with authenticated time and actor
information were submitted to this CI. Physical Switch rendering and
original engine exact pose / hierarchy behavior remain unverified.
Next steps should prioritize **privately acquired, matched source-game
motion evidence** over adding more synthetic metrics.
