#ifndef FOJ_STAGE303_BC1_PAGE_UV_H
#define FOJ_STAGE303_BC1_PAGE_UV_H

/* Research-only 1024 BC1 texture atlas nearest-neighbor UV addressing.
 * DOES NOT automatically split geometry, prevent hardware bilinear seams,
 * fetch a private game texture or prove NeXium GPU page selection.
 */
#include <stdint.h>
#include "bc1_atlas_page.h"

typedef struct {
    uint32_t atlas_x, atlas_y;  /* 0..1023, top-left atlas origin */
    uint32_t page_x, page_y;    /* 0..3, 256px BC1 pages */
    uint32_t local_x, local_y;  /* 0..255 on the selected page */
    float local_u, local_v;     /* center of nearest texel, in (0,1) */
} FojBc1PageUv;

/* No output mutation on failure.
 * Normalized [0,1] atlas UV. u=1 or v=1 addresses the final texel
 * (clamp semantics), not wrap. Rejects NaN/infinity/out of range.
 * Y grows downward. Explicitly nearest sampling only; linear filtering
 * and cross-page UV derivatives require separate GPU research.
 */
int foj_bc1_1024_resolve_uv(float u,float v,FojBc1PageUv *out);

/* Exact integer atlas texel -> page/local texel mapping. */
int foj_bc1_1024_resolve_texel(unsigned x,unsigned y,FojBc1PageUv *out);

#endif
