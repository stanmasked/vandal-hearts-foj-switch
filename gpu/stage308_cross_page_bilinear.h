#ifndef FOJ_STAGE308_CROSS_PAGE_BILINEAR_H
#define FOJ_STAGE308_CROSS_PAGE_BILINEAR_H
/* Stage308: generated-only, unambiguous cross-page bilinear reference.
 * This is a CPU research contract, not a deko3d GPU shader or game decoder.
 * 1024x1024 atlas split into 256x256 pages; row within pages 0..255.
 */
#include <stdint.h>
#include "stage303_bc1_page_uv.h"

/* Return 1 iff both page buffers have exactly 256x256x4 RGBA bytes,
 * position u lies between the centers of atlas texels 511 and 512,
 * and row_y is within one page. Returns the exact rounding-to-nearest
 * linear reconstruction of those two cross-page texels. Output stays
 * unchanged on every failure. No implicitly clamped unrelated U.
 */
int foj_stage308_cross_page_bilinear(
    const uint8_t *left_rgba, const uint8_t *right_rgba,
    unsigned row_y, float atlas_u, uint8_t out_rgba[4]);

/* Compare with independent clamp-to-edge lookups at the *same* seam:
 * return 1 only when left/right are distinct, desired lies between them
 * on >=1 channel, and either page alone cannot produce desired pixel.
 * Explicitly not a proof of GPU seam repair. */
int foj_stage308_requires_two_pages(
    const uint8_t left_pixel[4], const uint8_t right_pixel[4],
    const uint8_t blended_pixel[4]);

#endif
