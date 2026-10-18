# Stage 209 — privately compare articulated motion *between* frames

Stages 196–208 analyze operator-labelled poses, private PNG/PPM
source identity, image-plane alignment, lag hypotheses and crossvalidated
affine camera nuisances. None of these proves that the **sequence of
pose changes** in the original PS3 game matches the research viewer.

Stage209 adds an owner-local **interframe articulated-shape
coherence diagnostic**. Only invented data are used by public CI;
the owner's original game images and model exports are never
published.

## Method

`tools/foj_stage209_private_motion_coherence.py` requires the
strict Stage196 schema: 3–12 chronological frame pairs, consistent
4–32 operator-labelled, noncollinear landmarks, and declared capture
time uncertainty. For each source and research frame:

1. Convert the points to normalized **pairwise landmark distances**;
   this is invariant to 2D camera translation, uniform scale,
   in-plane rotation and reflection.
2. Compute the signed *change in each pairwise distance* between
   consecutive frames, separately for PS3-side annotations and
   experimental research-side annotations.
3. Compare transition activity, RMS difference between the two
   change vectors and, where measurable, their directional similarity.
4. Check consistency of adjacent source/research sampling intervals
   using the **operator-provided** timestamps. Ratios above 1.25
   become an explicit sampling-timebase warning.
5. If two neighboring transitions disagree, report a possible
   error in the shared middle frame. This is a **review hint**,
   not an automatic declaration that the manual landmark label
   was incorrect.

The report distinguishes:
- `shape_transition_consistent_only`: at least two informative
  intervals with low 2D shape-change disagreement.
- `unresolved_insufficient_articulated_motion`: static or sparsely
  moving sequence, even when the images appear to match.
- `unresolved_local_motion_or_annotation_mismatch`: inconsistent
  relative changes, reversed motion or one stream moving while
  the other is static.
- `unresolved_interval_timebase_disagreement`: declared source
  and experimental frame sampling differ substantially.
- `operator_capture_not_declared`: one or both streams have not
  even been marked recorded by the operator.

Conservative heuristic thresholds are used only to prioritize human
inspection; they **are not PS3 accuracy requirements**. Actual
motion, camera perspective, joint occlusion, sampling intervals
and mislabeled limbs can produce the same apparent disagreement.

The report includes only aggregate counts and RMS statistics, never
individual source points, bone names, image bytes, original game
filenames, proprietary data hashes or original actor identifiers.

## Owner-local standalone use

```sh
python3 -m tools.foj_stage209_private_motion_coherence \
  --observations local-data/observations/pose-landmarks.json \
  > local-data/observations/private-interframe-report.json
```

The source and research landmarks must refer to equivalent visible
anatomical points on the same character and matching animation.
This program **does not automatically validate image provenance**.
For defensible private diagnostics, Stage203 integration is preferred.

## Full private native actor/PS3 evidence bundle

Use `--interframe-coherence` with Stage203 and the two mandatory
image evidence bindings:

```sh
python3 -m tools.foj_stage203_private_actor_evidence \
  --rig local-data/rig/preview.fojrm \
  --primary local-data/anims/preview.banim \
  --secondary local-data/anims/preview_b.banim \
  --observations local-data/observations/pose-landmarks.json \
  --source-png-dir local-data/observations/ps3-frames \
  --source-png-manifest local-data/observations/source-png-private.json \
  --frame-bindings local-data/observations/native-frame-binding.json \
  --interframe-coherence \
  --output-root local-data/stage209-private-evidence
```

This generates native 480 × 320 C-wireframe research screenshots
locally, requires Stage205's exact owner-private PNG manifest,
requires Stage204's landmarks actually touch the named C-rendered
research PPM lines, and stores
`private-interframe-coherence.json` as a mode-0600 **private**
diagnostic. Missing prerequisite evidence rejects the run before
creating an output directory.

To visually review a possible middle-frame annotation mismatch,
add Stage206's `--review-overlays` to an owner-local run. Recheck
which **named joint** each mark represents on original images and
research frames. No algorithm can make that determination for the
user from image-plane distances alone.

## Essential limitations

Shape-distance changes ignore translation, rotation, reflection and
uniform scaling, but cannot remove perspective projection or
occlusions. A match in change sequence does not authenticate a PS3
recording, original actor, animation clip, actual clock, bone matrices
or original gameplay. Repeated motion can match in a wrong phase;
a temporal lag needs separate Stage197–199 ambiguity checks.
An unmoving character can produce perfect zero-change agreement
while revealing **no useful animation evidence**.

Even success must be described only as a tentative **2D
annotation-based interframe consistency** result. No PS3 source
footage, owner model or protected screenshot has been examined by
public CI.

## Synthetic-only testing

`tests/test_foj_stage209_private_motion_coherence.py` covers
camera-similarity nuisance, coherent nontrivial movement, a single
mislabelled middle frame, asymmetric motion, static sequences,
uncertain local clocks, declared/unreported sources, timing offsets,
repeated cycles, malformed IDs and timestamps, private CLI
output and integration into Stage203 with **generated FOJRM001,
two generated BANIMs, a real native C renderer** and invented
local source PNGs. Tests never publish original PS3 materials.
