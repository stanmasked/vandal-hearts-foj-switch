#ifndef FOJ_STAGE320_UV_PAGE_BATCHES_H
#define FOJ_STAGE320_UV_PAGE_BATCHES_H
/* Stage320: public synthetic-only UV triangle render-planning reference.
 * The plan groups triangles by identical geometric page footprints AND
 * bilinear filter-source page dependencies, WITHOUT GPU upload or assets.
 * Underlying masks are Stage318 and Stage319 computed from the UV triangle.
 */
#include <stddef.h>
#include <stdint.h>
#include "stage319_bilinear_halo_support.h"

enum { FOJ_STAGE320_MAX_TRIANGLES=128u };

typedef struct {
    uint32_t first_index;   /* first index in the flattened original-ID list */
    uint32_t index_count;   /* number of grouped triangles */
    uint16_t geometry_mask; /* page cells with positive UV geometric area */
    uint16_t filter_mask;   /* pages needed for continuous bilinear sampling */
    uint16_t halo_mask;     /* filter_mask minus geometry_mask */
    uint16_t reserved;      /* must be zero */
} FojStage320Batch;

typedef struct {
    unsigned triangle_count;
    unsigned batch_count;
    unsigned geometry_page_references; /* summed popcount over all triangles */
    unsigned filter_page_references;   /* summed popcount over all triangles */
    uint16_t all_geometry_pages;
    uint16_t all_filter_pages;
    uint16_t all_halo_only_pages; /* filter pages required by at least one halo */
    uint16_t reserved;
} FojStage320Plan;

/* Deterministic ascending (filter_mask, geometry_mask) batch order.
 * Stable original triangle order within each matching batch.
 * output_ids are original zero-based triangle IDs, not vertex indices;
 * this does not generate a GPU draw stream or copy triangle geometry.
 *
 * All inputs must be distinct from all outputs. Input triangle count
 * must be in [1,128]. Capacity is explicit: index_capacity >= count,
 * batch_capacity >= number of distinct keys. On any failure (invalid
 * triangle, insufficient capacity, aliases or null), neither output
 * buffer nor report is changed at any index.
 */
int foj_stage320_plan_triangle_batches(
    const FojStage318Triangle *triangles,size_t triangle_count,
    uint16_t *output_ids,size_t index_capacity,
    FojStage320Batch *output_batches,size_t batch_capacity,
    FojStage320Plan *report);
#endif
