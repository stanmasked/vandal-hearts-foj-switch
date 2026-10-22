# Stage324 — bounded triangle clipping and tile-local UV remapping

## Why this stage follows Stage323

Stage322 builds an exact 16×16 RGBA8 tile from the four independently
decoded BC1 pages around any of the nine internal atlas junctions.
Stage323 then proved that one such 1-KiB synthetic tile reaches a real
NeXium GPU draw and produces a four-corner, two-axis filtered gradient.

That was a controlled centered-quad experiment. It did not yet explain
how a triangle with its own XYZ and atlas UVs should be clipped to the
small region covered by a corner tile. Stage324 adds that bounded CPU
geometry primitive without pretending it is already a full renderer.

## Geometry contract

For junction page coordinates (px, py), each in [1,3], the tile covers
the source atlas texel domain

- x: [256*px - 8, 256*px + 8]
- y: [256*py - 8, 256*py + 8]

normalized by the 1024×1024 atlas dimensions. The triangle is clipped
against this rectangle using Sutherland–Hodgman half-plane clipping.
New boundary vertices linearly interpolate XYZ and source UV. The
surviving UVs are remapped to the local 16×16 tile domain [0,1]², with
small floating-point boundary excursions clamped only after checking
that the values remain within a strict tolerance.

The clipped convex polygon is fan-triangulated to at most five triangles
and fifteen vertices. Caller-owned storage has an exact bounded capacity.
All validation occurs before commit; invalid inputs and memory aliases
leave the output and report unchanged. Valid no-area/tangent intersections
return an empty output rather than inventing a draw.

## Native checks

The new GCC/Clang and sanitizer matrix covers:

- all nine internal atlas junctions with full rectangle intersections;
- exact source-domain bounds and tile-local UV corner coverage;
- affine XYZ interpolation at every generated vertex;
- partial intersection and reversed triangle winding;
- zero-area edge contact, which must not become a draw;
- deterministic output, NaN/degenerate input refusal, wrong capacity,
  invalid junctions and input/output/report alias refusal;
- output/report atomicity on invalid input.

All fixtures are invented numeric geometry. No original PS3 resources,
gameplay captures, or private logs enter CI.

## Explicit limitations

This is a CPU clipping primitive, not the complete deferred-batch executor.
It emits only the part of one triangle that lies inside one corner tile.
The non-tile remainder still needs an explicit complementary partition;
the renderer must also retain original draw order and handle overlapping
patches, transparency, and GPU texture upload. Stage324 does not parse
original FoJ meshes, infer their real UV conventions, issue GPU commands,
or claim physical Nintendo Switch validation. Keep this work Draft and
leave \`main\` unchanged.
