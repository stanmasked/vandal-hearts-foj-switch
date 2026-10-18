# Stage 192 — controlled synthetic BANIM playback

The native animation research pipeline now has a small portable C
playback controller, `core/anim_player.c/.h`. It is not a recovered
PS3 game actor scheduler or proof of game-specific animation blending.

## Research playback operations

- **Pause/resume** maintains the same local pose while paused. A paused
  transition retains its fade progress and both source/target times.
- **Time advance** uses a finite, nonnegative delta of at most 60 s.
  Each clip saturates at its end time. This is a documented research
  choice, not proven original loop or wrap behavior.
- **Clip replacement** with zero fade starts the replacement clip at
  time zero. Invalid skeleton topology/parent indices or time values
  are rejected without mutating playback state.
- **Controlled crossfade** begins at alpha 0 and advances to alpha 1,
  with shortest-arc quaternion slerp for local rotations and linear
  XYZ blending. It advances source and target clocks independently.
  A second clip request while fading is rejected; completion promotes
  the target and releases the transition state.
- **Skin palette** is produced using the existing validated production
  C hierarchical matrix and inverse-bind implementation.

The API assumes the caller owns and preserves both animation clips
while referenced. It is not thread-safe, has no original-game layer
mask, curve, root-motion application or blend tree.

## Independent cross-language test

`tools/foj_stage192_player_probe.c` runs real production C code with
two **invented two-bone BANIM clips** and a weighted skinned vertex.
The test traces 13 states: play, pause, resume, fade at 0/25/50/75/100%,
a pause within a fade, continued playback of clip B, end clamping and
instant restart of clip A.

`tests/test_foj_stage192_player_contract.py` independently samples
each clip using Python shortest-arc quaternion interpolation, blends
local poses, and uses the geometrically independent Stage 190 skeleton
oracle to calculate expected matrix/vertex results. It compares all
12 components of both C skinning matrices and every skinned XYZ to
within **0.0007**.

Eight regression tests also ensure paused frames are numerically
unchanged, the beginning of the fade has no instantaneous jump,
intermediate crossfade frames are not static, invalid arguments leave
the state unchanged, switching at zero fade starts the next clip at
time zero, and corrupted native output is rejected.

Run without any original PS3 data:

    python3 -m unittest tests.test_foj_stage192_player_contract -v

The GitHub Research tools workflow compiles the real native C code
and runs these generated-only tests under Python 3.11 and 3.13.

## Important limitations

Successful checks establish consistency of the **experimental**
animator. The correct original PS3 playback rules, true actor/clip
association, bind-pose convention, animation layers, timing and
movement remain unverified. No original PS3 assets are committed,
and this is not proof of a playable Switch port or physical console
execution. Integration into a visual Switch/NRO prototype is a
separate validation step.
