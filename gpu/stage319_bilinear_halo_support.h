#ifndef FOJ_STAGE319_BILINEAR_HALO_SUPPORT_H
#define FOJ_STAGE319_BILINEAR_HALO_SUPPORT_H
/* Generated-only 4x4 atlas: conservative page support for an entire
 * continuous UV triangle under clamped RGBA8 bilinear texture filtering.
 *
 * Geometry is NOT expanded, no GPU draw or original PS3 material data.
 * Bilinear texel support extends 0.5 / 1024 normalized atlas UV units
 * into each neighboring page on both axes. This is distinct from the
 * triangle's actual geometric positive-area page footprint. */
#include <stdint.h>
#include "stage318_triangle_uv_coverage.h"

typedef struct {
    uint16_t geometry_page_mask;
    uint16_t filter_page_mask;
    uint16_t halo_only_page_mask;
    unsigned geometry_pages;
    unsigned filter_pages;
    unsigned halo_only_pages;
    double filter_halo_uv;
} FojStage319FilterSupport;

/* For each of 16 source pages, clip the triangle against that page
 * expanded by exactly half an atlas texel on each side, clamped to
 * normalized [0,1]. Any positive-area intersection adds filter support;
 * a zero-area tangent is NOT by itself a positive-area contribution.
 * Return a conservative UV-continuum support mask: no guarantee that
 * a finite raster framebuffer actually samples every candidate page.
 * Inputs invalid for Stage318, null or aliasing outputs are refused.
 * No caller memory is modified on failure. */
int foj_stage319_triangle_bilinear_pages(
    const FojStage318Triangle *triangle,FojStage319FilterSupport *out);
#endif
