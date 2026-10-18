# Stage 210 — owner-private consistency across multiple motion sequences

Stages 196–209 can compare a single original-side and research-side
operator-annotated sequence. Stage199 also checks tentative time-offset
consensus between two to four declared different actions. However,
repeating **the same pose trajectory** with mirrored camera, different
file names, reverse landmark ordering or changed timestamps does not
establish an independent confirmation of animation fidelity.

Stage210 introduces a separate, private **multi-sequence 2D movement
consistency** audit.

## Operator-local input

Use the pre-existing Stage199 private manifest schema:
`foj.stage199.private_multiwindow_consensus.v1`. It must contain
between two and four distinct operator-annotated Stage196 observation
documents and the declaration

`motion_independence_declaration: "distinct_actions_operator_declared"`

for the program to even consider a tentative multisequence assessment.
A declaration is not proof that the recordings or characters actually
came from the original PS3 game.

```sh
python3 -m tools.foj_stage210_multisequence_motion \
  --analyze local-data/observations/motion-windows-private.json \
  > local-data/observations/private-multisequence-motion.json
```

The input is strictly bounded and read with Stage199's duplicate-key,
finite-number and file-type protections. It **never** uploads local
content, source images, coordinates, raw rig data or names.

## Diagnostic gates

The program first executes the Stage209 per-interval motion coherence
audit *independently for every operator-provided window*. It then:

1. Canonicalizes every window's research-side and source-side
   **normalized pairwise landmark-distance sequence**, sorting
   anatomical labels and intentionally discarding exact timestamps.
2. Hashes that canonical geometry **privately in memory** and rejects
   two windows with identical normalized trajectories from being
   counted as independent observations. It therefore detects a
   repeated movement whose input points have merely been reordered,
   reflected, translated, uniformly scaled or rotated.
3. Counts windows with observable articulated movement, source/research
   motion mismatches, sample-clock warnings and missing operator
   capture declarations.
4. Returns a conservative diagnosis. It can only return
   `tentative_operator_declared_multisequence_coherence_only` when
   all windows contain observable, coherent 2D motion, their
   normalized trajectories differ, and the operator has declared both
   capture recordings and distinct actions.

The report emits only **aggregate counts and diagnostic strings**,
never the private geometry fingerprints, image names, landmark IDs,
time series or source PNG SHA-256 values.

### Limitations

Two genuinely independent recordings of the same static or repeated
animation may have exactly the same normalized shape trajectory. They
are **conservatively not counted as separate evidence**. Conversely,
changed coordinates or operator timestamps can make a duplicated
capture appear numerically different. Therefore the program cannot
**authenticate actual independence** merely because fingerprints
differ.

This stage does not require original PS3 media in public CI; it is
only a strict *offline* analysis of annotations. For evidence with
real images, review each window's private Stage205 source-PNG binding,
Stage204 research-frame binding and Stage206 paired visual overlays
on the owner's computer. The Stage199 independent timing consensus
should be run separately if timing is of interest.

Neither matching 2D motion, multiple declared actions, nor matching
time offsets proves the correct PS3 character, original animation,
hidden skeletal transforms, engine frame clock, actual PS3 hardware
or physical Nintendo Switch playback. All such authenticity and
fidelity fields remain **false**.

## CI

`tests/test_foj_stage210_multisequence_motion.py` uses entirely
generated landmark sequences. Tests cover three distinct invented
actions, camera-mirrored duplicate replays, reorder/timestamp replay
tricks, missing independence declaration, missing capture claims,
one corrupted middle frame, one static sequence, wrong operator time
intervals, invalid schemas, chronology and ID defects, untouched
inputs and CLI privacy. No owner-supplied commercial assets or
real-game reports are used in GitHub Actions.
