#include "stage303_bc1_page_uv.h"
#include <math.h>
#include <string.h>

int foj_bc1_1024_resolve_texel(unsigned x,unsigned y,FojBc1PageUv *out) {
    if (!out || x>=FOJ_BC1_SOURCE_EDGE || y>=FOJ_BC1_SOURCE_EDGE)
        return 0;

    const unsigned page_x=x/FOJ_BC1_PAGE_EDGE;
    const unsigned page_y=y/FOJ_BC1_PAGE_EDGE;
    const unsigned local_x=x%FOJ_BC1_PAGE_EDGE;
    const unsigned local_y=y%FOJ_BC1_PAGE_EDGE;
    const FojBc1PageUv calculated = {
        x,y,page_x,page_y,local_x,local_y,
        ((float)local_x+0.5f)/(float)FOJ_BC1_PAGE_EDGE,
        ((float)local_y+0.5f)/(float)FOJ_BC1_PAGE_EDGE,
    };
    memcpy(out,&calculated,sizeof(calculated));
    return 1;
}

int foj_bc1_1024_resolve_uv(float u,float v,FojBc1PageUv *out) {
    if (!out || !isfinite(u) || !isfinite(v) ||
        u<0.0f || v<0.0f || u>1.0f || v>1.0f)
        return 0;
    /* Integer quantization first: exact edge u=0.25 -> page x=1.
     * Upper endpoint u=1 is clamped to pixel 1023.
     * Float product at 0.5/1024 texel centers is exactly representable. */
    unsigned x=(unsigned)(u*(float)FOJ_BC1_SOURCE_EDGE);
    unsigned y=(unsigned)(v*(float)FOJ_BC1_SOURCE_EDGE);
    if (x>=FOJ_BC1_SOURCE_EDGE)x=FOJ_BC1_SOURCE_EDGE-1u;
    if (y>=FOJ_BC1_SOURCE_EDGE)y=FOJ_BC1_SOURCE_EDGE-1u;
    return foj_bc1_1024_resolve_texel(x,y,out);
}
