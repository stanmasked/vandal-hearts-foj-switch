#include "stage317_atlas_bilinear.h"
#include <math.h>
#include <stdint.h>
#include <string.h>

static int overlaps(const void *aa,size_t an,const void *bb,size_t bn) {
    const uintptr_t a=(uintptr_t)aa,b=(uintptr_t)bb;
    if (an>UINTPTR_MAX-a || bn>UINTPTR_MAX-b)return 1;
    return a<b+bn && b<a+an;
}
int foj_stage317_sample_atlas(
    const uint8_t *const pages[FOJ_BC1_PAGE_COUNT],
    const size_t lengths[FOJ_BC1_PAGE_COUNT],
    float u,float v,uint8_t out[4],FojStage317RoutingReport *report) {
    if (!pages || !lengths || !out || !report ||
        !isfinite(u) || !isfinite(v) ||
        u<0.f || u>1.f || v<0.f || v>1.f ||
        overlaps(out,4u,report,sizeof(*report)))return 0;
    /* Validate all 16 independent source buffers before reading any pixel.
     * This refuses material aliases that could quietly fake page routing. */
    for (unsigned i=0;i<FOJ_BC1_PAGE_COUNT;++i) {
        if (!pages[i] || lengths[i]!=FOJ_BC1_PAGE_RGBA_BYTES ||
            overlaps(out,4u,pages[i],lengths[i]) ||
            overlaps(report,sizeof(*report),pages[i],lengths[i]))
            return 0;
        for (unsigned j=0;j<i;++j)
            if (overlaps(pages[i],lengths[i],pages[j],lengths[j]))
                return 0;
    }
    float fx=u*1024.f-0.5f,fy=v*1024.f-0.5f;
    if (fx<0.f)fx=0.f;
    if (fy<0.f)fy=0.f;
    if (fx>1023.f)fx=1023.f;
    if (fy>1023.f)fy=1023.f;
    const unsigned x0=(unsigned)floorf(fx),y0=(unsigned)floorf(fy);
    const unsigned x1=x0<1023u?x0+1u:x0;
    const unsigned y1=y0<1023u?y0+1u:y0;
    const float tx=fx-(float)x0,ty=fy-(float)y0;
    const unsigned ax[4]={x0,x1,x0,x1};
    const unsigned ay[4]={y0,y0,y1,y1};
    FojStage317RoutingReport result={0};
    uint8_t corner[4][4];
    unsigned pages_seen=0;
    for(unsigned i=0;i<4u;++i) {
        FojBc1PageUv t={0};
        if (!foj_bc1_1024_resolve_texel(ax[i],ay[i],&t))
            return 0;
        const unsigned page=t.page_y*4u+t.page_x;
        if (page>=FOJ_BC1_PAGE_COUNT)return 0;
        pages_seen|=1u<<page;
        const size_t k=((size_t)t.local_y*256u+t.local_x)*4u;
        memcpy(corner[i],pages[page]+k,4u);
        result.texel[i]=t;
    }
    for(unsigned i=0;i<16u;++i)result.distinct_pages+=(pages_seen>>i)&1u;
    result.crosses_page_x=(unsigned)(result.texel[0].page_x!=
                                     result.texel[1].page_x);
    result.crosses_page_y=(unsigned)(result.texel[0].page_y!=
                                     result.texel[2].page_y);
    uint8_t color[4];
    for(unsigned channel=0;channel<4u;++channel) {
        const float up=(1.f-tx)*corner[0][channel]+tx*corner[1][channel];
        const float down=(1.f-tx)*corner[2][channel]+tx*corner[3][channel];
        const float value=(1.f-ty)*up+ty*down;
        color[channel]=(uint8_t)floorf(value+0.5f);
    }
    memcpy(out,color,4u);
    *report=result;
    return 1;
}
