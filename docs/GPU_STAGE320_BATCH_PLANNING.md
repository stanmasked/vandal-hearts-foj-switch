# Stage320 — deterministic UV triangle batch planning by atlas page dependencies

## Context

Stage316 verified real two-dimensional GPU bilinear interpolation through
a CPU-assembled, generated-only four-way BC1 corner patch. Stage317 passed
full 16-page synthetic texel address tests. Stage318 computed geometric
UV triangle overlap across 4x4 pages, and Stage319 separately identified
filter-only source pages required by the half-texel bilinear halo.

The next step is a reference plan combining those analyses across a series
of triangles without pretending any original game assets have been decoded.

## Native output contract

foj_stage320_plan_triangle_batches() accepts 1–128 synthetic normalized
UV triangles and caller-owned capacity-checked outputs. It calls Stage319
for each triangle and groups exact equivalent masks:

- geometry_mask: pages covered by the triangle's positive UV area;
- filter_mask: page textures needed for continuous bilinear sampling;
- halo_mask: filter_mask minus geometry_mask.

Separate groups are necessary even if the geometric area mask is the same:
two triangles fully inside page (1,1) may require just that page, two
pages near a vertical seam, or all four pages near a corner.

The returned batches are sorted deterministically by numeric
(filter_mask, geometry_mask), rather than input arrival order. The
flattened uint16 triangle-ID array preserves input order within each
group; a batch stores its first index, element count, and all masks.
IDs reference the input triangle index; this is a CPU planning format,
NOT vertex buffer byte offsets, and it never issues GPU commands.

A report returns batch count, triangle count, union of geometric/filter/
halo-only page masks, and total per-triangle source page references.

## Validation and atomicity

Null/empty or too-large input, insufficient index/batch capacity,
malformed triangle UVs, aliased output regions, aliased input/output,
pointer arithmetic overflow and unexpected Stage319 failures all refuse
without modifying any output. The implementation uses bounded local
staging arrays before a final commit to all caller-owned buffers, with
no heap allocation or external filesystem access.

## Native regression

- Synthetic triangles exercising single-page interiors and 1→2 and 1→4
  filter page dependencies; a diagonal 3→4 case and UV=1 atlas clamp.
- Nonconsecutive duplicate groups and exact stable original-ID ordering.
- All sixteen pages represented across the 128-triangle maximum batch.
- Deterministic byte-for-byte repeat plan and preservation of inputs.
- Every output ID belongs to exactly one batch; batch masks are
  independently recomputed using Stage319.
- Reject nulls, zero/overlimit count, insufficient capacities, aliases,
  malformed NaN/infinite UV late in a full array, with exact atomicity.

Four CI variants: GCC optimized, Clang optimized, GCC UBSan,
Clang ASan+UBSan. All fixture triangles are generated and safe to publish.

## Limits and next research

Stage320 does not perform texture loading, original FoJ mesh parsing,
UV seam triangulation, actual GPU descriptor binding or NeXium rendering.
A batch may reference more than the current research renderer's 3
simultaneous materials; that is a planning dependency, not a claim it can
already be drawn. Follow-up work needs a robust bounded patch/texture
upload schedule and, privately, verified original FOJRM and material
coordinate semantics before rendering actual game geometry.

Never publish original NPEB00148 PS3 assets, private capture traces or
raw guest logs. Keep this stacked PR Draft and main unchanged.
