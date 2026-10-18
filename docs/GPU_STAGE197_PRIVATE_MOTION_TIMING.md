# Stage 197 — private time-lag diagnosis from moving landmark shapes

Stage 196 introduced an offline, manually annotated 2D pose comparison.
Stage 197 adds a **separate** diagnostic for a possible **constant time
offset** between source-game motion and an experimental research NRO.
This does not identify the original FoJ PS3 animation scheduler or
prove that original rig/clip pairs have been reconstructed.

## New diagnostic

`tools/foj_stage197_private_motion_lag.py` accepts the **same private JSON
schema** as Stage 196, with at least 8 and at most 12 chronologically
ordered frame entries. It treats PS3 and experimental coordinates as
**two independently timestamped motion series**, so unlike Stage 196,
the paired timestamps need not already agree.

For every frame, it calculates pairwise landmark distances divided by
that frame's landmark radius. This removes in-plane camera translation,
uniform scale, rotation, and reflection. It **cannot** remove
perspective, depth changes, occlusion or inconsistent identification of
limbs. A pose that only moves as a rigid body contains no usable signal
for this method.

For each candidate offset in a symmetric grid (default -0.2..+0.2
seconds in 0.025-second increments), the comparator linearly
interpolates the experimental 2D **shape signature** to the original
frame time plus that offset. **Every offset must use the same interior
reference frames**; a candidate cannot win by discarding awkward end
frames. Alternate interior frames are reserved for holdout checking,
and offset candidates are selected only on the training frames.

A positive offset means `original_pose(t)` resembles
`experimental_pose(t + offset)`: experimental motion may occur later
relative to the annotated clocks. This is a *diagnostic sign
convention*, not original engine frame-delay proof.

The output distinguishes:

- `tentative_nonzero_shift`: candidate is away from the search
  boundary, residual is acceptable, uncertainty is small, and held-out
  frames improve relative to zero shift.
- `no_clear_shift`: best shift is within one search step of zero.
- `ambiguous`: search boundary, declared timing uncertainty, absent
  operator capture declaration, or a distinct competing shift makes
  the estimate unreliable.
- `unresolved_shape_disagreement`: even the best aligned shape
  differs too much under this experimental model.

These labels are **heuristics for further local investigation**, not
statistical confidence intervals, PS3 timing authentication, or proof
of real source animation identity.

## Private usage

Keep source footage, experimental emulator screenshots, annotated
landmarks, original PS3 game files and reports outside GitHub. For
example, annotate 12 actual authorized paired frames from
0.00..1.65 seconds, in 0.15-second steps, preserving consistent
landmark names and separately recording both playback times.

```sh
python3 -m tools.foj_stage197_private_motion_lag \
  --analyze local-data/observations/pose-landmarks.json \
  --max-shift 0.2 \
  --step 0.025 \
  > local-data/observations/motion-timing-private.json
```

The same blank template from Stage 196 is available through:

```sh
python3 -m tools.foj_stage196_private_pose_observations \
  --init local-data/observations/pose-landmarks.json
```

The blank template **will not pass** the Stage 197 minimum-motion or
frame-count requirements. None of the original PS3 captures have been
provided to GitHub Actions by this change.

The public report from a synthetic test contains a best candidate
offset, training/holdout RMS, sample counts, ambiguity reasons, and
explicitly false authenticity flags. Reports derived from real
observations **must remain private**, despite omitting source image
bytes, point coordinates, landmark labels and local file paths.

### Explicit limitations and safeguards

- Require 8–12 frames, 4–32 consistent named landmarks per frame,
  finite normalized 0..1 coordinates and strictly increasing time
  within each motion series.
- Reject static/near-static shape signatures, large capture gaps,
  insufficient common comparison interval, malformed JSON and
  unsupported lag grids.
- A reported `tentative_nonzero_shift` is never evidence that any
  corresponding PS3 and NRO frames have actually been authenticated.
- The method uses **linear interpolation of shape distances** between
  timestamped frames, not original transform interpolation.
- Slow/periodic motions and uncertain observation clocks can give
  nonunique minima. Inspect alternative scores and repeat with
  independent clips/motions before interpreting the lag.
- Human annotation errors, camera perspective, skeleton proportions,
  lighting and projection may all create false lag signals.
- The parser reuses the strict Stage 196 private JSON reader and never
  accesses the network or the actual source media.

`tests/test_foj_stage197_private_motion_lag.py` uses only synthetic
moving points. It covers positive/negative/zero shifts, mirrored
camera nuisance, ambiguous input, static motion, temporal ordering,
privacy, and bounded CLI behavior.

**Next evidence gate:** timestamped authorized original PS3 capture
and matched NRO capture for the same genuine character/clip, privately
annotated and compared. Until such evidence exists, this is an
analysis tool, not confirmation of accurate original FoJ animation.
