# Stage328 — atomic corner-tile plus ordered GPU stream

## Purpose

Stage327 proved that one corner-tile partition can be serialized into the
existing GPU-independent vertex stream. Stage328 combines the earlier stages
into one transactional preparation API:

1. verify that a supplied Stage320 batch describes every supplied triangle;
2. independently recompute each triangle's Stage319 geometry/filter/halo masks;
3. regenerate the four-page Stage321 PATCH_REQUIRED command;
4. build the exact 16x16 RGBA8 corner tile with Stage322;
5. partition the same source triangles with Stage327 into ordered source-atlas
   and tile-texture sections;
6. commit the tile, used stream ranges and compact receipt only after all
   preceding steps succeed.

The batch must correspond to one of the nine internal atlas junctions and to
the same triangle subset supplied in Stage320 stable order. The source texture
index represents the original atlas/material for the remainder; the generated
tile has a distinct texture index. This is still CPU-side staging, not a draw.

## Bounds and transactional behavior

The combined helper is deliberately limited to 16 source triangles to keep
its temporary vertex stream bounded on the Switch application thread stack.
The fixed maximum is 912 vertices and 32 sections. All page buffers are
exactly one decoded 256x256 RGBA8 page; the tile output is exactly 1,024 bytes.

All input UV page masks are rechecked against the Stage320 batch before the
planner command is regenerated. Wrong corner masks, mismatched batches,
invalid geometry, incorrect page lengths, insufficient capacities, invalid
texture indices and overlapping input/output regions are rejected. Tile and
stream outputs are staged locally; any rejection leaves all caller output
buffers and the receipt unchanged.

The receipt contains the source page mask and page IDs, tile checksum and
midpoint sample, texture indices, and counts for the partitioned stream.
No original game assets are bundled, and the code performs no file I/O,
allocation or GPU command.

## Regression matrix

The dedicated workflow runs Stage326's independent spatial coverage oracle,
Stage327's ordered-stream tests, and Stage328's combined integration test
under GCC and Clang optimized builds, GCC UBSan, and Clang ASan+UBSan. The
Stage328 test constructs synthetic decoded pages and exercises all nine
internal junctions. It verifies exact copied texels, matching Stage320 masks,
source/tile section order, deterministic receipts, shared GPU projection,
and fail-closed behavior for capacity, mask, page-length, invalid geometry,
texture-index and output-alias failures.

The Stage323 bounded-corner NRO make target also compiles the new Stage328
source so the native devkitA64 build checks its headers and ABI.

## Limits and next step

This connects the tile-generation and CPU geometry paths, but it does not
upload the generated tile as a second deko3d texture, issue a real patch draw,
prove the original PS3 material/shader semantics, support triangles crossing
multiple corner junctions in one pass, or prove transparent-mesh ordering.
Physical Switch rendering remains unverified. Keep the PR Draft and leave
main unchanged until the new matrix and native build results are reviewed.
