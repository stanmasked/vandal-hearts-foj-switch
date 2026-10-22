#ifndef FOJ_STAGE325_CORNER_TILE_PARTITION_H
#define FOJ_STAGE325_CORNER_TILE_PARTITION_H
/* Stage325 builds on Stage324's canonical tile clip/remap primitive. */
#include <stddef.h>
#include <stdint.h>
#include "stage324_corner_tile_clip.h"

enum {
    FOJ_STAGE325_MAX_POLYGON_VERTICES=12u,
    FOJ_STAGE325_TILE_VERTICES=FOJ_STAGE324_MAX_OUTPUT_VERTICES,
    FOJ_STAGE325_REMAINDER_VERTICES=42u
};

typedef FojStage324Vertex FojStage325Vertex;
typedef FojStage324Triangle FojStage325Triangle;

typedef struct {
    uint32_t atlas_first_x,atlas_first_y;
    float source_uv_bounds[4]; /* left, top, right, bottom */
    double input_uv_area;
    double tile_uv_area;
    double remainder_uv_area;
    unsigned tile_vertices;       /* tile-local UV; multiple of 3 */
    unsigned tile_triangles;
    unsigned remainder_vertices;  /* original atlas UV; multiple of 3 */
    unsigned remainder_triangles;
    uint8_t tile_intersects;
    uint8_t reserved[7];
} FojStage325PartitionReport;

/* Partition a source-UV triangle against one of the nine 16x16 corner
 * tiles centered on an internal 256x256 page junction in a 1024x1024 atlas.
 * The tile fragment and its local UVs come from Stage324. Remainder pieces
 * preserve source-atlas UVs and are emitted in a disjoint triangle soup.
 *
 * The remainder is decomposed into at most 14 non-overlapping triangles by
 * successively splitting against the four tile half-planes. Together the
 * tile and remainder preserve the input triangle's UV area and winding.
 * Boundary edges may be shared, but no positive-area region is duplicated.
 *
 * Capacities are exact and fixed to make the memory bound explicit.
 * On valid input with no positive-area tile intersection, tile output is
 * all zero and the remainder contains the complete triangle.
 * Invalid input, aliases or capacity mismatch return 0 and leave all
 * caller output and report bytes unchanged. No original assets are read.
 */
int foj_stage325_partition_triangle_at_corner_tile(
    const FojStage325Triangle *triangle,
    unsigned junction_page_x,unsigned junction_page_y,
    FojStage325Vertex *tile_output,size_t tile_capacity,
    FojStage325Vertex *remainder_output,size_t remainder_capacity,
    FojStage325PartitionReport *report);

#endif
