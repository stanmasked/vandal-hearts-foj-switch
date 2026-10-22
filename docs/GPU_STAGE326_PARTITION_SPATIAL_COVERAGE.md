# Stage326 — independent spatial coverage oracle

## Purpose

Stage325 checks output capacities, winding, interpolation and UV-area
conservation. Area conservation alone is not an independent proof that the
two output soups cover the right locations: a gap and an overlap could, in
principle, cancel in an area sum.

Stage326 adds a deterministic point-location oracle. It samples points strictly
inside each synthetic source triangle, maps the point into tile-local UV space,
and counts coverage in the tile fragment and the original-atlas remainder.

## Invariant checked

For every accepted sample, exactly one output region must contain it:

- samples inside the 16×16 corner-tile rectangle are covered once by the
tile-local triangle soup and zero times by the remainder soup;
- samples outside the rectangle are covered zero times by the tile soup and
once by the remainder soup.

The oracle also rejects sampled positive-area overlap between remainder
triangles. Samples near emitted edges and tile boundaries are skipped to avoid
ambiguous point-on-boundary classifications. The PRNG seed and test cases are
fixed for reproducibility.

## Coverage set

The test checks all nine internal atlas junctions with:
- a triangle spanning the tile interior and surrounding remainder;
- broad triangles on both sides of the atlas diagonal;
- 56 deterministic randomized triangles around each junction;
- 4,096 samples for each centered case, 1,024 for each broad case and 192 for
each randomized case.

All geometry is generated numeric test data. No original game resources are
read or uploaded.

## Validation matrix

The dedicated workflow compiles and runs the same oracle with GCC and Clang
optimized builds, GCC UBSan, and Clang ASan/UBSan.

## Limits

This is a deterministic sampled oracle, not a formal proof over all real-valued
points and not a renderer integration test. It does not establish original
FoJ mesh UV conventions, transparent draw ordering, GPU texture upload behavior
or physical Nintendo Switch rendering. Keep the work Draft and leave main
unchanged.
