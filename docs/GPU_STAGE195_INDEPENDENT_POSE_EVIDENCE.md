# Stage 195 — independent dual-clip skinning oracle and private pose envelope

This stage adds numerical evidence to the completed Stage 194 research
viewer. A topology match does **not** establish source-game actor identity,
and the inverse-bind convention remains an unverified research hypothesis.

## 15 controlled native C states

`tools/foj_stage195_dual_pose_probe.c` runs actual production C:
`rigged_actor_session → anim_player → skeletal_skin`. It uses invented
three-bone, **two-root** geometry; root/child rotations span X/Y/Z;
quaternion sign, negative first-key time, unequal keyframe timestamps,
influences from two bones, and an unweighted vertex are exercised.

The probe traces bind identity, paused start, continuous play, pause,
resume, crossfade from clip A to B at 0/25/50/75/100%, paused midpoint,
B end saturation, instant return to A and reset. All 3x4 bone matrices
and six 3D weighted vertex positions are printed for synthetic tests.

`tests/test_foj_stage195_independent_dual_pose_oracle.py` computes expected
local-pose interpolation and quaternion hierarchy in Python, independently
of C's row-major matrix implementation. It compares **15 states ×
(36 matrix floats + 18 vertex floats) = 810 scalar values** to tolerance
0.001, and checks exact pause, zero-weight fade, bind identity,
unweighted vertices, end saturation, transition motion, and malformed
native trace rejection. The native C probe includes internal guards
on invalid transition requests.

No C test output contains authentic PS3 motion or geometry.

## Opt-in, entirely PRIVATE real-data diagnostic

To investigate a user-owned compatible FOJRM001 rig and one or two
BANIM files, run on the owner's machine:

```sh
python3 -m tools.foj_stage195_private_pose_envelope \
  local-data/rig/preview.fojrm \
  local-data/anims/preview.banim \
  --secondary local-data/anims/preview_b.banim \
  > local-data/private-pose-envelope.json
```

A single clip is accepted when `--secondary` is omitted. The tool
rejects malformed data, duplicates, hierarchy mismatches and files
outside existing size ceilings. It reuses Stage 194 full-file
compatibility checks, and then samples each clip at start, midpoint
and end (at most six poses) in private memory.

It uses **a separate Python quaternion geometry implementation**, not
the C inverse-bind matrix code, to compare each research-deformed
vertex with the source vertex. The output contains only integer
counts, three displacement RMS/max aggregates per clip (rounded to
five decimal places) in unknown source coordinates, research bind
identity displacement, and explicitly false authenticity flags.
It never emits raw vertices, matrices, quaternions, original keyframes,
bone parent arrays, paths, source filenames or file hashes. Error
messages suppress private paths. Even though aggregate-only, **keep
the report private**: it can reveal properties of the owner's assets.

Nine generated-only tests validate the local inspector, including
two-root bind identity, nontrivial parent rotation, valid/invalid
dual-clip intake, malformed bytes, nonfinite values and CLI privacy.

## What this establishes — and what it does not

- It **can** verify consistency of the **chosen** research skin
  mathematics between C and independent Python, including pause/fade
  boundaries.
- On private assets, it **can** quantify how far the experimental
  output moves from the original mesh under that chosen convention.
- It **cannot** prove original PS3 joint spaces, coordinate handedness,
  bind-pose correction, genuine actor/animation association, retargeting
  rules, character fidelity, or an original-game frame comparison.
- The CI cannot run original copyrighted input, which is not included
  in the repository. The private CLI is *not* executed on the actual
  user-owned package by GitHub Actions.

Further progress requires private observations of original PS3 behavior
at reproducible timestamps to distinguish possible matrix conventions.
The synthetic NRO's existing NeXium regression continues to protect
known guest behavior; it does not validate authentic character animation.
