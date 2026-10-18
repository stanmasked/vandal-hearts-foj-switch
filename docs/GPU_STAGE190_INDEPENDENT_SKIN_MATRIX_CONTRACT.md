# Stage 190 — independent C / Python skeleton matrix contract

The portable C implementation in core/skeletal_skin.c already builds
an experimental world-space bone palette, multiplies by inverse bind
matrices and deforms vertices with linear blend skinning. Stage 190 adds
an **independent numerical implementation in Python** to test that
mathematical contract using a second implementation.

## Why this matters

An implementation can pass its own self-tests while carrying a shared
incorrect assumption about transform composition. This cross-check
deliberately uses two distinct calculations:

- The production C code constructs row-major 3×4 affine rotation
  matrices from XYZW quaternions, multiplies parent world matrices,
  then computes animatedWorld × inverse(bindWorld) and weighted output.
- The Python oracle composes quaternion+translation world poses,
  computes animated × conjugate(bind) rotations, translates the
  transformed binding origin, and constructs matrix columns by rotating
  canonical unit axes using quaternion products. It independently
  applies weighted points.

The native C probe calls the **real C library**, not a copy of the
algorithm. Its textual output is validated for shape, finite values,
expected case names and records. Every matrix component and deformed
vertex is compared against the independent Python oracle with a
0.0003 absolute tolerance for C float32 rounding.

## Invented-only test scenarios

Five deterministic cases exercise:

1. **Bind identity:** 3 bones including two roots, inverse-bind
   cancellation, weighted and unweighted vertices.
2. **Child Z90:** child-only pivot rotation, root-only influence and
   50/50 linear weight blending with independent analytic points.
3. **Rotated parent plus independent root:** one parent's motion
   propagates to its child; another root moves independently.
4. **Equivalent quaternion signs:** +W to -W must not change orientation
   or the deformed vertex positions.
5. **Three-bone hierarchy:** different X/Y/Z rotation axes, mixed
   skinning influences and an unchanged unweighted vertex.

Six regressions run in the Research tools CI matrix for Python 3.11
and Python 3.13. They compile the native C probe against the real
core/skeletal_skin.c and core/banim_core.c source files.

To execute privately on a host with a C compiler:

    python3 -m unittest tests.test_foj_stage190_skin_matrix_contract -v

## Limits

This validates the **chosen experimental skinning convention**.
It does not prove that the original PS3 engine uses the same local
coordinate spaces, matrix multiplication convention, inverse bind
construction or track-to-bone mapping. It does not identify real
model-animation pairs, reconstruct FoJ combat, use original files
in GitHub CI or prove native Switch GPU scanout.

Stage 188/189's local-only rig/animation candidate census remains
independent of this synthetic mathematical contract.
