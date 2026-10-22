#include "stage315_corner_patch.h"
#include "stage314_four_page_corner.h"
#include <stdint.h>
#include <string.h>
static int overlaps(const void *aa,size_t an,const void *bb,size_t bn) {
    const uintptr_t a=(uintptr_t)aa,b=(uintptr_t)bb;
    if (an>UINTPTR_MAX-a || bn>UINTPTR_MAX-b)return 1;
    return a<b+bn && b<a+an;
}
int foj_stage315_build_corner_patch(
    const uint8_t *const pages[4], const size_t lengths[4],
    uint8_t *out_rgba,size_t out_len,FojStage315CornerReport *report) {
    if (!pages || !lengths || !out_rgba || !report ||
        out_len!=FOJ_BC1_PAGE_RGBA_BYTES ||
        overlaps(out_rgba,out_len,report,sizeof(*report)))return 0;
    for (unsigned i=0;i<4u;++i) {
        if (!pages[i] || lengths[i]!=FOJ_BC1_PAGE_RGBA_BYTES ||
            overlaps(out_rgba,out_len,pages[i],lengths[i]) ||
            overlaps(report,sizeof(*report),pages[i],lengths[i]))
            return 0;
    }
    static const size_t pixel_offset[4]={
        ((size_t)255u*256u+255u)*4u,((size_t)255u*256u)*4u,
        (size_t)255u*4u,0u
    };
    uint8_t corners[4][4];
    for(unsigned i=0;i<4u;++i)
        memcpy(corners[i],pages[i]+pixel_offset[i],4u);
    uint8_t midpoint[4]={0};
    /* The original Stage314 reference validates the real atlas coordinates. */
    if (!foj_stage314_four_page_bilinear(
         pages[0],lengths[0],pages[1],lengths[1],
         pages[2],lengths[2],pages[3],lengths[3],
         .5f,.5f,midpoint))return 0;
    FojStage315CornerReport result={0};
    for(unsigned a=0;a<4u;++a)
        for(unsigned b=a+1u;b<4u;++b)
            if (memcmp(corners[a],corners[b],4u))
                ++result.distinct_corner_pairs;
    result.strict_four_page_midpoint=(unsigned)
        foj_stage314_requires_four_page_mix(corners,midpoint);
    memcpy(result.midpoint_rgba,midpoint,4u);
    /* Every texture pixel is written exactly once; no later failure path. */
    for(unsigned y=0;y<256u;++y) {
        for(unsigned x=0;x<256u;++x) {
            const unsigned corner=(y>=128u?2u:0u)+(x>=128u?1u:0u);
            memcpy(out_rgba+((size_t)y*256u+x)*4u,corners[corner],4u);
        }
    }
    result.pixels_written=65536u;
    *report=result;
    return 1;
}
