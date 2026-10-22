#ifndef FOJ_STAGE318_TRIANGLE_UV_COVERAGE_H
#define FOJ_STAGE318_TRIANGLE_UV_COVERAGE_H
/* Stage318: generated-only exact positive-area UV-triangle coverage across
 * the 4x4 pages of a 1024x1024 atlas. Input triangle is in normalized UV.
 * No original FoJ assets, geometry reconstruction or GPU rendering. */
#include <stddef.h>
#include <stdint.h>
typedef struct { float u,v; } FojStage318Uv;
typedef struct { FojStage318Uv point[3]; } FojStage318Triangle;
typedef struct {
    uint16_t page_mask;     /* bit index = page_y*4+page_x */
    unsigned pages_covered;
    unsigned vertical_page_boundaries_crossed;
    unsigned horizontal_page_boundaries_crossed;
    double triangle_area_uv;
    double covered_area_uv;
    double page_area_uv[16];
} FojStage318Coverage;

/* Calculates the *positive-area* intersection of a triangle with each
 * 1/4 x 1/4 page rectangle using 2D polygon clipping, NOT bounding-box
 * overapproximation. Page boundary touch with zero area is not coverage.
 * Valid input UVs must be finite and in [0,1] inclusive; triangle must
 * have non-negligible nonzero area. An output overlapping the input is
 * refused. Any refusal leaves output unchanged. The 16 per-page areas
 * sum to triangle_area_uv (to floating tolerance), without duplicating
 * area on seams. This is geometric footprint, not bilinear filter support. */
int foj_stage318_triangle_page_coverage(
    const FojStage318Triangle *triangle,FojStage318Coverage *out);
#endif
