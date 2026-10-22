# Stage327 — ordered GPU stream staging for one corner-tile partition

## Purpose

Stage325 provides a bounded CPU partition of one UV-mapped source triangle
into the corner-tile fragment and its original-atlas remainder. Stage326 adds
an independent sampled spatial-coverage oracle. Stage327 connects that
partition to the existing GPU-independent vertex-stream contract without
claiming to upload or draw original game geometry.

## Stream contract

The input is a bounded list of 1–32 source triangles that share one source
texture and one of the nine internal atlas-corner tiles. For each source
triangle, the builder appends:

1. the nonempty remainder soup in original atlas UVs, using the source texture;
2. the nonempty tile soup in tile-local UVs, using the generated tile texture.

The pieces of a single triangle have no duplicated positive-area region, so
their local ordering does not alter coverage. Pieces from different source
triangles are never reordered, and adjacent sections are not merged. This
keeps the source primitive sequence explicit for later alpha/order handling.

The output uses `FojTexturedVertex` and contiguous `FojTextureSection` ranges.
The complete stream can be passed once to `foj_gpu_prepare_stream`, which
calculates camera-space depth normalization across all vertices and returns
ordered GPU batches. Calling the projection separately for each material
could create incompatible depth ranges; this adapter avoids that mistake.

## Bounds and rejection

- At most 32 source triangles.
- At most 57 output vertices and two nonempty sections per source triangle.
- Fixed global limits of 1,824 vertices and 64 sections, both below the
  existing GPU stream limits.
- Source and tile texture indices must be distinct and within the declared
  texture count.
- Wrong capacities, invalid source geometry, overlapping buffers, invalid
  junctions, or an invalid Stage325 partition are rejected during preflight.
  Failed preflight leaves output arrays and report unchanged.

No heap allocation, file I/O, original PS3 resource, or GPU command is used.

## Tests

The dedicated GCC/Clang and sanitizer matrix re-runs Stage326's spatial
coverage oracle and validates Stage327 with mixed partial/outside/inside
triangles. Tests compare emitted vertices against direct Stage325 output,
check section order and texture selection, feed the complete stream through
the shared GPU projection, check deterministic output, and verify fail-closed
behavior for undersized buffers, invalid material selection, NaN geometry and
output aliasing.

## Limits and next step

This proves CPU-side staging for one generated tile and one source texture. It
does not bind the actual generated tile to deko3d, preserve a complete original
FoJ mesh's alpha draw order, support multiple corner tiles per triangle, infer
original PS3 UV/material semantics, or validate physical Switch rendering.
Keep this PR Draft and leave `main` unchanged.
