#ifndef FOJ_STAGE324_CORNER_TILE_CLIP_H
#define FOJ_STAGE324_CORNER_TILE_CLIP_H
/* Stage324: clip a UV-mapped triangle to one bounded 16x16 atlas-corner
 * tile and remap its UVs to the local tile. This is CPU geometry only:
 * it does not issue a GPU draw, render the remainder, or parse FoJ assets. */
#include <stddef.h>
#include <stdint.h>

enum {
    FOJ_STAGE324_MAX_POLYGON_VERTICES=12u,
    FOJ_STAGE324_MAX_OUTPUT_VERTICES=15u
};

typedef struct {
    float x,y,z,u,v;
} FojStage324Vertex;

typedef struct {
    FojStage324Vertex point[3];
} FojStage324Triangle;

typedef struct {
    uint32_t atlas_first_x;
    uint32_t atlas_first_y;
    float source_uv_bounds[4]; /* left, top, right, bottom */
    double clipped_uv_area;
    unsigned polygon_vertices;
    unsigned output_vertices;
    unsigned output_triangles;
    uint8_t intersects;
    uint8_t reserved[7];
} FojStage324TileClipReport;

/* Clip a triangle against the 16x16 texel domain surrounding an internal
 * corner (junction page x/y in [1,3]) of the normalized 1024x1024 atlas.
 * The tile spans [junction-8,junction+8] source texels on both axes.
 * XYZ and source UV are linearly interpolated at clip intersections;
 * surviving UVs are remapped to [0,1] tile-local coordinates.
 *
 * A convex triangle/rectangle intersection has <=7 unique vertices and
 * is fan-triangulated into <=5 triangles (15 output vertices). Capacity
 * must be exactly FOJ_STAGE324_MAX_OUTPUT_VERTICES for a bounded contract.
 * On valid input with no positive-area intersection, return 1, set
 * intersects/output counts to zero, and zero the output array.
 * Invalid inputs/aliases return 0 and leave output and report unchanged.
 * This creates only the patch portion; drawing the non-patch remainder,
 * preserving transparent draw order, and binding a GPU material are later
 * stages. All geometry/data are caller-owned and synthetic-safe.
 */
int foj_stage324_clip_triangle_to_corner_tile(
    const FojStage324Triangle *triangle,
    unsigned junction_page_x,unsigned junction_page_y,
    FojStage324Vertex *output,size_t output_capacity,
    FojStage324TileClipReport *report);

#endif
