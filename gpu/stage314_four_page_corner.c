#include "stage314_four_page_corner.h"
#include "stage303_bc1_page_uv.h"
#include <math.h>
#include <stdint.h>
#include <string.h>

static int overlap(const void *ap,size_t an,const void *bp,size_t bn) {
    const uintptr_t a=(uintptr_t)ap,b=(uintptr_t)bp;
    if (an>UINTPTR_MAX-a || bn>UINTPTR_MAX-b)return 1;
    return a<b+bn && b<a+an;
}
int foj_stage314_four_page_bilinear(
    const uint8_t *nw,size_t nw_bytes,
    const uint8_t *ne,size_t ne_bytes,
    const uint8_t *sw,size_t sw_bytes,
    const uint8_t *se,size_t se_bytes,
    float atlas_u,float atlas_v,uint8_t rgba_out[4]) {
    if (!nw || !ne || !sw || !se || !rgba_out ||
        nw_bytes!=FOJ_BC1_PAGE_RGBA_BYTES ||
        ne_bytes!=FOJ_BC1_PAGE_RGBA_BYTES ||
        sw_bytes!=FOJ_BC1_PAGE_RGBA_BYTES ||
        se_bytes!=FOJ_BC1_PAGE_RGBA_BYTES ||
        !isfinite(atlas_u) || !isfinite(atlas_v) ||
        overlap(rgba_out,4u,nw,nw_bytes) ||
        overlap(rgba_out,4u,ne,ne_bytes) ||
        overlap(rgba_out,4u,sw,sw_bytes) ||
        overlap(rgba_out,4u,se,se_bytes))return 0;
    const float min=511.5f/1024.f,max=512.5f/1024.f;
    if (atlas_u<min || atlas_u>max ||
        atlas_v<min || atlas_v>max)return 0;
    const float tx=atlas_u*1024.f-511.5f;
    const float ty=atlas_v*1024.f-511.5f;
    if (tx<0.f || tx>1.f || ty<0.f || ty>1.f)return 0;
    FojBc1PageUv resolved[4]={{0}};
    if (!foj_bc1_1024_resolve_texel(511u,511u,&resolved[0]) ||
        !foj_bc1_1024_resolve_texel(512u,511u,&resolved[1]) ||
        !foj_bc1_1024_resolve_texel(511u,512u,&resolved[2]) ||
        !foj_bc1_1024_resolve_texel(512u,512u,&resolved[3]))
        return 0;
    const unsigned page_x[4]={1u,2u,1u,2u};
    const unsigned page_y[4]={1u,1u,2u,2u};
    const unsigned local_x[4]={255u,0u,255u,0u};
    const unsigned local_y[4]={255u,255u,0u,0u};
    const uint8_t *pages[4]={nw,ne,sw,se};
    uint8_t corners[4][4];
    for (unsigned i=0;i<4u;++i) {
        if (resolved[i].page_x!=page_x[i] ||
            resolved[i].page_y!=page_y[i] ||
            resolved[i].local_x!=local_x[i] ||
            resolved[i].local_y!=local_y[i])return 0;
        const size_t at=((size_t)local_y[i]*256u+local_x[i])*4u;
        memcpy(corners[i],pages[i]+at,4u);
    }
    /* Weighting is separable but rounded exactly once after 4 samples.
     * No integer truncation or two-stage 8-bit quantization bias. */
    uint8_t mixed[4];
    for (unsigned k=0;k<4u;++k) {
        const float top=(1.f-tx)*corners[0][k]+tx*corners[1][k];
        const float bottom=(1.f-tx)*corners[2][k]+tx*corners[3][k];
        const float value=(1.f-ty)*top+ty*bottom;
        mixed[k]=(uint8_t)floorf(value+0.5f);
    }
    memcpy(rgba_out,mixed,4u);
    return 1;
}

int foj_stage314_requires_four_page_mix(
    const uint8_t corners[4][4],const uint8_t center[4]) {
    if (!corners || !center)return 0;
    for (unsigned i=0;i<4u;++i)
        if (!memcmp(corners[i],center,4u))return 0;
    for (unsigned i=0;i<4u;++i) {
        /* NW-NE, SW-SE, NW-SW, NE-SE respectively. */
        static const unsigned pairs[4][2]={
            {0u,1u},{2u,3u},{0u,2u},{1u,3u}};
        uint8_t edge[4];
        for(unsigned k=0;k<4u;++k)
            edge[k]=(uint8_t)((corners[pairs[i][0]][k]+
                              corners[pairs[i][1]][k]+1u)/2u);
        if (!memcmp(edge,center,4u))return 0;
    }
    int interior=0;
    for(unsigned k=0;k<4u;++k) {
        unsigned lo=255u,hi=0u;
        for (unsigned i=0;i<4u;++i) {
            if (corners[i][k]<lo)lo=corners[i][k];
            if (corners[i][k]>hi)hi=corners[i][k];
        }
        if (center[k]<lo || center[k]>hi)return 0;
        if (center[k]>lo && center[k]<hi)interior=1;
    }
    return interior;
}
