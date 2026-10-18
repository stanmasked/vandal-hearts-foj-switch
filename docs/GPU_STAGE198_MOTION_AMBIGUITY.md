# Stage 198 — repeated motion and annotation sensitivity

Stage 197 provided private lag estimation from source-game versus
experimental-viewer 2D landmarks. Stage 198 adds **independent
sensitivity checks** before treating a lag as worth investigating.

This is a diagnostic for operator-annotated observations, **not** a
source-footage authenticity check, original PS3 animation-timing
measurement, or recovered skeletal animation model.

## What was added

`tools/foj_stage198_motion_ambiguity.py` consumes the same private
Stage 196/197 observation JSON without uploading original screenshots
or assets.

It recomputes Stage 197's fixed-window, train/holdout lag profile and
checks three new ambiguity sources:

1. **Repeated/cyclic motion.** A second lag is considered
   competitively plausible if it is sufficiently separated in time
   and its training **and** holdout RMS are close to the best candidate.
   Two similarly good lag candidates are not silently resolved by a
   lowest-score tie.
2. **Suspicious annotated frame.** Check per-frame residual at the
   selected lag. Frames whose residual is a large outlier relative to
   median residual are counted. The tool does not declare whether the
   problem is misannotation, camera mismatch, or actual animation.
3. **Landmark leave-one-out stability.** Remove each annotated
   landmark identity in turn, recompute the lag search and check
   whether the selected time offset changes substantially. If there
   are only four points, skip this check and mark the comparison as
   **insufficiently redundant**, not successful.

The new system can **downgrade** `tentative_nonzero_shift` or
`no_clear_shift` to `ambiguous_motion_or_annotation`. It must
never upgrade an earlier rejected, unresolved, or ambiguous
Stage 197 result to a successful one.

## Local-only usage

```sh
python3 -m tools.foj_stage198_motion_ambiguity \
  --analyze local-data/observations/pose-landmarks.json \
  --max-shift 0.2 --step 0.025 \
  > local-data/observations/private-motion-ambiguity.json
```

Inputs still require Stage 197's bounded set of 8–12 frames, 4–32
consistent nondegenerate landmark names, strictly ordered local
timestamps, dynamic articulated motion and a common interior window.
The default scan considers offsets -0.2s to +0.2s by 0.025s.

The report contains only diagnostic score aggregates, counts, one
estimated offset and explicit false provenance and authenticity flags;
it contains no original screenshots, mesh vertices, keyframes, manual
landmark coordinates or landmark names.

**Do not publish the original input or even the aggregate report
derived from real user assets.** The tests use solely invented
landmarks and do not authenticate source PS3 or Switch recordings.

### Interpretation

- A **second plausible lag** can reflect repeated movement, coarse
  sampling or a false correspondence. It is not an alternate engine
  animation rule.
- A **suspect frame** can be a valid unusual pose. An outlier warning
  is a prompt for private manual inspection, not license to delete
  inconvenient source observations.
- A **landmark-sensitive lag** suggests an unstable hypothesis but
  cannot identify which particular anatomical point is wrong.
- The diagnostic is limited to similarity-invariant 2D shapes. It
  cannot infer absolute camera translation, depth, original PS3
  frame pacing or internal joint matrices.

## Reproduction and future evidence

```sh
python3 -m unittest discover -s tests -p \
  'test_foj_stage198_motion_ambiguity.py' -v
```

Public CI checks synthetic clean motion, negative/zero lag, mirrored
camera, repetitive pose cycles, one erroneous frame, reduced landmark
coverage, unreported capture status, duplicate/changed labels,
invalid grids and privacy-respecting CLI failures.

A future genuine PS3-versus-NRO comparison still requires private
authorized source-game captures synchronized to experimental
recordings, with independently reviewed frame and landmark
annotations. **No original game's animation precision is confirmed
by Stage 198.**
