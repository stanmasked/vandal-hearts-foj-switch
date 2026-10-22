#ifndef FOJ_STAGE315_CORNER_PATCH_H
#define FOJ_STAGE315_CORNER_PATCH_H
/* Generated-only corner material for four decoded 256x256 BC1 pages.
 * Order: NW (1,1), NE (2,1), SW (1,2), SE (2,2).
 * No game files, hardware GPU calls or private paths. */
#include <stddef.h>
#include <stdint.h>
#include "bc1_atlas_page.h"
typedef struct {
    unsigned pixels_written;
    unsigned distinct_corner_pairs;
    unsigned strict_four_page_midpoint;
    uint8_t midpoint_rgba[4];
} FojStage315CornerReport;
/* Output quadrant colors NW/NE in upper 128 rows, SW/SE below.
 * Refuses invalid lengths, null pointers and source/report/output aliasing.
 * No input, output or report mutation on failure. */
int foj_stage315_build_corner_patch(
    const uint8_t *const pages[4], const size_t page_bytes[4],
    uint8_t *out_rgba, size_t out_bytes, FojStage315CornerReport *report);
#endif
