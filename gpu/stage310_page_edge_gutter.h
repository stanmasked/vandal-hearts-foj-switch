#ifndef FOJ_STAGE310_PAGE_EDGE_GUTTER_H
#define FOJ_STAGE310_PAGE_EDGE_GUTTER_H
/* CPU-native generic cross-page gutter builder.
 * Input: two already-decoded 256x256 RGBA8 pages, each at exact size.
 * Output: 256x256 RGBA8 2-color-column texture:
 *    [0..127]=last texel of left page, [128..255]=first of right page.
 * Exact copies for EVERY row; not hardcoded colors or source game data.
 * Rejects overlapping output/input, bad sizes or null, leaves caller
 * buffer and report unchanged on failure.
 */
#include <stddef.h>
#include <stdint.h>
#include "bc1_atlas_page.h"

typedef struct {
    unsigned rows;
    unsigned contrasting_edge_rows;
    unsigned strictly_mixed_rows;
} FojStage310GutterReport;

int foj_stage310_build_page_edge_gutter(
    const uint8_t *left_rgba,size_t left_bytes,
    const uint8_t *right_rgba,size_t right_bytes,
    uint8_t *out_rgba,size_t out_bytes,
    FojStage310GutterReport *report);
#endif
