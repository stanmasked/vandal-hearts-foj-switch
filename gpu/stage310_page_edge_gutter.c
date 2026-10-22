#include "stage310_page_edge_gutter.h"
#include "stage308_cross_page_bilinear.h"
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

/* Check overlap by validated integer address intervals without forming
 * any out-of-bounds C pointers. Refuse unrepresentable pointer ranges. */
static int intersect(const void *ap,size_t an,const void *bp,size_t bn) {
    const uintptr_t a=(uintptr_t)ap,b=(uintptr_t)bp;
    if (an>UINTPTR_MAX-a || bn>UINTPTR_MAX-b)return 1;
    return a<b+bn && b<a+an;
}

int foj_stage310_build_page_edge_gutter(
    const uint8_t *left_rgba,size_t left_bytes,
    const uint8_t *right_rgba,size_t right_bytes,
    uint8_t *out_rgba,size_t out_bytes,
    FojStage310GutterReport *report) {
    if (!left_rgba || !right_rgba || !out_rgba || !report ||
        left_bytes!=FOJ_BC1_PAGE_RGBA_BYTES ||
        right_bytes!=FOJ_BC1_PAGE_RGBA_BYTES ||
        out_bytes!=FOJ_BC1_PAGE_RGBA_BYTES ||
        intersect(out_rgba,out_bytes,left_rgba,left_bytes) ||
        intersect(out_rgba,out_bytes,right_rgba,right_bytes) ||
        intersect(out_rgba,out_bytes,report,sizeof(*report)) ||
        intersect(report,sizeof(*report),left_rgba,left_bytes) ||
        intersect(report,sizeof(*report),right_rgba,right_bytes))
        return 0;

    uint8_t *temporary=(uint8_t*)malloc(FOJ_BC1_PAGE_RGBA_BYTES);
    if (!temporary)return 0;
    FojStage310GutterReport result={0,0,0};
    int ok=1;
    for(unsigned y=0;y<256u;++y) {
        const uint8_t *left=left_rgba+((size_t)y*256u+255u)*4u;
        const uint8_t *right=right_rgba+(size_t)y*256u*4u;
        uint8_t blended[4];
        if (!foj_stage308_cross_page_bilinear(
                left_rgba,left_bytes,right_rgba,right_bytes,y,.5f,
                blended)) { ok=0;break; }
        ++result.rows;
        if (memcmp(left,right,4u))++result.contrasting_edge_rows;
        if (foj_stage308_requires_two_pages(left,right,blended))
            ++result.strictly_mixed_rows;
        uint8_t *row=temporary+(size_t)y*256u*4u;
        for(unsigned x=0;x<256u;++x)
            memcpy(row+(size_t)x*4u,x<128u?left:right,4u);
    }
    if (ok && result.rows==256u) {
        memcpy(out_rgba,temporary,FOJ_BC1_PAGE_RGBA_BYTES);
        *report=result;
    } else ok=0;
    free(temporary);
    return ok;
}
