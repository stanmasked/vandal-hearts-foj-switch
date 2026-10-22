#ifndef FOJ_STAGE317_ATLAS_BILINEAR_H
#define FOJ_STAGE317_ATLAS_BILINEAR_H
/* Generated-only general BC1 1024 atlas RGBA8 bilinear reference.
 * All sixteen already decoded pages are supplied in ROW-MAJOR order:
 * pages[page_y*4+page_x], 256x256 RGBA8 each. No original PS3 files,
 * game UV inference, GPU ownership or private file handling. */
#include <stddef.h>
#include <stdint.h>
#include "stage303_bc1_page_uv.h"
typedef struct {
    FojBc1PageUv texel[4]; /* NW,NE,SW,SE sampled atlas texels. */
    unsigned distinct_pages;
    unsigned crosses_page_x;
    unsigned crosses_page_y;
} FojStage317RoutingReport;

/* Clamp-to-edge normalized atlas UVs [0,1] on both axes. Output is the
 * rounded-once bilinear mix of the four actual atlas texels. Identical
 * texels on clamped outer edges are permitted. Only bounded page sizes
 * accepted: 16 unique, nonoverlapping RGBA8 buffers, each 256x256.
 * Reject null, wrong sizes, NaN/Inf, page aliasing, and output/report
 * overlap; leave output/report and all pages unchanged on ANY failure. */
int foj_stage317_sample_atlas(
    const uint8_t *const pages[FOJ_BC1_PAGE_COUNT],
    const size_t page_bytes[FOJ_BC1_PAGE_COUNT],
    float atlas_u,float atlas_v,uint8_t out_rgba[4],
    FojStage317RoutingReport *report);
#endif
