# Stage272 — portable native topological order of translucent triangles

Stacked on Stage271 negative NeXium safety checks. Stage270's
fixed draw-order guard and three actual NeXium positive captures remain
unchanged.

## The problem

Stage270 intentionally refuses any three-layer overlap whose input
order is not already back-to-front. For a larger actor, ordering may
still be **unambiguously solvable** even when the source triangle
sections arrive in arbitrary order.

Stage272 introduces a **host-only C11 planning module**:

```c
foj_alpha_sort_back_to_front(vertices, count, output, capacity);
```

The input contains from 1 to 64 triangles, three clip-space vertices
per triangle, and a constant W=1. The coordinate convention is the same
as earlier research: orthographic XY in [-1,1], normalized Z in [0,1],
larger Z nearer. Output indices refer to input triangle positions.
The caller must allocate at least `count` indices.

For every pair, projected convex intersection is computed using
winding-aware clipping. On the **positive-area** overlap polygon, a
barycentric Z difference must have a constant strict sign, or the
pair is rejected. Depth-equal/crossing geometry remains **unsafe**.

Relations between overlapping triangles become edges in a directed
graph **from farther to nearer**. Kahn's algorithm selects the lowest
currently available original triangle index to produce a stable,
reproducible back-to-front sequence. Disjoint pairs impose no
constraints. Cycles are rejected.

### Transactional and bounded behavior

- No heap allocation, GPU calls, file access, external dependencies,
  user assets or platform-specific SDK functions.
- At most 64 triangles. Refuses nonfinite/out-of-range XYZ, W != 1,
  degenerate projections, ambiguous depth or unsafe cycles.
- **Does not modify output on any error**. Graph and results are first
  computed into bounded stack arrays.
- Tests cover inverse source order, nonoverlapping triangles, unsafe
  crossings and coplanarity, 64 disjoint triangles exercising the
  highest `uint64_t` bit, and unchanged output on failure.
- Python reference comparison checks **1,000 deterministic invented
  multi-triangle scenes** with random screen position, winding and Z.
  This supplements Stage271's 2,000 projected geometry comparisons
  for the existing fixed 3-layer guard.

## Critical limitation

**This code plans CPU draw order; it does not yet reorder GPU batches.**
Neither Stage267 nor Stage270 NRO has changed. There is no new NeXium
render verification in Stage272 itself. In particular, this is NOT
alpha order-independent transparency (OIT): pairs with crossing depth
are refused, and a split-geometry or per-pixel approach is required to
render them correctly. Transparent textured actors, animations,
original PS3 resources, perspective interpolation, hardware Switch
operation and final playable game port remain separate work.

The next stage must explicitly integrate and verify any resulting
ordering against real deko3d commands; an all-green Stage272 host
workflow does not prove GPU rendering.
