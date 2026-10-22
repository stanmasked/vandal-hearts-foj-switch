#ifndef FOJ_STAGE314_FOUR_PAGE_CORNER_H
#define FOJ_STAGE314_FOUR_PAGE_CORNER_H
/* Research-only four-page bilinear corner of a 1024x1024 BC1 atlas.
 * Pages ordered NW=(1,1), NE=(2,1), SW=(1,2), SE=(2,2).
 * Exact source boundary x/y 511..512; RGBA8 decoded 256x256 pages.
 * No game resources, GPU usage, or private file operations.
 */
#include <stddef.h>
#include <stdint.h>
#include "bc1_atlas_page.h"

/* The sole supported u,v interval spans the 4 texel centers:
 * normalized 511.5/1024 through 512.5/1024 inclusive.
 * Rejects invalid pointers/bytes, nonfinite/out-of-bounds UV,
 * aliased output, and preserves all input/output bytes on failure.
 * The four corner texels contribute in fixed NW/NE/SW/SE order.
 * Applies rounding once, after both weighted interpolation axes.
 */
int foj_stage314_four_page_bilinear(
    const uint8_t *northwest,size_t nw_bytes,
    const uint8_t *northeast,size_t ne_bytes,
    const uint8_t *southwest,size_t sw_bytes,
    const uint8_t *southeast,size_t se_bytes,
    float atlas_u,float atlas_v,uint8_t rgba_out[4]);

/* Refuses a "four-page" claim unless center RGBA is distinct from
 * all four source corners and all four two-page edge midpoints.
 * Does NOT claim that actual hardware automatically blends pages.
 */
int foj_stage314_requires_four_page_mix(
    const uint8_t corners[4][4],
    const uint8_t center[4]);

#endif
