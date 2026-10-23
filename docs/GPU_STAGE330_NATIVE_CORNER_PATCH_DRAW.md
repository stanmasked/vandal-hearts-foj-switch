# Stage330 — mixed source remainder and generated corner-tile draw

## Purpose

Stage329 proved that a generated 16×16 corner tile could be uploaded and sampled by a real deko3d draw. Stage330 closes the adjacent integration gap: a single source triangle crosses the tile boundary and must produce both a source-atlas remainder and a tile fragment in the same ordered GPU stream.

## Scene and contracts

- The triangle spans atlas UVs 480–544 in both axes around junction (2,2).
- Stage328 atomically produces the 16×16 tile and a geometry stream with exactly two material sections.
- Section 0 is the source remainder using texture index 0; section 1 is the corner tile using texture index 1.
- The tile fragment covers the whole tile and is triangulated as two triangles. The remainder must have positive area and at least one triangle.
- Tile UVs are remapped to [0,1]. Source-remainder UVs stay in atlas coordinates; a second normalization is rejected.
- The synthetic 256×256 source atlas uses the same red, green, blue, and white quadrants as the four generated pages. Its midpoint and the generated tile therefore share a known color contract.

## Evidence

The host C test verifies the atomic Stage328 receipt, tile checksum, section ordering, texture indices, UV domains, and GPU stream preparation. The NeXium audit then samples a real framebuffer: the tile midpoint and four quadrant gradients must be visible, while pixels outside the tile must show the source texture's left/right interpolated colors. The upload marker is necessary but never accepted as a substitute for framebuffer evidence.

Only generated data is used. No original PS3 assets, user DDS files, or private game resources are read or published. Passing this stage does not prove behavior on physical Nintendo Switch hardware.


## Follow-up audit — complete two-material upload reservation

The native entry point now validates the actual Stage330 material mask (bits 0 and 1), rather than the Stage329 tile-only mask (bit 1). The host C test exercises the same actor upload planner and verifies payload size, aligned allocation, both material bits, and the two-batch count. This prevents the native NRO from rejecting the valid mixed source/tile stream before GPU command recording.


The framebuffer audit also requires near-full contrast at the center tile's ±20-pixel samples. The synthetic source atlas alone produces a visibly softer transition at those positions and must fail this check; the tile-only negative path is rejected by the source-remainder samples outside the tile.
