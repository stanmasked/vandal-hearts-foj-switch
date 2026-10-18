# Stage 207 — private multi-frame 2D orientation, apparent scale and time audit

The Stage 206 output gives the owner a visual correspondence review of
original-side PNG and research-side C wireframe PPM frames, with consistent
numbered anatomical landmarks. Stage 207 adds a **multi-frame
image-plane diagnostic** to help prioritize suspicious camera, pose,
orientation and time correspondence issues before claiming PS3 fidelity.

This analysis does **not** recover the original game camera, engine
matrix convention, character/clip association or animation schedule.
**No genuine original PS3 captures have been tested in public CI.**

## Offline implementation

`tools/foj_stage207_private_view_timing.py` accepts a private Stage196
observation file with 3–12 ordered, consistently labelled,
noncollinear frame pairs. Every frame is fitted under two different
experimental-to-source **2D similarity models**:

- In-plane translation, uniform scale and rotation.
- The same 2D transform with optional left/right reflection.

Fits use Stage196's exact mathematical convention; they do not switch
correspondences or read any source images automatically. The output
includes only aggregate metrics:

- Which **2D** reflected/unreflected model has the lower median
  normalized RMS; a small gap is reported as ambiguous.
- Largest per-frame variation of the fitted in-plane angle, accounting
  for the 179°/−179° circular wraparound.
- Ratio of maximum to minimum fitted **relative apparent size**.
- Median/worst shape residuals and number of frames with strong
  disagreement over reflection preference.
- When at least 8 valid moving frames are provided, Stage197's
  *tentative* constant-lag finding. Static or unsupported movement
  yields an explicit `not_resolvable_from_motion` rather than
  invented timing evidence.

For illustration, a relative image-plane rotation greater than 15°
or apparent-size variation over 30% across the selected frames
raises `possible_view_or_pose_inconsistency`. These are
**conservative operator-review heuristics, not camera accuracy
tolerances or verified source-engine constraints**.

The source/research timestamp checks of Stage196 remain in force.
Where the source and experimental capture clocks are not declared,
the status is `operator_capture_not_declared`.

A stable result is strictly named `image_plane_similarity_stable_only`.
It can never mean that the original PS3 camera was reproduced or
that real animation timing/pose math is accurate.

## Standalone operator-local usage

```sh
python3 -m tools.foj_stage207_private_view_timing \
  --observations local-data/observations/pose-landmarks.json \
  > local-data/observations/private-view-temporal-report.json
```

This reads only bounded private JSON; it does not touch game files,
contact any external service or upload captured images or
coordinates. Keep **even aggregate output** inside an
owner-controlled private directory.

## Integration into the Stage203 bundle

Stage203 also supports `--view-temporal-audit`, which requires both
independently validated sides of the owner-private comparison:

- Stage205 source PNG content manifest and original-side observations.
- Stage204 research wireframe-to-landmark binding and native C frames.

The new flag is **not** allowed with unbound synthetic coordinate
lists alone. For private original-game assets:

```sh
python3 -m tools.foj_stage203_private_actor_evidence \
  --rig local-data/rig/preview.fojrm \
  --primary local-data/anims/preview.banim \
  --secondary local-data/anims/preview_b.banim \
  --observations local-data/observations/pose-landmarks.json \
  --source-png-dir local-data/observations/ps3-frames \
  --source-png-manifest local-data/observations/source-png-private.json \
  --frame-bindings local-data/observations/native-frame-binding.json \
  --view-temporal-audit \
  --output-root local-data/stage207-private-evidence
```

The new file `private-view-temporal-audit.json` is
**owner-private**. The umbrella Stage203 status records that the
audit ran, together with its diagnostic label, but all actual
original-game provenance, pose correctness and animation accuracy
flags remain false.

For visual confirmation of the **identities** of numbered landmarks,
the same private invocation can also include `--review-overlays`
(Stage206). An apparent 2D shape match can still be anatomically
wrong; inspect originals and research images yourself.

## What the diagnostic cannot distinguish

2D rotation changes might be caused by an actor turning, camera roll,
image coordinate calibration or a real 3D orientation change.
Apparent size changes might come from perspective, camera distance,
the actor movement or incorrect landmark assignment. 2D reflection
is not proof of original skeleton handedness. Hidden bones cannot
be recovered from a small set of annotated screen points.

When a timing shift is found on 8–12 annotated frames, the fit
remains **tentative and operator-provided**, not evidence for PS3
frame pacing. Repeating movements can mimic a delay; Stage198–199
provide additional optional ambiguity checks, not authentication.

No tool autonomously verifies that source captures actually depict
the original PS3 game, the correct character or the intended
original animation. A definitive fidelity claim still needs
authorized matched source gameplay with independent human review.

## Public CI tests

`tests/test_foj_stage207_private_view_timing.py` uses generated 2D
motion only. It covers stable similarity, reflected fit preference,
wrapped 179° angles, large in-plane rotation, apparent size drift,
wrong landmarks, missing capture declarations, no invented lag on
static/short sequences, tentative lag on moving sequences, malformed
IDs/clocks, no mutation of private input, protected CLI errors, and
strict Stage203 provenance requirements.

No original game materials, original captured PNGs, NRO assets or
private per-actor metrics are introduced into public GitHub Actions.
