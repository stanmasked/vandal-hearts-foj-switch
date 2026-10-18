# Stage 191 — native BANIM sampling and skinning across animation time

Stage 190 checked the mathematical correctness of one set of **synthetic**
bone matrices and vertex weights using independent C/Python implementations.
Stage 191 tests the **full experimental sampling pipeline over time**:
native C BANIM local-track interpolation, hierarchical world transforms,
inverse-bind palettes and CPU-skinned vertex positions.

## End-to-end production C tested

The host probe `tools/foj_stage191_multiframe_skin_probe.c`
constructs only invented clips, then invokes **production functions**:

1. `foj_skin_sample_palette()`, which calls `foj_banim_sample()`.
2. `foj_skin_build_palette()`, including parent inheritance and inverse bind.
3. `foj_skin_deform()`, including the source vertex weights.

Eight times are checked: **−0.5, 0, 0.125, 0.25, 0.5, 0.75, 1 and 1.5
seconds**. The synthetic clip has three tracks in two independent
hierarchy roots. The child has different first and last key times from
its parent. The final track uses opposite-sign but physically
equivalent quaternions.

The independent Python test does **not** reproduce the C matrix
formula. It samples the same invented tracks using a Python
shortest-arc quaternion slerp/linear XYZ interpolation, then invokes
the previously independent Stage 190 quaternion world-composition
oracle. Every 3×4 matrix component and every deformed XYZ must match
the real C output to an absolute tolerance of **0.0005**.

## Test coverage

Seven test groups check:

- Exact C/Python matrix and vertex agreement at **all eight times**.
- Clamping before the first and after the last key.
- A late-starting child track's independent local-time clamp.
- Independent movement of the second root, including quaternion sign.
- Non-static weighted vertex animation across multiple sample times.
- Finite, bounded outputs.
- Fail-closed handling of malformed, duplicate, non-finite or
  incomplete native frame records.

Run locally with a C11 compiler and Python:

    python3 -m unittest tests.test_foj_stage191_multiframe_skin_oracle -v

The existing Research tools CI matrix runs this test on both Python
3.11 and 3.13, compiling the **actual production C** sources.

## Evidence limits

This tests the consistency of **our experimental implementation**,
not the true PS3 animation playback algorithm. The authentic game
may use a different bind pose, coordinate transform order, actor/clip
binding, root motion, blend state or timebase. The test uses
**synthetic** geometry and keyframes, never publishes copyright
materials, and does not prove performance or execution on a physical
Nintendo Switch.

This work improves the testability of the port's animation path.
It is not a finished playable FoJ remake or a recovered original
engine animation system.
