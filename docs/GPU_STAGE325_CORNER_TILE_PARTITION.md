# Stage325 — complementary partition around a bounded corner tile

## Purpose

Stage324 introduces a bounded primitive that clips a UV triangle to one
16×16 atlas-corner tile and remaps that fragment's UVs to [0,1]². Drawing
only that fragment would omit the rest of the source triangle. Stage325
adds the complementary geometry needed to preserve coverage.

## Partition algorithm

The source triangle is first passed to Stage324 for the canonical clipped
tile fragment and tile-local UV remapping. Separately, the original triangle
is successively split by the tile's left, right, top and bottom half-planes.
At each edge, the outside polygon is emitted to a remainder triangle soup
in original atlas UV space, and the inside polygon continues to the next
edge. This independently partitions the complement while reusing Stage324's
tile geometry rather than implementing tile remapping a second time.

This partitions the original triangle into positive-area-disjoint regions.
Adjacent pieces can share boundary edges, but do not duplicate area.
Polygon fans preserve source winding. The worst-case bound is four
remainder polygons with at most 14 remainder triangles total (42 vertices),
plus at most five tile triangles (15 vertices).

The function preflights all arguments, capacities and memory overlaps
before touching caller memory. Invalid calls preserve both output buffers
and the report byte-for-byte. Valid non-intersections return the complete
triangle as remainder and an empty tile output. Receipt padding is zeroed
for deterministic byte comparisons.

## Synthetic tests

The GCC/Clang and sanitizer matrix checks all nine atlas junctions,
full-tile coverage, triangles fully inside or outside, partial intersections,
edge tangency, reversed winding, affine XYZ interpolation, exact tile UV
range, deterministic output, area conservation and atomic refusal paths.
All test geometry is generated numeric data.

## Limits

Stage325 remains a CPU partitioner, not a complete GPU batch executor.
The caller must submit tile and remainder fragments with correct source
texture/material bindings while retaining the original draw ordering.
Transparent overlap, actual FoJ mesh UV conventions, texture uploads,
original PS3 resources and physical Switch rendering are not verified here.
Keep the work Draft and do not alter `main`.
