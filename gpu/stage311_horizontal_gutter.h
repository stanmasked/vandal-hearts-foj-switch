#ifndef FOJ_STAGE311_HORIZONTAL_GUTTER_H
#define FOJ_STAGE311_HORIZONTAL_GUTTER_H
/* Stage311 synthetic-only horizontal page seam reference.
 * The last texel row of atlas page (1,1) and first texel row of
 * page (1,2) meet at atlas V=0.5, row coordinates 511 and 512.
 * These are caller-owned 256x256 RGBA8 decoded BC1 buffers.
 */
#include <stddef.h>
#include <stdint.h>
#include "bc1_atlas_page.h"

typedef struct {
    unsigned columns_processed;
    unsigned contrasting_columns;
    unsigned genuinely_mixed_columns;
} FojStage311HorizontalReport;

/* Restricted to the interval between texel centers 511.5/1024 and
 * 512.5/1024; refuses nonfinite V, bad X or buffer sizes.
 * Leaves output bytes untouched on failure. */
int foj_stage311_horizontal_bilinear(
    const uint8_t *top_rgba,size_t top_bytes,
    const uint8_t *bottom_rgba,size_t bottom_bytes,
    unsigned local_x,float atlas_v,uint8_t out_rgba[4]);

/* Row 0..127: copy top page's bottommost decoded row 255.
 * Row 128..255: copy bottom page's first decoded row 0.
 * Each column is independently copied. Never uses game files,
 * changes caller source data, or leaks source paths.
 * Rejects any overlapping output/report with input buffers, and
 * leaves output and report bit-identical on rejection. */
int foj_stage311_build_horizontal_gutter(
    const uint8_t *top_rgba,size_t top_bytes,
    const uint8_t *bottom_rgba,size_t bottom_bytes,
    uint8_t *gutter_rgba,size_t gutter_bytes,
    FojStage311HorizontalReport *report);
#endif
